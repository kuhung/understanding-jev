## 压测数据分析 / Benchmark Data

<!-- lang:zh -->
脱离真实环境的宣传指标往往不够客观。Archer Hume 针对 Jev 官方接口发起了上万次测试，记录了其在长文本与高并发场景下的实际表现。

在长文本扩展测试中，测试脚本向同一个长文本上下文投喂单个问题，记录端到端耗时：

| 输入上下文（Tokens） | 中位数延迟（Median Latency） | 极速延迟（Fastest Latency） |
| -------------------- | ---------------------------- | --------------------------- |
| 360                  | 57.5 ms                      | 44.0 ms                     |
| 9,796                | 89.0 ms                      | 81.0 ms                     |
| 29,835               | 218.0 ms                     | 211.0 ms                    |

当输入从 360 Tokens 增加到近 30,000 Tokens 时，中位数耗时从 57.5ms 增加到 218ms。文本量增长了约 80 倍，延迟仅增加约 160ms。这符合非自回归模型的特征：没有长文本逐字解码的累加耗时，主要耗时都在一次性的 Prefill 阶段。

在高并发问答测试中，固定短文本上下文，将并发问题数量从 1 逐步拉升至 1,500 个：

| 并发问题数量（Questions） | 中位数延迟（Median Latency） | 表现特征             |
| ------------------------- | ---------------------------- | -------------------- |
| 1 - 100                   | 70.0 - 100.0 ms              | 耗时相对平稳         |
| 500                       | ~240.0 ms                    | 延迟温和上升         |
| 1,500                     | 610.0 ms                     | 出现排队与积压       |

从 1 个问题增加到 100 个问题，延迟基本保持在 70ms 到 100ms 区间。当并发激增至 1,500 个时，耗时上升到 610ms。数据反映出底层复用了 KV Cache 共享前缀，不需要为公共上下文重复做计算。

速度快并不代表判断质量完美。Richard Becker 在开源项目 [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) 中，使用 Qwen 2.5 7B 裸 Logits 与 Jev 官方接口进行了对比：

官方宣传两者决策一致性可达 86.6%，但 Becker 的实测结果约为 73.8%。实测也证实了未校准模型的盲目自信问题：当 Qwen 预测错误时，输出的 Softmax 置信度依然经常高于 0.90。

```python
# https://github.com/rorshopping/jev-on-a-laptop
probs = torch.softmax(qwen_logits[:, target_token_ids], dim=-1)
pred_idx = torch.argmax(probs, dim=-1)
confidence = probs.max(dim=-1).values
# 预测错误时 confidence 仍常高于 0.90
```

关于输出 Token 的计费方式：Jev 官方接口沿用了行业通用的“输出 Token”计费口径。但从技术机制来看，底层只执行了单次前向计算，并不存在自回归逐字生成。最终返回的几个标签字节被折算成虚拟 Token，本质上是厂商为了迎合开发者熟悉的计费习惯，按次计算服务成本即可。

<!-- lang:en -->
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
