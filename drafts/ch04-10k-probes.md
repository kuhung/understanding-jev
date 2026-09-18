## 万次压测数据说话 / 10,000 Probes

<!-- lang:zh -->
任何脱离真实网络抖动与极端边界的官方基准测试，在工程开发者眼中都是精心修饰的广告。官方宣传单上的亮眼数字遮蔽了长文本尾部延迟和并发塌陷的真实底细。笔者与同行需要的不是经过公关过滤的实验室报告，而是来自独立第三方的上万次高频探针。Archer Hume 针对 Jev 接口发起的万次实测，终于撕下了这一层营销面纱。

长文本扩展测试直接检验了推理引擎的底色。面对 80 倍的输入体积暴涨，传统大模型的自回归解码早已被首字延迟拖垮。Hume 的测试向同一个长状态连续投喂单个问题，记录了真实生产网络环境下的端到端响应耗时。

| 输入上下文（Tokens） | 中位数延迟（Median Latency） | 极速延迟（Fastest Latency） |
| :--- | :--- | :--- |
| 360 | 57.5 ms | 44.0 ms |
| 9,796 | 89.0 ms | 81.0 ms |
| 29,835 | 218.0 ms | 211.0 ms |

当输入上下文从 360 Tokens 飙升至接近 30,000 Tokens 时，系统耗时中位数仅从 57.5ms 增加到 218ms。80 倍的文本膨胀只换来了 150ms 左右的增量，极速状态甚至能稳定在 211ms。这彻底打破了大模型处理海量上下文必然陷入龟速的固有印象。

高并发问答场景展现了同样反常的平稳特性。测试脚本在保持短状态的前提下，将并发提问数量从 1 个持续拉升至 1,500 个。数据曲线给出了令人吃惊的平台期分布。

| 并发问题数量（Questions） | 中位数延迟（Median Latency） | 性能表现特征 |
| :--- | :--- | :--- |
| 1 - 100 | 70.0 - 100.0 ms | 几乎平直的水平线 |
| 500 | ~240.0 ms | 轻微上扬 |
| 1,500 | 610.0 ms | 队列开始出现排队积压 |

从 1 个问题增加到 100 个问题，系统的中位数延迟几乎是一条 70ms 至 100ms 的直线。只有当并发规模激增至 1,500 个查询时，整体耗时才抬升到 610ms。这种性能表现确凿证实了底层架构对 KV Cache 共享前缀的高效复用。系统没有为每个请求重复计算公共上下文，而是借由静态图或内存共享直接完成了多路并行分发。

<!-- DIAGRAM: Archer Hume 压测延迟曲线与 KV Cache 前缀复用拓扑 -->

亮眼的速度指标并不意味着推理质量完美无瑕。第三方开源复现实测揭开了一个被宣传物料刻意淡化的缺陷。Richard Becker 在开源项目 [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) 中，直接用 Qwen 2.5 7B 裸 Logits 与 Jev 进行了万次对齐判定。

官方宣称两者的决策一致性高达 86.6%，但 Becker 的实测结果仅有 73.8%。更为致命的是未校准模型表现出的虚假狂妄。当模型给出完全错误的分类预测时，其输出的 Softmax 置信度往往依然超过 90%。缺乏概率校准的小模型在单步决策中极度盲目自信，这会给没有任何回退重试机制的自动化流水线带来灾难。

```python
# https://github.com/rorshopping/jev-on-a-laptop
probs = torch.softmax(qwen_logits[:, target_token_ids], dim=-1)
pred_idx = torch.argmax(probs, dim=-1)
confidence = probs.max(dim=-1).values
# 预测错误时 confidence 仍常年高于 0.90
```

真实的工程检验必须回到端到端任务场景。社区开发者在浏览器自动化、移动端操作与音频处理中搭建了全链路探针。这些实测数据展示了小步反射机制在复杂业务流中的真实威力与代价。

在 [browser-use/jev-ultrafast](https://github.com/browser-use/browser-use) 项目中，自动化流水线耗时 7 秒便完成了 Google Flights 航班查询与预订。系统单次 DOM 判定与点击决策仅需 300ms 左右，仅在面对输入框需要组织自然语言文本时才唤醒重量级文本 LLM。在移动端项目 [droidrun/mobile-jev](https://github.com/droidrun/droidrun) 中，Agent 历经 9 次点击推进至 Uber 支付页面，全程耗时 21 秒，平均每步耗时 2.3 秒。

音频实时过滤项目 [santos-sanz/jev-audio-beeper](https://github.com/santos-sanz/audio-beeper) 将脏话消音判定延迟压缩到了 466ms，满足了准实时直播流的剪辑要求。与此同时，[awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) 在 macOS 自动化任务中将单步操作成本削减到了 0.0002 美元。数万次真实调用表明，将感知决策与文本生成解耦，是压低端到端延迟与云端开销的务实解法。

<!-- DIAGRAM: 混合 Agent 调用链路对比：传统纯自回归模型 vs Jev反射加LLM兜底 -->

极低的账单数字背后，隐藏着云服务厂商的定价障眼法。Jev 官方 API 依然沿用了大模型行业通用的“输出 Token 计费”名目。然而 Archer Hume 的逆向抓包与笔者的复算指出，其底层根本不存在自回归文本生成循环。

所谓输出 Token，纯粹是服务器在完成单次前向传播与分类打分后，按序列化 JSON 字符串的长度反向折算出的虚拟计量单位。服务商借用开发者熟悉的每千 Token 计费心智，掩盖了每次调用实质上就是一次固定成本的前向计算事实。这种定价策略锁定了极高的服务毛利率。频繁发起高频小步请求的开发者，在不知不觉中为这种折算游戏支付了额外溢价。

<!-- lang:en -->
Official benchmarks detached from network jitter and edge conditions are little more than polished marketing copy. Flawless laboratory metrics regularly mask tail latency degradation and concurrency collapse in production systems. Engineers struggling with runaway infrastructure bills require empirical data from thousands of unsanctioned probes rather than curated vendor brochures. Archer Hume subjected the Jev endpoint to 10,000 independent requests, uncovering the operational reality behind the hype.

Context scaling tests expose the true nature of any inference engine. Conventional autoregressive decoders buckle under first-token latency penalties when input volumes surge eightyfold. Hume tested Jev by streaming single queries against progressively larger state payloads to capture authentic round-trip latency.

| Input Context (Tokens) | Median Latency | Fastest Latency |
| :--- | :--- | :--- |
| 360 | 57.5 ms | 44.0 ms |
| 9,796 | 89.0 ms | 81.0 ms |
| 29,835 | 218.0 ms | 211.0 ms |

Expanding context from 360 tokens to nearly 30,000 tokens increased median latency from 57.5ms to just 218ms. An 80x surge in payload size added a mere 150ms of execution overhead, with optimal network runs holding at 211ms. These measurements refute the assumption that processing massive state windows must inevitably destroy real-time responsiveness.

High-concurrency query patterns revealed an equally surprising profile. By holding payload size constant and scaling simultaneous inquiries from 1 to 1,500, Hume observed a pronounced flatline response. The resulting figures document clear architectural boundaries.

| Concurrent Questions | Median Latency | Observed Characteristics |
| :--- | :--- | :--- |
| 1 - 100 | 70.0 - 100.0 ms | Virtually flat plateau |
| 500 | ~240.0 ms | Gentle upward slope |
| 1,500 | 610.0 ms | Request queuing bottlenecks emerge |

Between 1 and 100 concurrent questions, median latency stayed virtually flat between 70ms and 100ms. Response times only climbed to 610ms once concurrency reached 1,500 simultaneous queries. This behavior proves that the serving infrastructure relies heavily on shared prefix KV Cache reuse. Rather than recomputing common prompt state for every downstream inquiry, the backend dispatches parallel heads over a unified memory representation.

<!-- DIAGRAM: Archer Hume benchmark latency curve and KV Cache shared prefix reuse topology -->

Raw speed numbers tell only half the story. Independent open-source verification exposed a critical flaw that vendor marketing systematically downplays. In the repository [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop), Richard Becker pitted raw Qwen 2.5 7B logits directly against Jev across 10,000 runs.

While official marketing claims an 86.6% behavioral match rate, Becker measured an actual alignment of only 73.8%. Even more alarming is the model's uncalibrated overconfidence during inference. On misclassified samples, the raw softmax probability frequently exceeded 90%. Uncalibrated single-step models fail with utter certainty, posing severe risks to automated pipelines that lack fallback logic.

```python
# https://github.com/rorshopping/jev-on-a-laptop
probs = torch.softmax(qwen_logits[:, target_token_ids], dim=-1)
pred_idx = torch.argmax(probs, dim=-1)
confidence = probs.max(dim=-1).values
# Misclassifications consistently exhibit confidence above 0.90
```

Meaningful engineering evaluation requires validating complete agent workflows. Community developers deployed probes across browser automation, mobile app navigation, and audio processing pipelines. These integration benchmarks reveal the operational balance between reflex speed and structural overhead.

In [browser-use/jev-ultrafast](https://github.com/browser-use/browser-use), an agent completed a full Google Flights search and booking routine in 7 seconds. Individual DOM parsing and click decisions resolved in approximately 300ms, reserving large language models strictly for text inputs. Similarly, [droidrun/mobile-jev](https://github.com/droidrun/droidrun) advanced through an Uber booking flow to checkout in 21 seconds across 9 discrete taps, averaging 2.3 seconds per step.

Real-time audio filter [santos-sanz/jev-audio-beeper](https://github.com/santos-sanz/audio-beeper) achieved 466ms profanity censoring latency, keeping pace with live broadcast requirements. Meanwhile, [awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) reduced macOS desktop automation expenses to $0.0002 per step. Thousands of production traces prove that decoupling spatial perception from generation is the only practical path to sub-second UI agents.

<!-- DIAGRAM: Hybrid agent invocation pipeline comparison: Traditional autoregressive LLM vs Jev reflex with LLM fallback -->

Favorable billings conceal another subtle accounting tactic. The Jev commercial API continues to bill customers using conventional output token metrics. Reverse engineering by Archer Hume confirms that no autoregressive generation loop executes on the backend.

Output token counts are calculated retroactively by converting serialized response characters into synthetic token units. Providers leverage developer familiarity with token-based pricing to obscure what is fundamentally a fixed-cost single forward pass. This pricing structure protects vendor margins. Frequent sub-step calls quietly accumulate substantial billing markups for unsuspecting teams.
