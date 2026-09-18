## Jev 是什么 / What Is Jev

<!-- lang:zh -->
Jev 是一个被包装成新物种的统计分类器。它的工程价值真实存在，但围绕「全新 AI 品类」的营销话术需要适度降温。笔者在过去一年见过太多披着新外衣的传统方法，Jev 也是其中之一。它没有推翻任何计算理论，只是把过去属于传统分类任务的事情做到了极致廉价与极致快速。

发布初期，大量开发者以为这只是一场愚人节恶搞。创始人 Diogo Almeida 的名字无论拼写还是发音都极像 Anthropic 首席执行官 Dario Amodei。直到海外社区流出用 Jev 毫秒级操控经典游戏 DOOM 的实机录屏，技术圈才收敛了调侃。这位前 OpenAI 核心研究员曾经是 ChatGPT 与 RLHF 的共同发明人，他很清楚生成式架构在哪些场景下纯属过度工程。

产品名称取自经济学中的杰文斯悖论。当某种资源的利用效率大幅提升时，其总消耗量不会缩减，反而会呈指数级暴增。煤炭在工业革命时期如此，机器决策在当下的应用架构中同样如此。一旦单次推理决策的成本下降四百倍，开发者便会产生强烈的冲动，试图把业务链路里所有的 if-else 都塞进模型调用中。

<!-- DIAGRAM: 杰文斯悖论在 AI 决策流中的体现：推理成本暴跌四百倍引发的调用密度几何级增长 -->

Jev 的核心定位是机器对机器的状态评估。它不负责回答用户的提问，也从不生成半句人类可读的自然语言文本。在整套现代系统架构里，它的角色类似于数字传感器。上游服务将上下文数据抛给它，它在几十毫秒内返回一个离散标签，直接决定下游代码走哪条分支。

从官方披露的运行指标来看，它的定价策略极具攻击性。输入端每百万 Token 仅计费 0.042 美元，输出 Token 则完全免费。端到端请求延迟被压制在 70 到 500 毫秒区间。相比于大语言模型动辄数秒的等待和每次几美分的账单，这种开销让高频次判断逻辑终于具备了上线可能。

这种设计直接对应了认知科学中的双系统理论。人类大脑不会动用高级大脑皮层来计算如何眨眼，膝跳反应只由脊髓完成。现代大语言模型如同慢速而昂贵的深思系统，而 Jev 扮演的正是快速且廉价的脊髓反射。当系统面临海量前置过滤与路由分流时，让生成模型参与其中无疑是严重的资源浪费。

<!-- DIAGRAM: 认知双系统映射：脊髓反射（Jev 单步评估）与大脑深思（LLM 生成推演）的分工架构 -->

为了充当合格的反射中枢，Jev 舍弃了自回归文本生成，仅保留三种输出原语。第一种是 choice，用于在给定的字符串枚举列表中完成多选一路由。第二种是 score，用于在有序离散区间内打分，例如 0 到 10 的数值评分或情绪梯度。第三种是 noul，专门表达包含 true、false 与 unknown 的布尔概率评估。

每次输出背后都附带了经过严格校准的置信度概率。很多开发者吃过大模型结构化输出幻觉的苦头，那些模型给出的浮点概率常常盲目自信。Jev 的置信度数值直接映射概率分布，方便下游系统设立严格的安全阈值。一旦模型给出低置信度的判定，工程流水线就能立刻接管并触发熔断。

<!-- DIAGRAM: Jev 三种输出原语结构及其校准置信度矩阵 -->

在工程分发上，TypeSafe AI 选择了紧贴云厂商原生生态。开发者既可以通过 Cloudflare AI Gateway 请求 `typesafe/jev`，也可以在 Vercel 基础设施上调用 `typesafe-ai/jev`。配合官方 `@ai-sdk/typesafe-ai` 适配层，核心代码只需通过 `experimental_evaluate` 接口声明判断原语。

```typescript
import { experimental_evaluate } from '@ai-sdk/typesafe-ai';

const result = await experimental_evaluate({
  model: 'typesafe-ai/jev',
  prompt: contextText,
  primitive: { type: 'choice', options: ['allow', 'block', 'escalate'] },
});
```
参见调用示例 [`examples/eval-route.ts`](examples/eval-route.ts)。

把 Jev 捧上神坛大可不必。从技术本质来看，它并不是什么超越统计学习的神秘物种，它的能力边界极其狭窄。它无法代替大语言模型完成长文本创作、复杂逻辑推演或多轮对话记忆。只有在开发者被账单和超时警告逼到墙角时，这个剥离了所有生成幻象的分类器，才展现出冷酷的实用价值。

<!-- lang:en -->
Jev is a statistical classifier packaged as a novel artificial intelligence species. Its engineering utility is genuine, yet the marketing narrative hailing a brand-new AI category demands cold skepticism. We have witnessed too many classical algorithms repackaged in modern rhetoric over the past year. Jev overturns no laws of computation; it merely makes discrete classification radically cheap and fast.

When Jev first surfaced, many engineers dismissed the announcement as an elaborate April Fools prank. The founder's name, Diogo Almeida, sounds and looks uncannily similar to Anthropic CEO Dario Amodei. Community skepticism dissolved only after demo footage surfaced showing Jev controlling classic DOOM in real time. As a former OpenAI core researcher and co-inventor of ChatGPT and RLHF, Almeida understands where generative architectures waste compute on trivial routing.

The system takes its name from the economic concept known as the Jevons Paradox. When technological progress increases the efficiency of using a resource, total consumption skyrockets rather than declines. Coal followed this exact pattern during the industrial revolution, and programmatic decision-making follows it today. When single-step inference costs drop four hundred times, engineers face an irresistible urge to replace conditional logic with model evaluations.

<!-- DIAGRAM: Jevons Paradox in AI decision workflows: exponential invocation density triggered by a 400x cost drop -->

Jev focuses strictly on machine-to-machine state evaluation. It never converses with human users, nor does it generate sentences of natural language. Across a production architecture, it operates like a high-speed digital sensor. Upstream services pass contextual data to Jev, which returns a discrete label within milliseconds to branch execution logic.

The official operating metrics explain why this approach commands immediate engineering interest. Input tokens cost $0.042 per million, while output tokens are entirely free. End-to-end request latencies hover between 70 and 500 milliseconds. Compared to multi-second stalls and painful bills from standard LLMs, this profile makes high-frequency routing viable.

This architecture mirrors the dual-process model from cognitive psychology. The human body does not engage the cerebral cortex to calculate a reflex blink. Fast reflexes run through the spinal cord, while deliberate thought remains reserved for deep planning. Routing every incoming event through a full generative model burns budget without delivering engineering value.

<!-- DIAGRAM: Dual-system cognitive mapping: spinal reflex (Jev single-step evaluation) versus cerebral deliberation (LLM generation) -->

To serve as an effective reflex mechanism, Jev strips away autoregressive text generation in favor of three discrete primitives. The first is `choice`, selecting a single option from an explicit string enum array. The second is `score`, evaluating inputs against ordered discrete scales like numerical ranges or sentiment gradients. The third is `noul`, outputting calibrated probabilities for boolean truth states.

Every prediction ships with an explicitly calibrated confidence probability. Production teams often battle hallucinations caused by uncalibrated floating-point logits from large language models. Jev maps probabilities directly to empirical certainty so downstream pipelines can enforce strict guardrail thresholds. If an evaluation score drops below acceptable tolerances, system interceptors can immediately trigger fallback paths.

<!-- DIAGRAM: Jev output primitives schema with calibrated confidence scoring matrix -->

TypeSafe AI distributes Jev directly through major cloud edge platforms. Engineers can route queries through Cloudflare AI Gateway via `typesafe/jev` or tap into Vercel AI Gateway using `typesafe-ai/jev`. Paired with the `@ai-sdk/typesafe-ai` package, evaluating state requires only a concise call to `experimental_evaluate`.

```typescript
import { experimental_evaluate } from '@ai-sdk/typesafe-ai';

const evaluation = await experimental_evaluate({
  model: 'typesafe-ai/jev',
  prompt: contextPayload,
  primitive: { type: 'choice', options: ['allow', 'block', 'escalate'] },
});
```
See integration example [`examples/eval-route.ts`](examples/eval-route.ts).

Deifying Jev would be an engineering mistake. It is not an omnipotent reasoning engine, and its operational boundaries are deliberately narrow. It cannot draft documentation, synthesize creative writing, or maintain multi-turn dialogue state. When latency budgets expire and cloud bills threaten margins, a stripped-down classifier offers pragmatic relief.
