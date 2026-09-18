## 四大设计模式 / Four Patterns

<!-- lang:zh -->
单独一个 Jev 分类器价值有限。把它作为二选一或三选一的银弹丢进复杂业务，很快就会触碰架构天花板。业务流转中交错纵横的规则，不可能靠单一的原子探针独立承担。组合使用模式才是生产落地的关键。

工程开发者受困于大模型的秒级延迟和高昂账单，往往急于寻找低成本替代品。但如果缺乏合理的拓扑编排，分类器不过是一个脆弱的概率玩具。笔者在拆解了大量工业级落地案例后，提炼出四种被真实流量反复验证的组合范式。这些模式将单步推断作为原子单元，在压榨出毫秒级响应的同时守住了系统的可靠性底线。

### 推测性扇出

面对长达数千字的用户长文档，系统往往需要同时抽取数十个维度的标签。如果用传统大模型挨个顺序提问，整体耗时会随问题数量线性暴增，Token 账单也会成倍膨胀。哪怕改用并行请求，数十次独立 Prefill 也会瞬间击穿显卡的计算带宽。推测性扇出模式正是为了在海量并发判定与有限计算预算之间求得平衡。

怎么用好这项模式？核心在于充分压榨推理引擎的前缀缓存机制，将长文本上下文在显存中仅 Prefill 计算一次。随后的二十到五十个离散问题并发挂载在同一份缓存指针之后，各自执行单个位置的轻量前向计算。五十个维度的批量提取耗时，在物理上被压缩到几乎与评估单个问题持平。

<!-- DIAGRAM: 推测性扇出架构：长文本单次 Prefill 固化共享 KV 缓存，50 个子问题并发前向计算，耗时与单问持平 -->

```typescript
// 共享前置长文本 KV Cache，一次网络往返并发求值多维标签
const profile = await jev.evaluateBatch({
  context: rawTicketContent,
  questions: { is_urgent: "noul", sentiment: "score", dept: { type: "choice", options: DEPTS } },
});
```
参见调用示例 [`examples/speculative-fanout.ts`](examples/speculative-fanout.ts)。

客服工单的全维度实时审查是该模式的经典战场。用户提交一条包含大量背景与投诉的长工单，网关必须在一秒内完成全景定性。系统并发提取工单紧急度、用户情绪焦躁分、责任归属部门与故障严重级。工单在进入排队队列前就已经被打满了结构化特征，下游路由引擎直接执行分发。

使用这项模式必须警惕显存暴涨与因果依赖陷阱。维持数十个并发问题的解码上下文，高并发流量极易耗尽显存配额。所有子问题之间必须在语义上严格正交。如果问题 B 的判定依赖问题 A 的输出结果，这种因果串联逻辑绝对无法放入同一个批次内推测扇出。

### 置信度门控

完全信任模型的输出是生产事故的常见源头，全量引入人工审核又会拖垮业务时效。分类器的输出只是概率分布的切片，不能直接视作不可动摇的真理。在任何需要自动化执行但容错成本极高的链路上，开发者都必须引入分级防御。置信度门控模式正是用于解决决策动作与执行权限之间的动态脱钩。

门控的核心原则是让预测结果决定业务动作，让置信度决定自动化等级。置信度高于 0.90 的请求直接放行或自动执行，无需人工介入。置信度落在 0.60 至 0.90 区间的请求暂缓落地，系统异步记录日志并触发告警抽检。置信度低于 0.60 时判定为高风险盲区，流水线直接熔断并无条件转交人工专席。

<!-- DIAGRAM: 置信度门控状态机：三档自动化安全阶梯与熔断转人工链路 -->

```typescript
// 动作由 answer 指引，执行权限由 confidence 分级裁决
if (result.confidence >= 0.90) return autoExecute(result.answer);
if (result.confidence >= 0.60) return logAndAlertAsyncReview(result.answer);
return circuitBreakToHuman(requestId);
```
参见调用示例 [`examples/confidence-gate.ts`](examples/confidence-gate.ts)。

高并发内容审核是置信度门控的典型舞台。面对每天数以千万计的论坛发言或即时评论，大语言模型审核的成本令人难以承受。Jev 在几十毫秒内输出判定结果与概率。极度确信的合规内容立刻展示，确信度极高的违规内容即刻拦截，唯独处于模糊地带的灰色发言被分流至人工复核池。

使用置信度门控的前提是模型具备经受住检验的校准度。如果直接拿未经 RLCD 训练的开源模型裸 Logits 跑这套逻辑，模型经常在判断错误时给出 0.98 的虚假高分，整套防御体系形同虚设。门控阈值也绝不能拍脑袋硬编码在代码里。团队需要定期抽取生产样本绘制预期校准误差曲线，根据业务对误杀与漏放的容忍度微调阈值。

### 复合评分

许多工程团队试图让模型直接评估一个综合指标，比如给一篇文章打出百分制的综合质量分。这种做法在实操中极不稳定，模型根本无法在单步矩阵运算中准确执行多维度的加权乘加。任何细微的提示词扰动，都会导致综合得分出现非理性的非线性漂移。面对多因子评估诉求，必须把特征提取与权重聚合彻底剥离。

怎么实现精确可控的复合评分？做法是让模型退回最底层的感知探针角色，只对单一维度给出 0 到 10 的离散分。所有的加权公式、惩罚系数与业务红线，全部交由后端的确定性代码处理。业务策略调整权重倾斜时只需修改本地配置，完全不需要重新微调或诱导模型。

<!-- DIAGRAM: 复合评分数据流：Jev 输出原子单项分与确定性代码加权风控矩阵的分工解耦 -->

```python
# 模型仅提供单项原子分，加权公式与安全硬规则由确定性代码执行
scores = {k: jev.score(text, metric=k) for k in ["clarity", "depth", "factuality"]}
composite_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
is_qualified = composite_score >= 80 and scores["factuality"] >= 6
```
参见评估脚本 [`examples/composite-scoring.py`](examples/composite-scoring.py)。

金融风控授信与社区内容质量排行是复合评分的天然土壤。以交易反欺诈为例，Jev 在毫秒级内输出设备环境异常分、收货地址跳变度与买家聊天急迫性三项原子读数。下游规则引擎调取历史违约率矩阵，将三项读数代入确定性公式算出全局欺诈指数。一旦设备异常分突破单项红线，系统可以无视加权总分直接触发拦截。

拆解原子维度时最忌讳语义重叠。如果文字流畅度与语病频次被拆成两个子维度，加权代码就会在无形中施加双重惩罚。每个原子指标在设计阶段必须追求严格的特征正交。各维度的权重分配需要基于历史标注数据离线拟合，切勿依赖开发者的主观直觉拍定常数。

### 分层分类

业务标签空间往往并非只有三五个选项，真实场景经常包含数千个精细分类。如果一次性把一千个候选词全部塞进枚举列表，注意力机制会在庞大的候选池中遭受剧烈稀释。候选项之间强烈的交叉注意力竞争会彻底摧毁独立性假设。当分类树深度超过两层且分支成百上千时，平铺单次分类必然走向失效。

分层分类借鉴了经典集束搜索思想。系统首先将平铺的庞大标签库重构成树状层级拓扑。第一轮前向计算只在一级大类中选出置信度最高的 Top-K 分支。随后顺着保留的分支并行挂载二级子类候选池，逐级剪枝收窄直至锁定叶子节点。

<!-- DIAGRAM: 分层分类集束搜索拓扑：顶层粗筛、动态剪枝与叶子节点细分路径 -->

```python
# 顶层先粗筛出 Top-2 大类，随后沿活跃分支并发检索细分类
top_roots = jev.top_k(product_text, candidates=ROOT_CATEGORIES, k=2)
sub_candidates = [leaf for root in top_roots for leaf in TAXONOMY[root]]
final_leaf = jev.evaluate(product_text, candidates=sub_candidates)
```
参见实现脚本 [`examples/hierarchical-search.py`](examples/hierarchical-search.py)。

电商平台的全量商品类目归类是分层分类的绝佳范例。平台品类叶子节点动辄超过两万个，直接单步打分会导致错误率飙升。系统先判定商品属于数码家电还是户外运动，再沿着胜出分支细化到电脑外设，最终锁定在客制化机械键盘。医疗领域的国际疾病编码分类同样依赖这种先大类后亚型的分层路由逻辑。

分层搜索最大的工程风险是早期剪枝带来的误差单向扩散。一旦顶层分类因为噪声干扰误剔除了正确的大类，后续的所有计算无论多么精确都注定南辕北辙。在实现该模式时，必须在每层保留足够的集束宽度，推荐集束大小不低于二到三。当下层所有候选分支的置信度集体雪崩时，必须触发回退重搜机制，切忌盲目相信单路径贪心策略。

<!-- lang:en -->
A single Jev classifier offers modest engineering value on its own. Dropping it into complex business pipelines as a silver bullet for binary routing quickly hits an architectural wall. The crisscrossing rules of production workflows cannot rest on isolated atomic probes. Composite orchestration patterns hold the real key to production deployment.

Developers suffocating under high LLM latencies and punishing cloud bills often reach for fast alternatives without a solid architectural plan. Without structural orchestration, a single-step classifier remains a fragile toy. We examined dozens of real-world production deployments to isolate four battle-tested design patterns. These patterns treat single-step inference as an atomic primitive, unlocking millisecond response times without sacrificing system reliability.

### Speculative Fan-out

Production systems frequently need dozens of discrete tags from a single long document. Running sequential prompts through a generative model causes total latency to multiply with every added question. Batching separate parallel calls still saturates GPU prefill bandwidth with redundant token parsing. Speculative fan-out resolves this dilemma by decoupling feature extraction from redundant prompt computation.

How does one implement this pattern cleanly? The trick lies in sharing prefix key-value caches across inference branches. Twenty to fifty discrete questions mount directly onto that shared cache pointer, each evaluating its candidate tokens in a single forward pass. Wall-clock latency for fifty dimensions remains nearly identical to evaluating a single question.

<!-- DIAGRAM: Speculative fan-out architecture: single prefill locks shared KV cache, 50 questions evaluate concurrently with near-constant latency -->

```typescript
// Shared KV cache on long context, batch evaluating multi-dimensional tags in one roundtrip
const profile = await jev.evaluateBatch({
  context: rawTicketContent,
  questions: { is_urgent: "noul", sentiment: "score", dept: { type: "choice", options: DEPTS } },
});
```
See implementation sample [`examples/speculative-fanout.ts`](examples/speculative-fanout.ts).

Customer support triage represents the premier battleground for speculative fan-out. When an angry customer submits a detailed ticket, the gateway must profile the payload within one hundred milliseconds. The engine simultaneously extracts urgency, frustration level, target department, severity rating, and refund intent. The ticket arrives in worker queues fully structured before downstream routing logic executes.

Engineers adopting this pattern must monitor memory footprints and respect causal limits. Maintaining fifty active decoders against a long context burns GPU memory under high concurrent traffic. Sub-questions must also remain strictly independent. If the decision for question B hinges on the output of question A, that dependent relationship cannot live inside the same fan-out batch.

### Confidence-Gated

Blind trust in classifier predictions triggers catastrophic production outages. Conversely, routing every single event to manual review destroys operational efficiency. A discrete prediction reflects a statistical probability slice rather than infallible truth. High-stakes pipelines require tiered defensive barriers that scale human intervention with operational risk.

The operational rule is straightforward: the predicted answer determines the action, while the confidence score governs automation rights. Requests with confidence scores above 0.90 execute automatically without human eyes. Predictions falling between 0.60 and 0.90 execute with audit logging and trigger asynchronous spot checks. Any prediction dropping below 0.60 activates a hard circuit breaker and transfers directly to human operators.

<!-- DIAGRAM: Confidence-gated state machine: three-tier automated safety ladder and human escalation fallback path -->

```typescript
// Predicted answer drives action; calibrated confidence dictates execution tier
if (result.confidence >= 0.90) return autoExecute(result.answer);
if (result.confidence >= 0.60) return logAndAlertAsyncReview(result.answer);
return circuitBreakToHuman(requestId);
```
See implementation sample [`examples/confidence-gate.ts`](examples/confidence-gate.ts).

High-throughput content moderation serves as the standard proving ground for confidence gating. Moderating millions of user comments with frontier generative models bankrupts infrastructure budgets. Jev evaluates comments in under one hundred milliseconds. Obvious spam gets dropped instantly, clear text passes through unimpeded, and borderline edge cases drop into human moderator queues.

This design pattern falls apart without rigorous probability calibration. Open-weight models running raw logits frequently report 0.98 confidence on completely incorrect outputs, blowing past defensive tripwires. Engineers should never hardcode probability thresholds from intuition. Production teams must chart expected calibration curves against real traffic and calibrate thresholds to match acceptable error margins.

### Composite Scoring

Teams often try forcing a neural model to assign a monolithic score to complex inputs, such as rating article quality on a 100-point scale. This strategy fails reliably in production. Single forward passes cannot compute arithmetic weighted sums across multiple shifting factors. Slight phrasing variations trigger wild, unpredictable swings in the overall score.

How do we achieve deterministic and auditable composite scoring? Strip the model of arithmetic responsibilities and treat it strictly as an atomic sensor. Use the score primitive to rate individual orthogonal dimensions on discrete intervals from 0 to 10. Downstream application code then handles weighted sums, penalty caps, and policy thresholds deterministically.

<!-- DIAGRAM: Composite scoring dataflow: atomic score outputs decoupled from deterministic rule weighting engine -->

```python
# Model emits atomic scores; deterministic code evaluates weights and hard safety rules
scores = {k: jev.score(text, metric=k) for k in ["clarity", "depth", "factuality"]}
composite_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
is_qualified = composite_score >= 80 and scores["factuality"] >= 6
```
See implementation sample [`examples/composite-scoring.py`](examples/composite-scoring.py).

Transaction fraud detection and search result ranking thrive under composite scoring. When an e-commerce platform flags a suspicious purchase, Jev supplies three atomic ratings: device risk, shipping address discrepancy, and account age instability. The fraud engine feeds these ratings into a logistic scoring formula to calculate approval limits. If the device risk hits a critical ceiling, hardcoded rules abort the checkout immediately regardless of the total score.

Atomic dimensions must maintain strict semantic orthogonality. If an engine scores both grammar flaws and readability errors as separate dimensions, downstream math doubles the penalty on identical textual defects. Feature design must eliminate overlapping metrics before deploying scoring rules. Dimension weights must also derive from statistical regression on labeled datasets rather than subjective developer guesses.

### Hierarchical Beam Search

Production taxonomy systems regularly manage thousands of fine-grained categories. Cramming one thousand candidate labels into a single prompt flattens the attention field and dilutes classification signal. Severe cross-attention competition between candidate tokens disrupts probability independence. When decision trees grow deep and wide, flat single-step classification breaks down.

Hierarchical classification adapts classical beam search to structured taxonomies. The system organizes target labels into a multi-tier tree hierarchy. The first forward pass evaluates only top-level root categories and retains the top two or three candidates. The system then mounts subcategory candidate pools onto active branches, pruning unpromising paths until reaching the leaf nodes.

<!-- DIAGRAM: Hierarchical beam search topology: root triage, dynamic branch pruning, and leaf classification paths -->

```python
# Root stage selects top-2 categories, child stage evaluates leaves across active branches
top_roots = jev.top_k(product_text, candidates=ROOT_CATEGORIES, k=2)
sub_candidates = [leaf for root in top_roots for leaf in TAXONOMY[root]]
final_leaf = jev.evaluate(product_text, candidates=sub_candidates)
```
See implementation sample [`examples/hierarchical-search.py`](examples/hierarchical-search.py).

E-commerce catalog classification provides a clear example of hierarchical routing. Retail platforms handle tens of thousands of leaf categories, making flat evaluation noisy and slow. The classifier first determines whether an item belongs to Electronics or Sporting Goods, narrows the path to Computer Hardware, and finally commits to Mechanical Keyboards. International Classification of Diseases (ICD-10) coding follows an identical multi-stage traversal across bodily systems, organs, and specific pathologies.

Early pruning introduces the danger of cascading errors. If early noise causes the model to discard the correct root category, downstream evaluation cannot recover. Implementations must maintain adequate beam width across intermediate stages, keeping at least two or three branches alive. When confidence scores drop sharply across all subcategories, the search algorithm must fall back to broader sweeps rather than forcing a greedy leaf selection.
