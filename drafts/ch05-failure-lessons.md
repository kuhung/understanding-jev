## 失败课 / Failure Lessons

<!-- lang:zh -->
知道硬上限在哪，比知道跑多快更有工程价值。很多团队在基准测试里看到几十毫秒的响应就急于引入生产，随后在极端边界用例前被撞得头破血流。任何试图把单步分类器当成全能大模型的举动，都是对算力规律的无视。笔者梳理了五个经过严格复测的系统性失败，借此看清单步决策的真实边界。

### 无思考链的推理崩溃

单步前向网络能做多层因果推演吗？在钓鱼邮件基准测试 [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) 中，两千封充满复杂社交工程陷阱的真实攻击邮件揭开了残酷底细。面对隐藏在多层转折与伪造身份背后的诱骗逻辑，Claude Haiku 4.5 的判定准确率显著压制了 Jev。缺乏思考链的 Jev 出现了严重的漏判。

这种漏判的本质是计算路径被强行截断。大语言模型依靠自回归 Token 逐步展开推导，在前序输出中铺设因果支架。Jev 必须在一次矩阵乘法中完成特征提取与终审裁决。当欺诈逻辑嵌套超过两层时，单步打分不可避免地退化为随机猜测。

<!-- DIAGRAM: 钓鱼邮件基准测试漏判对比：Claude Haiku 4.5 思考链因果推演与 Jev 单步判定在多层社交工程攻击下的表现差距 -->

```python
# 单步评估缺乏中间推理步，多层逻辑直接击穿前向计算
decision = jev.evaluate(email_body, primitive={"type": "noul", "question": "Is this phishing?"})
```
参见评测脚本 [`eval/phishing-eval.py`](eval/phishing-eval.py)。

### 候选项顺序敏感

候选项的排列顺序会扭曲最终判定吗？Archer Hume 在针对 Jev 提示词布局的万次扰动测试中，捕获到了令人不安的统计学偏差。当关键判定依据被置于候选项之后呈现时，模型获得了 16/16 的全对战绩。一旦将该关键依据挪动到最前或者中间段落，正确率立即滑落至 11 到 12。

现代因果 Transformer 的单向注意力机制决定了靠后 Token 能够汇聚前方所有的上下文特征。如果核心线索出现得太早，注意力权重会在长序列传播中被持续稀释。候选项作为解码终点的锚点，其相对位置直接左右了特征池化的效果。调用方必须严格规范 Prompt 的物理排版，否则输出结果会随着输入模板的随机抖动而剧烈失准。

<!-- DIAGRAM: 提示词位置敏感性实验：关键信息位于候选项前、中、后时的注意力衰减与正确率分布 -->

### 不相关备选项独立性被破坏

统计学中的不相关备选项独立性（IIA）假设，在 Jev 内部遭遇了破坏。在标准的多选一测试场景中，测试者仅仅向枚举列表中加入了一个完全无关的「天气」选项。已有核心业务分支之间的相对对数几率比（log-odds），瞬间下滑了 0.28。多余选项虽然没有被最终选中，却暗中稀释并重塑了既定选项的概率分布。

为什么一个无关候选项会篡改其他分支的相对权重？原因在于 Jev 底层依赖现代 Transformer 的全量注意力交互，候选项 Token 之间并非孤立打分。候选池内部的注意力竞争，直接重构了最终投影层的几何空间。在金融风控或医疗分级等统计严格场景中，这种无法消除的系统偏差必须被纳入误差预算。

<!-- DIAGRAM: IIA 独立性破坏效应：注入无关天气选项导致的注意力竞争与已有候选项 log-odds 偏移 -->

### 裸 Logits 的置信度虚高陷阱

开源模型提取出的原始 Softmax 分数能直接当成置信度使用吗？实测表明，在完全一致的输入下，Qwen 7B 裸读出的 Logits 与 Jev 商业接口的一致性仅有 73.8%。未经 RLCD（校准强化学习）训练的开源模型普遍存在严重的过度自信倾向。模型常常给出超过 0.95 的置信度读数，对应的实际标签判定却彻底错误。

直接将未校准的裸 Logits 接入自动化流水线是极其危险的工程实践。业务网关依赖高置信度做全自动放行，只在低置信度时才触发熔断转人工。虚高的概率读数会彻底瘫痪这套防护网，导致恶意识别在绿灯状态下长驱直入。缺乏校准技术的自建小模型，在真实生产环境里不过是一个盲目自大的定时炸弹。

<!-- DIAGRAM: 预期校准误差（ECE）对比：Jev 经 RLCD 校准的置信度曲线 vs 开源模型裸 Logits 的过度自信漂移 -->

```python
# 裸 Softmax 产生虚高假象，无法代表真实胜率
probs = torch.softmax(qwen_logits[:, candidate_tokens], dim=-1)
confidence = probs.max(dim=-1).values
# 预测错误时 confidence 仍常年高于 0.90
```
参见校准差异对比脚本 [`eval/calibration-check.py`](eval/calibration-check.py)。

### 零自由文本生成能力

许多初次接触 Jev 的工程师容易对它的能力产生不切实际的幻想。Jev 在物理层面切断了自回归解码循环，连一整句人类语言都无法拼凑。它永远无法承担错误日志解读、异常代码修复或自然语言回复等生成式工作。在现代软件工程流水线中，它只能担任裁判员，绝无可能下场充当运动员。

这种极端的结构精简既是它获得毫秒级速度的原因，也是它无法逾越的能力鸿沟。如果业务网关在拦截恶意请求后需要向用户解释被封禁的理由，Jev 必须立刻将上下文移交给后续的生成式大模型。企图在这个架构上微调出文本生成能力，无异于在拖拉机底盘上安装火箭引擎。认清这一分工边界，能帮团队省去数周无意义的架构试错。

### 单步前向的算力硬顶

这五个失败案例并非训练数据不足导致的临时工程瑕疵。从多层欺诈推理的崩溃，到候选项注意力交叉污染，共同根源都在于单步前向传播的计算容量上限。单个前向网络只能在固定深度的矩阵变换中处理信息。工程技巧与提示词调优再精妙，也无法打破非自回归结构的数学极限。

工程落地的核心永远是边界判定。如果业务逻辑涉及多跳推导、文本合成或严格的概率隔离，强行采用单步决策必然导致系统在生产环境频繁失控。承认单步网络的局限，是构建可靠混合架构的第一步。在它无法胜任的领域，开发者依然只能老老实实为自回归大模型的延迟与算力买单。

<!-- lang:en -->
Knowing where the hard ceiling lies is far more valuable to engineering than knowing how fast a model runs. Teams dazzled by sub-100-millisecond benchmark numbers often rush into deployment, only to suffer painful outages against real-world edge cases. Attempting to treat a single-step classifier as a general-purpose reasoning engine violates basic computational constraints. We assembled five systematic failures that strip away the marketing facade.

### Reasoning Collapse Without Chain-of-Thought

Can a single forward pass resolve nested causal traps? In the phishing benchmark [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench), evaluators tested two thousand real-world attack vectors packed with deceptive social engineering. Claude Haiku 4.5 decisively outperformed Jev whenever emails introduced deceptive context shifts and forged identities. Lacking chain-of-thought scratchpads, Jev suffered severe false negative rates across the dataset.

This failure pattern reflects an abruptly truncated computation path. Large language models assemble intermediate deductions token by token, building causal scaffolding across multiple autoregressive steps. Jev must execute token feature extraction, intent categorization, and final adjudication inside a single forward pass. Once deceptive premises branch across multiple tiers, single-step scoring degrades into statistical guesswork.

<!-- DIAGRAM: Phishing detection failure rate comparison: Claude Haiku 4.5 chain-of-thought deduction versus Jev single-step false negatives under social engineering attacks -->

```python
# Single forward pass lacks scratchpad tokens, truncating multi-step causality
decision = jev.evaluate(email_body, primitive={"type": "noul", "question": "Is this phishing?"})
```
See evaluation harness [`eval/phishing-eval.py`](eval/phishing-eval.py).

### Candidate Order Sensitivity

Does changing option order destabilize classification outcomes? Archer Hume applied systematic prompt perturbations to Jev and captured substantial statistical drift. Placing critical decision evidence directly after candidate options yielded an unblemished 16 out of 16 classification score. Shifting that identical evidence block to the beginning or middle reduced accuracy down to 11 and 12 out of 16.

Causal attention in modern Transformer architectures allows trailing tokens to aggregate features across the entire preceding context window. Presenting key clues prematurely causes attention weights to dissipate across extensive sequence lengths. Because candidate tokens anchor the classification head, their physical position dictates pooling fidelity. Callers must enforce rigid prompt layouts to protect downstream logic against template jitter.

<!-- DIAGRAM: Prompt layout sensitivity test: attention weight dissipation and accuracy drops when shifting evidence positions -->

### Irrelevant Alternatives Break Independence

The econometric principle of Independence of Irrelevant Alternatives breaks down inside Jev. In standard multiple-choice configurations, Archer Hume injected a single irrelevant candidate option concerning local weather conditions. The relative log-odds between existing operational choices dropped by 0.28 immediately. Even though the dummy option was never chosen, its presence distorted the probability distribution of genuine candidates.

Why does an irrelevant candidate alter competing probabilities? Jev depends on full self-attention across candidate tokens, precluding isolated candidate evaluations. Attention competition within the candidate array reorganizes the geometry of the final projection layer. Systems operating in audit-heavy domains like automated underwriting or healthcare triage must formally budget for this persistent bias.

<!-- DIAGRAM: Breakdown of IIA: candidate cross-attention competition and log-odds drift following dummy option injection -->

### The Trap of Overconfident Raw Logits

Can self-hosted services safely feed raw open-weight logits into Softmax functions? Benchmark audits demonstrate that uncalibrated logits from Qwen 7B agree with Jev commercial endpoints only 73.8% of the time. Open models running without Reinforcement Learning from Calibrated Decisions exhibit pronounced overconfidence. Such models routinely report confidence values above 0.95 on misclassified samples.

Wiring uncalibrated logits into production pipelines introduces catastrophic risk. Production gateways rely on high probability readings for automated approvals, reserving low scores for human escalations. Artificially elevated probabilities compromise these defensive barriers and pass malicious traffic undetected. Self-hosted models lacking calibrated post-training operate as dangerous liabilities within critical production paths.

<!-- DIAGRAM: Calibration drift analysis: RLCD-trained alignment curve versus raw open-weight overconfidence dispersion -->

```python
# Raw softmax probabilities produce dangerous overconfidence without RLCD
probs = torch.softmax(qwen_logits[:, candidate_tokens], dim=-1)
confidence = probs.max(dim=-1).values
# Predictions frequently report over 0.90 confidence while picking wrong tokens
```
See calibration probe script [`eval/calibration-check.py`](eval/calibration-check.py).

### Zero Free-Text Generation

Engineers evaluating Jev often harbor unrealistic expectations regarding natural language output. Jev physically removes the autoregressive decoding loop and cannot generate a single grammatically complete sentence. It cannot parse error stacks into explanations, patch defective source code, or draft human-readable replies. Within production software architectures, Jev serves strictly as an umpire and can never enter the field of play.

This architectural reduction yields millisecond latencies while enforcing an unyielding capability boundary. If an operational gateway must provide a user-facing explanation when rejecting a request, Jev must hand the context over to an LLM. Attempting to fine-tune generative conversational capabilities onto this architecture resembles strapping rocket thrusters to a tractor frame. Establishing this architectural boundary spares teams weeks of fruitless experimentation.

### The Hard Bound of Single Forward Passes

These five failures do not represent transient training bugs waiting for expanded datasets. From multi-tiered phishing vulnerabilities to attention contamination between candidates, every defect originates in the compute bound of a single forward pass. A single forward pass executes a bounded tensor transformation across a fixed model depth. No prompt engineering trick or loss function tweak can transcend this non-autoregressive ceiling.

Sound engineering practices demand respecting operational boundaries. Forcing single-step models into domains requiring multi-hop logic, text synthesis, or strict probability isolation invites production instability. Acknowledging the inherent limits of reflex networks represents the first requirement of dependable hybrid architectures. Where single-step models reach their ceiling, developers must still pay the latency and compute bills of full autoregressive generation.
