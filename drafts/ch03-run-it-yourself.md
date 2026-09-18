## 20 行脚本跑一遍 / Run It Yourself

<!-- lang:zh -->
所有技术判断，跑一遍才算数。面对铺天盖地的单步决策宣传，一线开发者最该做的就是把代码拉到本地敲击回车。脱去所谓的革命性包装，这种零 Token 生成机制在本地只需二十行 Python 脚本就能跑通。笔者在 Apple Silicon 设备上进行了实测，端到端推断耗时稳定在三十毫秒以内。

本地最小验证的实现原理极其朴素。我们直接加载参数量只有五亿的开源模型 Qwen-2.5-0.5B-Instruct，给它一段带有候选标签的客服工单分类提示词。运行时彻底绕过消耗巨大的自回归生成循环，仅仅执行一次基础的前向推导。程序直接提取上下文末位对应候选标签的原始输出，经过局部归一化计算得出分值。

<!-- DIAGRAM: 本地单次前向传播截取候选 Token Logits 并在末位进行局部 Softmax 归一化的计算流程 -->

最核心的运算逻辑只有三行张量切片。

```python
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_ids]
    probs = torch.softmax(logits, dim=-1)
```

完整可执行代码存放在 [`scripts/fast_decide.py`](scripts/fast_decide.py)。在终端中执行命令 `uv run --with torch --with transformers python3 fast_decide.py` 即可原地检验。整个运行过程完全没有生成任何新词元，本地显存占用几乎可以忽略不计。

当业务逻辑迁移到边缘计算场景，调用形态同样非常精简。以 Cloudflare Workers 接入 `typesafe/jev` 为例，开发者不再需要费尽心机编写输出格式防穿透提示词。请求体直接传入状态文本与问题字典，一次性完成三个维度的离散探测。紧急度由 noul 输出二元概率，科室分配由 choice 挑出分类，用户愤怒度由 score 给出有序评级。

边缘网关调用的核心接口极为扁平。

```typescript
const result = await env.AI.run("typesafe/jev", {
  state: ticketContent,
  questions: { is_urgent: "noul", department: "choice", frustration: "score" }
});
```

完整的边缘处理逻辑收录在 [`scripts/cloudflare-worker.ts`](scripts/cloudflare-worker.ts)。如果不依赖云平台运行时，直接使用 `curl` 向 REST API 发送包含 state 与 questions 的 JSON 请求，也能获得相同结构。底层模型利用同一份前缀缓存并行评估多个问题，网络传输耗时几乎占据了整体延迟的全部。

<!-- DIAGRAM: 未经校准的本地裸 Logits 极度自信与经过 RLCD 校准的置信度可靠性分布对比 -->

跑完这两组代码，真正的技术分野才会浮现出来。许多工程师容易产生一种错觉，认为截取本地小模型的末位打分就能轻易取代商用决策接口。实测证明，未经统计校准的 Softmax 概率分布存在极度严重的过度自信缺陷。当模型面对未知语义发生严重误判时，依然会若无其事地给出高达百分之九十九的置信度。

商用决策引擎的真正壁垒不是那二十行提取得分的胶水代码。它的技术核心是 RLCD 这套面向决策校准的强化学习训练过程。算法通过长期的经验误差惩罚，强行将模型输出的置信度与真实世界的准确率拉齐。直接把未经校准的裸打分放进生产网关，自动化流程迟早会在高并发下遭遇静默灾难。

<!-- lang:en -->
Every architectural claim remains hollow until you execute the code yourself. Faced with breathless hype around single-step reasoning, real engineers open a terminal and test the baseline. Strip away the proprietary branding, and the underlying mechanism takes barely twenty lines of Python. On Apple Silicon hardware, end-to-end execution finishes comfortably under thirty milliseconds.

The logic behind this minimal local harness is refreshingly straightforward. We load Qwen-2.5-0.5B-Instruct, a compact open model, alongside a basic customer support ticket classification prompt. The execution completely skips the compute-heavy autoregressive generation loop. We run a single forward pass, slice the final token logits for candidate letters, and apply a local softmax.

<!-- DIAGRAM: Computation graph of local single forward pass slicing candidate token logits for normalized probabilities -->

The operational core reduces to three lines of tensor manipulation.

```python
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_ids]
    probs = torch.softmax(logits, dim=-1)
```

The complete script is available in [`scripts/fast_decide.py`](scripts/fast_decide.py). Running `uv run --with torch --with transformers python3 fast_decide.py` reproduces the benchmark on any modern laptop. The routine consumes negligible memory and emits zero new tokens.

Moving this evaluation to an edge environment preserves the exact same design philosophy. Calling `typesafe/jev` inside Cloudflare Workers eliminates tedious prompt engineering and JSON extraction schema checks. A single payload transmits the conversation state alongside a question map to perform three distinct classifications simultaneously. The service resolves urgency via noul, routes departments via choice, and scores user frustration on an ordinal scale.

The dispatch routine in edge handlers remains remarkably compact.

```typescript
const result = await env.AI.run("typesafe/jev", {
  state: ticketContent,
  questions: { is_urgent: "noul", department: "choice", frustration: "score" }
});
```

The production wrapper is documented in [`scripts/cloudflare-worker.ts`](scripts/cloudflare-worker.ts). Issuing a standard `curl` request with an identical JSON payload yields the exact same discrete outputs over raw HTTP. Because the server shares prompt key-value caches across all parallel questions, overall duration reflects network round-trip time.

<!-- DIAGRAM: Calibration curve contrasting raw overconfident softmax scores against RLCD aligned probabilities -->

Running both implementations exposes where the real engineering divide begins. Many teams prematurely assume that slicing uncalibrated logits from a tiny model replaces an enterprise decision endpoint. In reality, uncalibrated softmax scores suffer from pathological overconfidence. When a base language model encounters ambiguous phrasing and hallucinates an incorrect label, it still reports a ninety-nine percent probability.

The defensive moat of a commercial decision engine never rested on twenty lines of Python tensor slicing. The real barrier is reinforcement learning from calibrated decisions, known as RLCD. By penalizing calibration errors during training, the process aligns numerical confidence with true historical accuracy. Feeding raw uncalibrated probabilities directly into automated production gates invites silent operational failure under high load.
