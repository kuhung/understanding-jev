## 拆底层 / Under the Hood

<!-- lang:zh -->
把 Jev 的引擎盖掀开来看，里面是一台精心校准的概率机器，不是什么黑魔法。工程界苦大模型延迟久矣。传统大模型处理分类或决策任务，必须启动自回归循环，逐个生成 Token。

整个生成过程动辄耗费两到五秒，开发者还得在下游祈祷 JSON 括号不要漏闭合。Jev 的生成步数为零。输入提示词与候选动作后，底层网络只执行单次前向传播，毫秒级输出在数学上仅仅是一次矩阵运算的副产物。

<!-- DIAGRAM: 单次前向传播与自回归生成循环在步数与延迟上的核心计算链路对比 -->

Jev 发布不到两小时，开源社区便拆解出两条复现路径。这套机制没有重写注意力层，完全建立在现成的因果模型底座之上。一线开发者迅速摸清了两种截然不同的工程取舍。

第一条路径是候选词 Logits 掩码投影。Harsha Gundal 发布的 [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) 验证了这种思路。模型在单次前向推理后提取序列最后一个位置的 logits，仅从数万词表中抽取目标候选项对应的 Token ID。局部 Softmax 归一化随即算出置信度，计算过程毫秒即成。

```python
# harshatheg/Qwen-2.5-1B-RLCD logits projection
logits = model(input_ids).logits[:, -1, :]
candidate_logits = logits[:, candidate_token_ids]
probs = torch.softmax(candidate_logits, dim=-1)
```

第二条路径来自 NLI 交叉编码器架构。AlexWortega 开源的 [AlexWortega/openjev](https://github.com/AlexWortega/openjev) 选用 Qwen3.5-4B 与 Qwen3.5-35B-A3B MoE 作为底座。该方案把环境状态拼装为前提，把候选动作转化为假设。分类头直接输出蕴含、中立与矛盾三分类得分，工程上只需取蕴含概率的极大值完成路由。

```python
# AlexWortega/openjev cross-encoder scoring
inputs = tokenizer(premise=state, hypothesis=action, return_tensors="pt")
logits = cross_encoder(**inputs).logits
entailment_score = logits[:, ENTAILMENT_IDX]
```

<!-- DIAGRAM: Logits 掩码投影与 NLI 交叉编码器双路径推理机制对比 -->

单次前向如果只能评估单个分支，依然无法应付生产环境的高吞吐诉求。Jev 依赖现代因果架构的前缀缓存共享机制化解了这一瓶颈。面对长达万字的业务上下文，模型在 Prefill 阶段仅计算一次并将其写入显存。

五十到一百个候选决策并行挂载在同一份 KV 缓存之后。显卡无需为每个候选项重新扫描长文档，只要并行计算少量候选 Token 的注意力。系统评估五十个维度的总耗时几乎等同于单次评估。

<!-- DIAGRAM: 基于共享 Prefill KV 缓存的分支并行扇出推理机制 -->

普通小模型为何不能直接套用这套逻辑？未经专门训练的开源模型普遍存在虚高的过度自信，表面给出 99% 的 Softmax 分数，实测真实准确率可能不及六成。工业级生产拦截系统无法依赖这种漂移严重的裸露数值。

Jev 引入了面向校准决策的强化学习（RLCD）。这项训练策略放弃了人类偏好对齐，也不关心输出文本的语言修辞。损失函数直接瞄准预期校准误差（ECE）进行最小化优化，确保 0.82 的模型置信度能够严谨对应 82% 的真实准确率。

严密的概率校准并未完全消除架构底层的不稳定。Archer Hume 开展的无关项扰动实验戳破了模型独立打分的假象。在既有的四个有效选项后追加一个与主题无关的天气选项，原最优候选项的优势 log-odds 竟从 +0.38 骤降至 +0.11。

这个落差证明候选项之间存在着不可忽视的交叉注意力交互。模型内部本质上在执行列表级排序，候选池中的干扰项会直接污染内部表征。开发者若误以为各选项是相互独立的事件，线上决策随时会发生不可预测的漂移。

笔者实测发现，选项放置的物理位置同样暴露了因果自注意力的结构偏见。把关键参考卡片放在选项末尾时录得 16/16 全对，平均置信度达到 0.88。一旦把该卡片调至最前或中间位置，命中数迅速滑落到 11 左右。

只有当参考卡片作为背景事实放入共享的状态前提中，系统才能恢复 48/48 的全对表现。输入格式的微小变动足以在单次前向传播中激起剧烈震荡。

<!-- DIAGRAM: 无关项扰动与选项位置偏移对决策准确率及置信度的影响曲线 -->

有人据此认为 Jev 不过是 2018 年 BERT 分类器的旧瓶装新酒。这种判断低估了底座能力对结构化决策的支撑。BERT 狭小的上下文窗口和早期的词表结构，根本看不懂 Kubernetes 资源拓扑与 Python 异常堆栈。

Jev 的骨架是经历万亿级 Token 预训练的现代因果 Transformer，并大概率采用了混合专家结构。它对 DOM 树、系统命令和工程代码的隐式理解，来自大规模预训练注入的世界知识。研发团队只是拆除了沉重的自回归排气管，将整台引擎的推力集中锁死在单步输出的概率槽位上。

<!-- lang:en -->
Pop the hood on Jev, and you find a finely calibrated probability engine rather than black magic. Engineering teams have spent years wrestling with the brutal latency of frontier models. Traditional language models tackle classification by firing up an autoregressive generation loop, spitting out tokens one by one.

That text-generation loop burns two to five seconds while developers pray that the downstream parser does not choke on unclosed JSON brackets. Jev sets the generation step count to zero. Given a context prompt and candidate actions, the underlying network executes a single forward pass, delivering millisecond outputs as a direct byproduct of matrix multiplication.

<!-- DIAGRAM: Latency and execution path comparison between single forward pass and autoregressive generation loops -->

Within two hours of Jev's release, the open-source community had reverse-engineered its core mechanics. Nobody needed to invent an alien attention mechanism. Practitioners immediately mapped out two distinct engineering paths built entirely on standard causal Transformer weights.

The first path relies on logit projection over candidate tokens. Harsha Gundal demonstrated this pipeline in [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD). The model runs a single forward pass, grabs the logits at the final sequence position, and extracts only the target token IDs out of the vocabulary. A quick local softmax normalizes the candidate logits into confidence scores in single-digit milliseconds.

```python
# harshatheg/Qwen-2.5-1B-RLCD logits projection
logits = model(input_ids).logits[:, -1, :]
candidate_logits = logits[:, candidate_token_ids]
probs = torch.softmax(candidate_logits, dim=-1)
```

The second path builds on Natural Language Inference cross-encoders. AlexWortega open-sourced this architecture in [AlexWortega/openjev](https://github.com/AlexWortega/openjev), using Qwen3.5-4B and Qwen3.5-35B-A3B MoE as backbones. This design frames the environment state as a premise and casts each candidate action as a hypothesis. The classification head outputs scores across entailment, neutral, and contradiction, picking the action with the maximum entailment probability.

```python
# AlexWortega/openjev cross-encoder scoring
inputs = tokenizer(premise=state, hypothesis=action, return_tensors="pt")
logits = cross_encoder(**inputs).logits
entailment_score = logits[:, ENTAILMENT_IDX]
```

<!-- DIAGRAM: Comparison between Logit Projection and NLI Cross-Encoder inference pipelines -->

Evaluating candidate actions one by one through single forward passes still hits a wall on production throughput. Jev clears this hurdle by leaning on prefix cache sharing across speculative branches. When processing massive context documents, the prefill stage runs exactly once and commits the key-value states to GPU memory.

Fifty to one hundred candidate decisions then fan out directly against that pinned KV cache. The GPU never re-reads the background context, computing attention only over the short candidate suffixes. Scoring fifty branching dimensions takes roughly the same wall-clock time as evaluating one.

<!-- DIAGRAM: Shared prefill KV-cache architecture powering parallel fan-out speculative evaluation -->

Why can off-the-shelf small models not pull off this trick directly? Standard open-weight models suffer from chronic overconfidence, often printing a 0.99 softmax score when their real-world accuracy barely clears 60 percent. Production safety filters and high-speed routers cannot gamble on uncalibrated confidence numbers.

Jev solves this distortion through Reinforcement Learning for Calibrated Decisions (RLCD). The training loop scraps human preference alignment and discards stylistic prose tuning. The loss function minimizes Expected Calibration Error (ECE) directly, forcing a 0.82 confidence score to represent an actual 82 percent success rate.

Even rigorous probability calibration cannot hide the mechanical cracks in the architecture. Archer Hume exposed this vulnerability through an irrelevant option perturbation experiment. Appending an irrelevant fifth option like weather to four valid choices caused the winning candidate's log-odds advantage to collapse from +0.38 to +0.11.

That collapse proves candidate options interact aggressively through cross-attention. The model performs listwise ranking rather than independent point-wise evaluations. Assuming candidate choices are isolated events will lead production systems straight into erratic routing errors.

Positional bias in causal self-attention creates another sharp fault line. My validation runs confirmed that placing the reference card at the end of the candidate list yielded a flawless 16 out of 16 run with 0.88 average confidence. Moving that card to the beginning or middle dropped accuracy down to 11 out of 16.

Accuracy bounced back to 48 out of 48 only when the reference facts were moved into the shared premise state. Minor formatting quirks trigger massive probability swings inside a single forward pass.

<!-- DIAGRAM: Decision accuracy and confidence degradation under distractor perturbation and option order shifts -->

Some skeptics dismissed Jev as nothing more than a 2018 BERT cross-encoder repackaged in modern marketing. That critique misses the immense representational depth required for software engineering decisions. BERT's tiny context windows and primitive tokenizers choke on Kubernetes manifests and Python stack traces.

Jev relies on a modern causal Transformer pre-trained on trillions of tokens, very likely backed by a mixture-of-experts architecture. Its grasp of DOM trees, system commands, and code logic comes from massive internet-scale pre-training. Its creators simply disconnected the sluggish autoregressive exhaust pipe and channeled raw model capacity straight into calibrated probability logits.
