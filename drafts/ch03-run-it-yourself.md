## 20行代码实测 / 20 Lines of Code

<!-- lang:zh -->
脱去概念包装，零 Token 生成机制在本地用 20 行 Python 脚本就能跑通。

我们加载参数量只有 5 亿的开源小模型 Qwen-2.5-0.5B-Instruct，给它一段带有候选标签的客服分类 Prompt。运行时绕过自回归生成循环，仅执行一次前向推导，提取末位对应候选标签的输出并做归一化：

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

如果让同一个 0.5B 模型按常规方式生成 JSON，需要自回归吐出数十个 Token，耗时通常在一两秒左右，且需要额外做 JSON 解析容错。直接提取末位 Logits 的耗时则可以压制在 30 毫秒以内。

在边缘计算场景中，通过 Cloudflare Workers 或 REST 接口调用 `typesafe/jev`，形态同样很精简：

```tsx
const result = await env.AI.run("typesafe/jev", {
  state: ticketContent,
  questions: { is_urgent: "noul", department: "choice", frustration: "score" }
});
```

跑完本地脚本与云端调用，技术层面的差异便清晰显现出来。

截取本地小模型的末位 Logits 虽然能拿到相对分数，但未校准的 Softmax 分数存在虚假自信问题。当模型遇到不确定的样本时，由于 Softmax 的指数放大效应，微小的 Logits 差距也会被拉大为 95% 以上的高置信度。

商业服务的主要工作，正是通过 RLCD 训练或大规模样本校准，将置信度与真实准确率拉齐。如果只是为了追求运行速度，本地部署小模型截取 Logits 已经足够可用；但如果要依赖置信度数值去做自动化拦截与放行，就需要自己在领域数据集上做温度缩放（Temperature Scaling）或后验校准，避免盲目放行错误分类。

<!-- lang:en -->
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
