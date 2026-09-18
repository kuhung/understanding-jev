## 拆底层 / Under the Hood

<!-- lang:zh -->
Jev 目前尚未完全开源，但结合官方技术报告与开源社区的逆向复现，它的实现路径已经相当明确。

传统大模型处理分类或决策，必须启动自回归解码循环，逐个生成 Token。整个过程通常耗时 2 到 5 秒，下游还得小心处理 JSON 字符串是否闭合。Jev 的生成步数为零。输入提示词与候选动作后，底层网络只执行单次前向传播，输出在数学上只是一次矩阵乘法的副产物。

<!-- DIAGRAM: 单次前向传播与自回归生成循环在步数与延迟上的核心计算链路对比 -->

开源社区在发布两小时内就跑通了两条复现路径，都不需要重写注意力机制，直接在开源小模型上就能运行。

第一条路径是候选词 Logits 掩码投影。社区项目 [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) 验证了这种思路：模型在单次前向推导后，直接提取序列最后一个位置的 Logits，仅筛选出候选标签对应的 Token ID，做局部 Softmax 归一化计算置信度。这也是过往做约束输出和意图路由时常用的方法。

```python
# harshatheg/Qwen-2.5-1B-RLCD logits projection
logits = model(input_ids).logits[:, -1, :]
candidate_logits = logits[:, candidate_token_ids]
probs = torch.softmax(candidate_logits, dim=-1)
```

第二条路径是基于 NLI（自然语言推理）的交叉编码器架构。项目 [AlexWortega/openjev](https://github.com/AlexWortega/openjev) 选用 Qwen 系列作为底座，把输入上下文作为前提（Premise），候选动作作为假设（Hypothesis）。分类头直接输出蕴含、中立与矛盾三分类得分，取蕴含概率做决策。

```python
# AlexWortega/openjev cross-encoder scoring
inputs = tokenizer(premise=state, hypothesis=action, return_tensors="pt")
logits = cross_encoder(**inputs).logits
entailment_score = logits[:, ENTAILMENT_IDX]
```

如果单次前向每次只能评估一个选项，面对高并发多选项时依然不够快。Jev 依靠 Decoder-only 架构的 KV Cache 前缀缓存共享来化解瓶颈。面对长文本上下文，模型在 Prefill 阶段只计算一次并存入显存，后续几十个候选选项共享同一份前缀缓存指针，只并行计算各自少量 Token 的注意力。这使得评估几十个维度的总耗时几乎等同于单次评估。

<!-- DIAGRAM: 基于共享 Prefill KV 缓存的分支并行扇出推理机制 -->

普通小模型为什么不能直接套用这套逻辑？熟悉机器学习的朋友清楚，Softmax 输出的分数只是指数归一化的相对值，不等于真实概率。未经专门校准的模型普遍存在严重的过度自信，即使预测完全错误，Softmax 也可能给出 0.99 的高分。工业级安全拦截系统不能直接依赖这种裸露数值。

Jev 引入了面向校准决策的强化学习（RLCD）。该训练方式不再关注生成句子的语言文采，而是针对预期校准误差（ECE）进行优化。简单来说，就是通过样本校验与惩罚，确保模型输出 0.8 的置信度时，在统计上真实对应约 80% 的准确率。

即便经过概率校准，也无法完全消除底层注意力的结构特性：

第一是无关选项的干扰。Archer Hume 的实验显示，在既有的四个有效选项后追加一个无关的“天气”选项，原有最优选项的优势 log-odds 会明显下滑。这说明候选项之间依然存在注意力交互，模型内部本质上是在做列表排序，选项并不是互相独立的。

第二是选项的物理顺序敏感性。由于自回归模型的单向注意力机制，排在后面的 Token 能看到前面的所有上下文。如果参考依据出现的位置发生变动，或者选项顺序调整，判断结果就会产生波动。只有把依据放在共享的 Prompt 上下文（State）中，注意力分配才会更加均衡。

有人会问，这和 2018 年的 BERT 分类器有什么区别？区别在于底座的常识与上下文容量。BERT 的上下文窗口通常只有 512 Tokens，词表较小，无法理解长篇代码、系统日志与长篇业务文档。Jev 建立在经历海量预训练的现代因果 Transformer 底座上，具备现代语义理解能力，只是摘掉了自回归生成的环节。

<!-- lang:en -->
Jev is not fully open source. Official reports plus community reproductions already make the path clear.

A normal LLM doing classification still runs an autoregressive decode, token by token. That often takes 2 to 5 seconds. Downstream still has to check whether the JSON closed. Jev generates zero tokens. After the prompt and candidate actions, the network does one forward pass. The output is a byproduct of a matrix multiply.

<!-- DIAGRAM: Latency and execution path comparison between single forward pass and autoregressive generation loops -->

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

<!-- DIAGRAM: Shared prefill KV-cache architecture powering parallel fan-out speculative evaluation -->

Why not drop any small model into this slot? Softmax scores are relative, not true probabilities. Uncalibrated models are overconfident. A wrong answer can still print 0.99. A production interceptor cannot trust that raw number.

Jev trains with RLCD, reinforcement learning for calibrated decisions. The objective is Expected Calibration Error, not pretty sentences. After sample checks and penalties, a reported 0.8 confidence should land near 80% accuracy.

Calibration does not erase attention structure.

First, irrelevant options interfere. Archer Hume added a dummy weather option after four valid ones. The winning option's log-odds dropped. Candidates still attend to each other. The model is ranking a list. Options are not independent.

Second, physical order matters. Causal attention lets later tokens see everything before them. Move the evidence, or shuffle options, and the answer can move. Put evidence in the shared prompt state so attention is more even.

People ask how this differs from a 2018 BERT classifier. The gap is world knowledge and context size. BERT is usually 512 tokens and a small vocabulary. It struggles with long code, logs, and business documents. Jev sits on a modern causal Transformer with large-scale pretraining. The generation loop is what got removed.
