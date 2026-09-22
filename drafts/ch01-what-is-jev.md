## Jev 是什么 / What Is Jev

<!-- lang:zh -->
Jev 本质上是一个面向状态评估的统计分类器。大模型擅长生成，Jev 专注于判别。它把传统分类任务用大模型处理时既慢又贵的痛点，做到了低成本和高速度。

产品发布初期，不少开发者以为是恶搞，因为创始人 Diogo Almeida 的名字和 Anthropic 首席执行官 Dario Amodei 读音相近。直到社区看到用 Jev 毫秒级操控经典游戏 DOOM 的录屏演示，技术圈才开始认真讨论它到底能用来做什么。

它的名字取自经济学中的杰文斯悖论。当某种资源的利用效率大幅提升时，其总消耗量往往不会缩减，反而会成倍增长。一旦单次模型决策的成本下降上百倍，系统里原本写死 if-else 的地方，可能都会考虑接入模型来做动态判断。

Jev 的核心定位是机器对机器的状态评估。它不回答用户提问，也不生成自然语言。它的职责是根据输入上下文，在几十毫秒内返回一个预定义的离散标签，将上游请求分流到下游分支。这类似于物流分拣中的分流模型。在早期的大模型工程落地中，用轻量小模型做路由分流本来就是常见做法。

官方公布的运行指标中，输入端每百万 Token 计费 0.042 美元，输出免费，端到端请求延迟在 70 到 500 毫秒区间。不管是底座模型小还是单步前向推导的优势，它的服务成本被压得很低。

官方在宣传时借用了认知科学的“双系统”概念：让昂贵的前沿大模型负责慢速的深度推演（System 2），让 Jev 充当快速廉价的反射弧（System 1）。在需要做前置过滤或路由分流时，用小判别模型就能搞定，不需要让生成模型全程陪跑。

<!-- DIAGRAM: 认知双系统映射：脊髓反射（Jev 单步评估）与大脑深思（LLM 生成推演）的分工架构 -->

为了追求速度，Jev 舍弃了文本生成，只保留三种输出原语：
1. `choice`：在给定的枚举列表中完成多选一路由。
2. `score`：在有序离散区间内打分（如 0 到 10 的数值评分）。
3. `noul`：输出二分类概率（布尔判断，如 true / false 或 yes / no）。

它的输出附带了置信度概率。很多开发者吃过大模型生成 JSON 时幻觉的苦头，大模型即使输出错误结果，也常常给出虚高的概率。Jev 宣称对置信度进行了校准，下游系统可以依据置信度设置阈值，一旦置信度偏低就由硬规则或人工接管。关于这个置信度是如何校准的，后文会详细展开。

在工程调用上，TypeSafe AI 接入了 Cloudflare AI Gateway 与 Vercel 基础设施。配合官方 `@ai-sdk/typesafe-ai` 适配层，核心代码通过 `experimental_evaluate` 声明判断原语即可：

```tsx
import { experimental_evaluate } from '@ai-sdk/typesafe-ai';

const result = await experimental_evaluate({
  model: 'typesafe-ai/jev',
  prompt: contextText,
  primitive: { type: 'choice', options: ['allow', 'block', 'escalate'] },
});
```

没必要把 Jev 捧上神坛。从技术本质来说，它没有超越统计学的理论创新，能力边界也很窄：它无法完成长文本创作、代码编写、多轮对话记忆，更解不了长步骤数学推导。但它提醒我们，不是所有任务都必须调用高价的前沿模型，专长于速度的判别模型同样有其工程价值。

<!-- lang:en -->
Jev is a statistical classifier for state evaluation. Large models generate. Jev discriminates. It takes classification work that is slow and expensive on an LLM, and makes it cheap and fast.

At launch, plenty of developers thought it was a joke. Founder Diogo Almeida sounds close to Anthropic CEO Dario Amodei. A community demo of millisecond-level DOOM control made people look at what it can actually do.

The name comes from Jevons paradox. When a resource gets much cheaper to use, total consumption often rises instead of falling. If one model decision gets a hundred times cheaper, places that used to be hard-coded if-else may start calling a model.

Jev sits in machine-to-machine state evaluation. It does not answer users. It does not write natural language. Given context, it returns a predefined discrete label in tens of milliseconds and sends the request down a branch. This is like a sorter in a logistics line. Lightweight routers in front of large models were already a common pattern.

Official numbers: $0.042 per million input tokens, free output, 70 to 500 ms end to end. Small base model, single forward pass, or both. Service cost stays low.

Marketing borrows the dual-system idea from cognitive science. Expensive frontier models do slow System 2 work. Jev is a cheap System 1 reflex. Prefetch filters and routing do not need a generator riding along.

<!-- DIAGRAM: Dual-system cognitive mapping: spinal reflex (Jev single-step evaluation) versus cerebral deliberation (LLM generation) -->

To go fast, Jev drops text generation and keeps three primitives:

1. `choice`: pick one option from an enum list.
2. `score`: score on an ordered discrete scale, such as 0 to 10.
3. `noul`: binary classification probability (boolean decision, e.g., true/false or yes/no).

Each output ships a confidence value. Many of us have watched LLMs emit wrong JSON with a smug probability. Jev says that confidence is calibrated. Downstream code can set a threshold and hand low-confidence cases to rules or humans. How that calibration is trained comes later.

On the wiring side, TypeSafe AI sits on Cloudflare AI Gateway and Vercel. With `@ai-sdk/typesafe-ai`, the call is `experimental_evaluate`:

```tsx
import { experimental_evaluate } from '@ai-sdk/typesafe-ai';

const result = await experimental_evaluate({
  model: 'typesafe-ai/jev',
  prompt: contextText,
  primitive: { type: 'choice', options: ['allow', 'block', 'escalate'] },
});
```

No need to put Jev on a pedestal. There is no statistical breakthrough. The skill set is narrow. It cannot write long prose, code, multi-turn memory, or long math. Not every job needs a pricey frontier model. A discriminator built for speed still has engineering value.
