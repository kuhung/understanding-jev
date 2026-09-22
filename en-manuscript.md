# Reading Jev: Millisecond Decisions and Engineering Limits

In past projects, I spent a lot of time cutting API latency. Users are highly sensitive to response speed. Once a system sits still for a second or two, it looks broken. Many large models take two or three seconds, sometimes more, just to reason. Teams try all kinds of engineering tricks. Autoregressive generation still writes tokens one by one, so latency is hard to squeeze down.

A lot of the time, we do not need a model that writes long essays. For state checks and enum classification, speed matters more than generation. That is why I want to talk about Jev.

Why did this model stir things up recently? The direction of general-purpose large models is mostly settled. New product teams have to find a different angle. Jev claims two years of closed development, and it sells extreme speed. It drops the autoregressive loop. Input is billed by tokens. Output tokens are free. That is fair. It is a discriminator. Nobody pays per token for a random forest score either.

This note covers Jev's technical path, local tests, common patterns, and where it belongs in production. Use it when you design architecture and pick models.

# What Is Jev

Jev is a statistical classifier for state evaluation. Large models generate. Jev discriminates. It takes classification work that is slow and expensive on an LLM, and makes it cheap and fast.

At launch, plenty of developers thought it was a joke. Founder Diogo Almeida sounds close to Anthropic CEO Dario Amodei. A community demo of millisecond-level DOOM control made people look at what it can actually do.

The name comes from Jevons paradox. When a resource gets much cheaper to use, total consumption often rises instead of falling. If one model decision gets a hundred times cheaper, places that used to be hard-coded if-else may start calling a model.

Jev sits in machine-to-machine state evaluation. It does not answer users. It does not write natural language. Given context, it returns a predefined discrete label in tens of milliseconds and sends the request down a branch. This is like a sorter in a logistics line. Lightweight routers in front of large models were already a common pattern.

Official numbers: $0.042 per million input tokens, free output, 70 to 500 ms end to end. Small base model, single forward pass, or both. Service cost stays low.

Marketing borrows the dual-system idea from cognitive science. Expensive frontier models do slow System 2 work. Jev is a cheap System 1 reflex. Prefetch filters and routing do not need a generator riding along.

To go fast, Jev drops text generation and keeps three primitives:

1. `choice`: pick one option from an enum list.
2. `score`: score on an ordered discrete scale, such as 0 to 10.
3. `noul`: binary classification probability (boolean decision, e.g., true/false or yes/no).

Each output ships a confidence value. Many of us have watched LLMs emit wrong JSON with a smug probability. Jev says that confidence is calibrated. Downstream code can set a threshold and hand low-confidence cases to rules or humans. How that calibration is trained comes later.

On the wiring side, TypeSafe AI sits on Cloudflare AI Gateway and Vercel. With `@ai-sdk/typesafe-ai`, the call is `experimental_evaluate`:

```tsx
import { experimental_evaluate } from '@ai-sdk/typesafe-ai';

const result = await experimental_evaluate({
  model: 'typesafe-ai/jev',
  prompt: contextText,
  primitive: { type: 'choice', options: ['allow', 'block', 'escalate'] },
});
```

No need to put Jev on a pedestal. There is no statistical breakthrough. The skill set is narrow. It cannot write long prose, code, multi-turn memory, or long math. Not every job needs a pricey frontier model. A discriminator built for speed still has engineering value.

# Under the Hood

Jev is not fully open source. Official reports plus community reproductions already make the path clear.

A normal LLM doing classification still runs an autoregressive decode, token by token. That often takes 2 to 5 seconds. Downstream still has to check whether the JSON closed. Jev generates zero tokens. After the prompt and candidate actions, the network does one forward pass. The output is a byproduct of a matrix multiply.

The community had two reproductions within two hours of launch. Neither rewrites attention. Both run on ordinary open small models.

Path one is logit masking over candidate tokens. [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) shows the idea. After one forward pass, take logits at the last position, keep only candidate token IDs, and softmax locally for confidence. Constrained decoding and intent routing have used this for a long time.

```python
# harshatheg/Qwen-2.5-1B-RLCD logits projection
logits = model(input_ids).logits[:, -1, :]
candidate_logits = logits[:, candidate_token_ids]
probs = torch.softmax(candidate_logits, dim=-1)
```

Path two is an NLI cross-encoder. [AlexWortega/openjev](https://github.com/AlexWortega/openjev) uses a Qwen base. Context is the premise. Each action is a hypothesis. The head scores entailment, neutral, and contradiction. Entailment probability is the decision.

```python
# AlexWortega/openjev cross-encoder scoring
inputs = tokenizer(premise=state, hypothesis=action, return_tensors="pt")
logits = cross_encoder(**inputs).logits
entailment_score = logits[:, ENTAILMENT_IDX]
```

One option per forward pass is still slow when many options arrive at once. Jev leans on decoder-only KV cache prefix sharing. Long context is prefilled once into GPU memory. Later candidates share that prefix pointer and only compute attention on a few extra tokens. Scoring dozens of dimensions takes about as long as scoring one.

Why not drop any small model into this slot? Softmax scores are relative, not true probabilities. Uncalibrated models are overconfident. A wrong answer can still print 0.99. A production interceptor cannot trust that raw number.

Jev trains with RLCD, reinforcement learning for calibrated decisions. The objective is Expected Calibration Error, not pretty sentences. After sample checks and penalties, a reported 0.8 confidence should land near 80% accuracy.

Calibration does not erase attention structure.

First, irrelevant options interfere. Archer Hume added a dummy weather option after four valid ones. The winning option's log-odds dropped. Candidates still attend to each other. The model is ranking a list. Options are not independent.

Second, physical order matters. Causal attention lets later tokens see everything before them. Move the evidence, or shuffle options, and the answer can move. Put evidence in the shared prompt state so attention is more even.

People ask how this differs from a 2018 BERT classifier. The gap is world knowledge and context size. BERT is usually 512 tokens and a small vocabulary. It struggles with long code, logs, and business documents. Jev sits on a modern causal Transformer with large-scale pretraining. The generation loop is what got removed.

# 20 Lines of Code

Drop the packaging. Zero-token generation runs locally in about 20 lines of Python.

Load Qwen-2.5-0.5B-Instruct, a 0.5B open model, with a support-ticket prompt and candidate labels. Skip the generation loop. One forward pass. Slice logits at the last position for those labels and normalize:

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")

prompt = "判断用户意图：'我想退货'。选项：[投诉, 咨询, 售后]"
candidate_words = ["投诉", "咨询", "售后"]
candidate_ids = [tokenizer.encode(w)[0] for w in candidate_words]

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_ids]
    probs = torch.softmax(logits, dim=-1)

for word, prob in zip(candidate_words, probs):
    print(f"{word}: {prob.item():.4f}")
```

Ask the same 0.5B model to emit JSON the usual way, and it writes dozens of tokens over a second or two, plus JSON parsing. Reading last-token logits can stay under 30 ms.

On the edge, `typesafe/jev` through Cloudflare Workers or REST looks just as small:

```tsx
const result = await env.AI.run("typesafe/jev", {
  state: ticketContent,
  questions: { is_urgent: "noul", department: "choice", frustration: "score" }
});
```

After local and cloud calls, the technical split is easier to see.

Local last-token logits give relative scores. Uncalibrated softmax still overstates confidence. On unsure samples, a tiny logit gap can blow up past 95%.

Commercial work is mostly RLCD or large-sample calibration, lining confidence up with real accuracy. If you only want speed, local logits are enough. If you auto-allow or auto-block on the number, run temperature scaling or post-hoc calibration on your own data. Do not auto-allow wrong labels because the score looks high.

# Benchmark Data

Lab numbers without real traffic are not objective enough. Archer Hume ran tens of thousands of calls against the official Jev API, on long context and high concurrency.

Long-context test: one question against the same growing document, end-to-end latency recorded.

| Input context (tokens) | Median latency | Fastest latency |
| ---------------------- | -------------- | --------------- |
| 360                    | 57.5 ms        | 44.0 ms         |
| 9,796                  | 89.0 ms        | 81.0 ms         |
| 29,835                 | 218.0 ms       | 211.0 ms        |

From 360 to about 30,000 tokens, median latency went from 57.5 ms to 218 ms. Text grew about 80x. Delay grew about 160 ms. That matches a non-autoregressive model. There is no per-token decode tax. Most of the time sits in one prefill.

High-concurrency test: short context, questions from 1 to 1,500.

| Concurrent questions | Median latency    | Behavior        |
| -------------------- | ----------------- | --------------- |
| 1 - 100              | 70.0 - 100.0 ms   | Fairly flat     |
| 500                  | ~240.0 ms         | Gentle rise     |
| 1,500                | 610.0 ms          | Queueing starts |

From 1 to 100 questions, latency stayed in the 70 to 100 ms band. At 1,500 it hit 610 ms. Shared KV prefix is being reused. Public context is not recomputed.

Speed is not quality. Richard Becker, in [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop), compared raw Qwen 2.5 7B logits with the official Jev API.

Marketing cites 86.6% decision agreement. Becker measured about 73.8%. Wrong Qwen predictions still often showed softmax confidence above 0.90.

```python
# https://github.com/rorshopping/jev-on-a-laptop
probs = torch.softmax(qwen_logits[:, target_token_ids], dim=-1)
pred_idx = torch.argmax(probs, dim=-1)
confidence = probs.max(dim=-1).values
# 预测错误时 confidence 仍常高于 0.90
```

On billing: the official API still uses an "output token" line item. Under the hood there is one forward pass, no autoregressive decode. A few label bytes get counted as synthetic tokens. Vendors keep a unit developers already know. Per-call cost is the actual model.

# Failure Modes

Knowing where it fits matters more than staring at a benchmark chart. Single-step classifiers fail in clear ways.

### Missing chain-of-thought

A single forward pass cannot run multi-hop causal logic. In [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench), emails with nested turns and fake identities favored Claude Haiku with chain-of-thought. Jev missed more of them.

The path is one matrix multiply. LLMs build intermediate steps while generating. Single-step scoring has to emit the answer at once. Past two layers of semantic bait, it often cannot keep up.

```python
# 单步评估缺乏中间推理步骤，多步逻辑推导容易失准
decision = jev.evaluate(email_body, primitive={"type": "noul", "question": "Is this phishing?"})
```

### Option order

Candidate order moves the decision. Archer Hume's prompt tests kept accuracy high when evidence sat after the options. Move that evidence to the front or the middle, and accuracy dropped.

Later tokens see everything before them. Evidence at the very start can get diluted in a long sequence. Put reference text in shared state, ahead of the options.

### Irrelevant options

Add a dummy option such as weather to a multiple-choice list, and log-odds among the real options slip.

Scoring is not independent. Full attention lets the candidate pool compete. Noise options take weight too. Tight statistical settings need a clean candidate set.

### Uncalibrated logits

Raw logits from a self-hosted small model are a safety problem if you treat them as confidence. Qwen 7B raw logits agreed with the calibrated commercial API only about 73.8% of the time.

If the gateway auto-allows high confidence and only reviews low confidence, inflated scores send wrong labels through. The safety net does not exist.

### No generation

Jev has no autoregressive decode. It cannot write a coherent sentence. Log summaries, code, and support replies are out of scope. It is a discriminator on the line. If you need to tell a user why a request was blocked, hand the context to a generator.

### Single-step ceiling

These limits share one cause: fixed capacity in one forward pass. The network only transforms features at a fixed depth. Multi-step logic, long text generation, or strict independent probabilities still need an autoregressive model.

# Four Patterns

In production, a single-step discriminator usually sits with rules and a large model. Four patterns show up often.

### Speculative fan-out

A long ticket or document often needs many labels at once. Asking an LLM one question after another grows time and cost linearly.

Fan-out reuses prefix cache. Prefill the long context once. Hang a dozen discrete questions on that cache and run light forwards in parallel. Multi-label extract time stays close to a single call.

```tsx
// 共享前置长文本 KV Cache，一次网络往返并发求值多维标签
const profile = await jev.evaluateBatch({
  context: rawTicketContent,
  questions: { is_urgent: "noul", sentiment: "score", dept: { type: "choice", options: DEPTS } },
});
```

Questions in one batch should be independent. If B depends on A's answer, they cannot run in the same batch.

### Confidence gate

The predicted label picks the action. Confidence picks how automatic it is.

Above 0.90, execute. Between 0.60 and 0.90, execute later, log, and sample for review. Below 0.60, treat as unknown and send to a human or a stronger model.

```tsx
// 动作由 answer 指引，执行权限由 confidence 分级裁决
if (result.confidence >= 0.90) return autoExecute(result.answer);
if (result.confidence >= 0.60) return logAndAlertAsyncReview(result.answer);
return circuitBreakToHuman(requestId);
```

High-volume moderation is the usual fit. Clear allow and clear block finish instantly. The gray band goes to humans. This needs real calibration. Tune thresholds against false blocks and false passes on a schedule.

### Composite scoring

Teams often ask a model for one 0-100 quality score. That number jumps around when the prompt twitches.

Have the model score one dimension at a time, 0 to 10. Weights and hard rules stay in deterministic backend code. Policy changes are config edits, not prompt rewrites.

```python
# 模型仅提供单项原子分，加权公式与安全硬规则由确定性代码执行
scores = {k: jev.score(text, metric=k) for k in ["clarity", "depth", "factuality"]}
composite_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
is_qualified = composite_score >= 80 and scores["factuality"] >= 6
```

### Hierarchical classification

Hundreds or thousands of labels in one enum dilute attention.

Walk a tree. Pick top-k at the root, then score children on the winning branches, prune as you go.

```python
# 顶层先粗筛出 Top-2 大类，随后沿活跃分支并发检索细分类
top_roots = jev.top_k(product_text, candidates=ROOT_CATEGORIES, k=2)
sub_candidates = [leaf for root in top_roots for leaf in TAXONOMY[root]]
final_leaf = jev.evaluate(product_text, candidates=sub_candidates)
```

E-commerce catalog work is the usual example: electronics vs outdoors first, then the leaf. Keep two or three branches alive at each level so an early miss does not dump the rest of the search.

# Production Architecture

Put a low-latency discriminator in front of the gateway and you stop a lot of generation you never needed.

### Hybrid routing

Traffic hits the API gateway, then a single-step classifier. Labels and confidence split the flow. Routine queries hit cache or precomputed answers. Policy violations stop there. Only multi-step reasoning wakes the generative model.

### Cost and latency

A service at 100,000 requests per day, 800 input tokens and 400 output tokens on average:

| Architecture | Daily LLM calls | Daily inference (USD) | Monthly (USD) | P50 latency | P99 latency |
| ------------ | --------------- | --------------------- | ------------- | ----------- | ----------- |
| All traffic to GPT-4o / Claude class | 100,000 | $840.00 | $25,200.00 | 1,800 ms | 4,200 ms |
| Discriminator in front + LLM | 20,000 | $171.36 | $5,140.80 | 25 ms | 2,100 ms |
| **Change** | **-80.0%** | **-79.6%** | **-79.6%** | **-98.6%** | **-50.0%** |

If about 80% of routine requests stop at the discriminator or the cache, LLM volume drops. Cost drops. Users wait less.

### Three gateway shapes

1. Interceptor: millisecond prefilter at ingress, cut injection there.
2. Router: read intent, send hard work to a heavy cluster, send small talk and canned Q&A to a local small model.
3. Guard: authorize before an agent runs a shell command or edits sensitive config. Block overreach immediately.

```tsx
const verdict = await jev.evaluate({
  state: `Command: ${command}; WorkingDir: ${cwd}`,
  primitive: { type: "choice", options: ["allow", "block", "escalate"] }
});
if (verdict.choice !== "allow") throw new SecurityViolationError(verdict);
```

### Production cases

A few public repos already ship this idea:

- `pi-warden`: intercepts file overwrites and terminal commands, instead of a keyword denylist.
- `pi-jev-auto-mode`: picks single-step speed or deep reasoning from task difficulty and context length.
- `jev-router` / `codex-router`: parse code intent at the door and split traffic.

### ReflexGate

Package the decision as middleware and people call it ReflexGate. Hang a 1B to 3B local model such as Qwen2.5-1.5B on ingress. Turn generation off. Run one deterministic forward pass. Per-GPU throughput goes up. Safety checks and intent scores finish in 10 to 30 ms.

```python
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_token_ids]
    calibrated_probs = torch.softmax(logits / temperature, dim=-1)
```

### Shadow traffic

Before cutover, copy live traffic to the new classifier and compare with the current path. Move it onto the main line when divergence stays inside tolerance and confidence looks stable.

# Ecosystem Map

After launch, the community reproduced and forked the idea across sizes, from tens of millions of parameters to tens of billions.

| Repo | Base | Notes |
| ---- | ---- | ----- |
| [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) | Qwen-2.5-1B | Parallel constrained decoding, no retraining, discrete distribution in one step |
| [AlexWortega/openjev](https://github.com/AlexWortega/openjev) | Qwen3.5-4B / 35B MoE | NLI sequence classification, including a Qwen3.5-35B-A3B MoE setup |
| [heman10x/rlcd-modernbert-151m](https://github.com/heman10x/rlcd-modernbert-151m) | ModernBERT 151M | 25 candidate slots, under 35 ms, edge-friendly |
| [Mapika/decider-2b](https://github.com/Mapika/decider-2b) | Qwen3.5-2B-Base | Full-parameter fine-tune on hundreds of thousands of labeled samples |
| [TheoLeeCJ/openjev](https://github.com/TheoLeeCJ/openjev) ([openjev.com](http://openjev.com)) | MiniCPM5-2B-GGUF | In-browser WebGPU, no backend |
| [vinnylarouge/jevlike](https://github.com/vinnylarouge/jevlike) | Tiny byte encoder | Cross-attention to cut option interference |
| [DavidHatley/system-one-mini](https://github.com/DavidHatley/system-one-mini) | Custom compact net | About 69M params, single-step reflex on little compute |

Where people actually put it:

1. **GUI automation**: `browser-use/jev-ultrafast` and `droidrun/mobile-jev` hand screen state and action choice to a single-step model, and call a generator only for long text.
2. **Security gateway**: `pi-warden` checks permission before an agent runs a command.
3. **Semantic routing**: `jev-router` grades difficulty at ingress and splits models.
4. **Game control**: `lukaske/jev-doom-agent` drives DOOM movement at millisecond latency.

# Should You Use It

When you design the architecture, first decide whether the job needs fast instinct or slow causal work. Many systems spin a tens-of-billions model to emit one enum. That is a compute mismatch.

### Four questions

1. **Are requests highly enumerable?** If most traffic sits in a known set, a single-step discriminator is cheaper. Open-ended tails still need a large model.
2. **Is the label set stable?** Labels that change often should be passed in at runtime. Stable labels can be distilled offline.
3. **What does a wrong label cost?** Low tolerance work, payments included, needs rules or a human behind it.
4. **Do you have gold labels?** Without them, you cannot check accuracy or calibration. Homegrown models overfit easily.

### Three-way trade-off

| Dimension | Classic BERT | Generative LLM | Jev / single-step |
| --------- | ------------ | -------------- | ----------------- |
| **Runtime flexibility** | Low. Labels are frozen. Adds need retraining. | High. Prompt defines the output. | Higher. Candidates arrive at runtime. |
| **World knowledge** | Weak. Needs in-domain labels. | Very rich. | Rich. Inherits pretraining. |
| **Context length** | Short. Often 512 tokens. | Very long. Hundreds of thousands. | Mid-long. Depends on the base cache. |
| **Latency** | Very fast. Often under 20 ms. | Slow. Hundreds of ms to seconds. | Fast. 20 to 200 ms. |
| **Output** | Fixed class distribution | Generated text, format can drift | Structured discrete probabilities |
| **Confidence** | Needs extra calibration | Raw logits often too high | More usable after calibration training |
| **Deep reasoning** | None | Strong. Multi-step chains. | Weak. Single-step pattern match. |

### Fit and non-fit

Use a single-step discriminator for:

- Intent and routing at the door
- High-volume compliance prefilter
- Sensitive API and shell permission checks
- Fixed enum state machines

Skip it for:

- Natural language explanations to users
- Work that needs two or more causal hops
- Security cases with stacked disguise
- Open generation with no candidate list

### Two notes

If you need very high accuracy plus multi-step deduction, use a model with chain-of-thought. A single forward pass has no scratchpad. Nested turns throw it off.

If you have almost no labels, run the product on a general LLM with few-shot prompts and keep the logs. After you have a cleaned set, distill or replace with a single-step discriminator.

### Index

- Archer Hume Jev API load tests
- [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) - raw Qwen logits vs Jev
- [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) - phishing, single-step vs chain-of-thought
- [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) - logit mask and PCD
- [AlexWortega/openjev](https://github.com/AlexWortega/openjev) - NLI cross-encoder
- [multimodalart/jev-reproductions-tracker](https://huggingface.co/spaces/multimodalart/jev-reproductions-tracker) - community tracker
- [AnotiaWang/awesome-jev](https://github.com/AnotiaWang/awesome-jev) - ecosystem index
- [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) - browser automation
- [droidrun/mobile-jev](https://github.com/droidrun/mobile-jev) - mobile agent
- [DevMortimer/pi-warden](https://github.com/DevMortimer/pi-warden) - command guard
