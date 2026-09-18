## 四种设计模式 / Four Patterns

<!-- lang:zh -->
在实际工程落地中，单步判别模型通常需要与规则引擎及大模型组合使用。以下是四种常见的落地模式。

### 推测性扇出

面对数千字的用户工单或长文档，系统往往需要同时提取多个维度的标签。如果用传统大模型挨个提问，耗时与费用都会线性增加。

推测性扇出模式利用了前缀缓存共享机制：长文本上下文在显存中只做一次 Prefill 计算，后续十几个离散问题并发挂载在同一份缓存上，各自执行轻量前向计算。多维度的提取耗时被压缩到接近单次评估水平。

<!-- DIAGRAM: 推测性扇出架构：长文本单次 Prefill 固化共享 KV 缓存，50 个子问题并发前向计算，耗时与单问持平 -->

```tsx
// 共享前置长文本 KV Cache，一次网络往返并发求值多维标签
const profile = await jev.evaluateBatch({
  context: rawTicketContent,
  questions: { is_urgent: "noul", sentiment: "score", dept: { type: "choice", options: DEPTS } },
});
```

并发提问的子问题在语义上必须相对独立。如果问题 B 的判定依赖问题 A 的结果，就无法放入同一个批次内并行计算。

### 置信度门控

门控模式的核心原则是：让预测结果决定业务动作，让置信度决定自动化等级。

<!-- DIAGRAM: 置信度门控状态机：三档自动化安全阶梯与熔断转人工链路 -->

置信度高于 0.90 的请求直接自动执行；置信度在 0.60 到 0.90 之间的请求暂缓执行，异步记录日志并触发抽检；低于 0.60 时判定为不确定区域，直接转交人工或更强模型处理。

```tsx
// 动作由 answer 指引，执行权限由 confidence 分级裁决
if (result.confidence >= 0.90) return autoExecute(result.answer);
if (result.confidence >= 0.60) return logAndAlertAsyncReview(result.answer);
return circuitBreakToHuman(requestId);
```

高并发内容审核是典型场景。绝大多数确信合规或确信违规的内容可以瞬间处理，只有处于模糊地带的请求才进入人工复核池。前提是模型具备可靠的概率校准，阈值需要根据误杀与漏放的容忍度定期调整。

### 复合评分

很多团队尝试让模型直接输出一个百分制的综合质量分，这种做法往往不稳定，细微的 Prompt 扰动就会导致综合分数剧烈漂移。

复合评分的做法是让模型只对单一维度给出 0 到 10 的离散分，加权公式与安全硬规则全部交由后端确定性代码执行。调整业务策略时只需修改本地权重配置，不需要重新调整提示词。

```python
# 模型仅提供单项原子分，加权公式与安全硬规则由确定性代码执行
scores = {k: jev.score(text, metric=k) for k in ["clarity", "depth", "factuality"]}
composite_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
is_qualified = composite_score >= 80 and scores["factuality"] >= 6
```

### 分层分类

当分类标签数量达到数百甚至数千个时，一次性把全部选项塞进枚举列表会导致注意力稀释。

分层分类参考了树状检索思路：先在顶层大类中选出 Top-K 分支，再沿着胜出的大类细化到二级子类，逐级剪枝收窄。

```python
# 顶层先粗筛出 Top-2 大类，随后沿活跃分支并发检索细分类
top_roots = jev.top_k(product_text, candidates=ROOT_CATEGORIES, k=2)
sub_candidates = [leaf for root in top_roots for leaf in TAXONOMY[root]]
final_leaf = jev.evaluate(product_text, candidates=sub_candidates)
```

例如电商商品归类，先判定属于数码还是户外，再细化到具体类目。实现时建议每层保留二到三个候选分支，避免早期误剪枝导致后续全部走偏。

<!-- lang:en -->
In production, a single-step discriminator usually sits with rules and a large model. Four patterns show up often.

### Speculative fan-out

A long ticket or document often needs many labels at once. Asking an LLM one question after another grows time and cost linearly.

Fan-out reuses prefix cache. Prefill the long context once. Hang a dozen discrete questions on that cache and run light forwards in parallel. Multi-label extract time stays close to a single call.

<!-- DIAGRAM: Speculative fan-out architecture: single prefill locks shared KV cache, 50 questions evaluate concurrently with near-constant latency -->

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

<!-- DIAGRAM: Confidence-gated state machine: three-tier automated safety ladder and human escalation fallback path -->

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
