## 生产架构 / Production Architecture

<!-- lang:zh -->
Jev 的最大价值从来不是替代大语言模型，而是在昂贵的大模型面前筑起一层 20 毫秒的神经反射弧。许多受困于生成高延迟与账单赤字的团队，容易陷入非黑即白的二极管思维。他们试图用开源小模型去硬扛复杂的推理链路，最终在生成质量崩溃中惨淡收场。现代软件工程有一条朴素的铁律：最快的计算是没有发生的计算。

为什么要把海量未经筛选的原始流量直接喂给生成式模型？让百亿参数模型去判断用户输入是问候还是攻击，属于极度奢侈的算力浪费。传统正则规则库难以应对语义模糊的自然语言变体，大模型又太慢太贵。介于固定规则与生成深思之间的单步反射层，正好补齐了这一真空地带。

### 混合路由全景

生产级 AI 系统的核心骨架由分层过滤构成。外部流量在穿过 API 网关后，首选进入执行极速单步评估的 System 1 分类器。决策路由根据分类标签与校准置信度，将请求分流至预计算响应、LLM 深度推演或人工介入三个下游通道。只有处于模糊地带且具备复杂因果关系的请求，才有资格唤醒沉重的 System 2 生成模型。

<!-- DIAGRAM: 混合生产架构全景图：API 网关入口通过 System 1 极速分类器分流至预计算响应、LLM 深度生成与人工复核三种后端 -->

这套分流机制对置信度阈值有着严苛的边界限定。常见业务查询和已索引知识直接命中缓存与预计算模块，在百毫秒内完成回包。一旦 System 1 探测到置信度跌破预设红线，请求会被立刻切流至降级策略或人工审核队列。这种动态分级避免了慢速生成模型在高峰期被击穿。

### 账单与延迟实算

算力账单是一面照出架构健康度的镜子。笔者设定一个日均十万次请求的典型在线服务，假设输入均长 800 Token，输出均长 400 Token。如果全部采用主流商业大模型直连方案，每日账单与尾部延迟将成为业务难以承受的包袱。引入 System 1 截断 80% 的常规请求后，透传至后端大模型的调用量瞬间缩减为两万次。

| 架构方案 / Architecture Pattern | 日均 LLM 调用量 | 日均推理费用 (USD) | 月度总支出 (USD) | 端到端 P50 延迟 | 端到端 P99 延迟 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 全量 LLM 直连 (GPT-4o/Claude 3.5 级别) | 100,000 次 | $840.00 | $25,200.00 | 1,800 ms | 4,200 ms |
| System 1 反射层 + LLM 混合路由 | 20,000 次 | $171.36 | $5,140.80 | 25 ms | 2,100 ms |
| **工程优化幅度** | **-80.0%** | **-79.6%** | **-79.6%** | **-98.6%** | **-50.0%** |

节省的开销直接来自无意义生成的消失。八万次被拦截或预计算拦截的请求，仅消耗了极低额度的 Jev 评估费用。绝大多数用户无需经历长达数秒的打字机等待，在数十毫秒内便获得了准确答复。

### 三种网关模式

在落地演进中，团队探索出了三种标准网关形态。第一种是拦截器模式，负责在流量入口针对恶意内容与越狱攻击进行高速预筛。恶意 Payload 会在 20 毫秒内被硬性切断，彻底杜绝脏数据侵入生成式上下文。这种模式把安全防火墙从正则匹配推进到了语义感知层面。

第二种是路由器模式，聚焦于高精度意图识别。网关根据输入上下文的多维语义标签，将任务分发至最匹配的专用后端。代码编辑任务导向重型推理集群，基础闲聊直接分发给紧凑型本地模型。研发团队不需要维护笨重的语义树，单步打分器在几十毫秒内完成靶向投递。

第三种是守卫模式，充当智能体执行高危操作前的安全门禁。当自主 Agent 试图触发终端 Shell 命令或修改敏感系统文件时，守卫会介入进行动态鉴权。任何存在越权风险的动作都会被毫秒级熔断阻断，避免破坏性指令落盘。这种机制把防御关口从外部入口下沉到了内部工具调用侧。

```typescript
const verdict = await jev.evaluate({
  state: `Command: ${command}; WorkingDir: ${cwd}`,
  primitive: { type: "choice", options: ["allow", "block", "escalate"] }
});
if (verdict.choice !== "allow") throw new SecurityViolationError(verdict);
```
参见守卫实现示例 [`packages/pi-warden/src/guard.ts`](packages/pi-warden/src/guard.ts)。

### 生产落地图谱

业内已经涌现出一批将该架构落地的真实开源与商业项目。`pi-warden` 项目通过拦截 Agent 运行时的文件覆写与 Bash 命令调用，构建起了终端物理沙箱。它用毫秒级分类替代了脆弱的关键词黑名单，阻止了大量静默逃逸行为。

`pi-jev-auto-mode` 则把单步评估嵌入了开发助手的模式切换中。系统实时度量会话上下文的复杂度与任务深度，动态决定启用极速单步执行还是启动深度推理。这种动态档位调度显著压低了日常编码交互中的等待卡顿。

在跨服务流量调度领域，`jev-router` 与 `codex-router` 证明了语义切流的可行性。它们在微秒与毫秒级别解析开发者代码意图，把高难度重构精准送往重型后端。Vercel 团队推出的 `vercel/eve` 则在边缘边缘运行网关裁决，实现零额外冷启动开销的动态策略分发。这些实践打破了模型只能作为终点服务的成见，将其转变为高并发网络基础设施的控制面。

### ReflexGate 架构

将网关层决策抽象为标准化组件，便诞生了 ReflexGate 模式。系统在接入层挂载 1B 到 3B 参数量的本地轻量模型，例如 Qwen2.5-1.5B 或 Llama-3.2-1B。该层级彻底关闭自回归词元生成通道，只执行一次确定性的单步前向推理。这一改造消除了显存带宽争抢与 KV 缓存开销，使得单卡并发吞吐暴涨三十倍。

<!-- DIAGRAM: ReflexGate 架构：1B-3B 本地轻量模型在接入层执行零生成 Token 的单次前向 Logits 切片与校准输出 -->

零 Token 生成带来的是确定性的计算延迟预算。网关工程师无需提防大模型无休止的冗长吐字，输入矩阵进入后直接投影为有限选项的概率分布。接入层可以在十到三十毫秒内完成全量安全检查与意图打分。这种稳定的物理响应曲线让 AI 组件首次具备了充当核心微服务网关的资格。

```python
# ReflexGate 核心单步前向切片逻辑
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_token_ids]
    calibrated_probs = torch.softmax(logits / temperature, dim=-1)
```
参见网关单步推断示例 [`scripts/fast_decide.py`](scripts/fast_decide.py)。

### 影子流量与日志飞轮

分流模型如果长期脱离真实生产环境，准确率衰减是必然发生的灾难。团队通常采用影子流量进行灰度发布，将生产请求旁路复制给新候选分类器。影子模型在不影响主链路响应的前提下输出评估结果，与现有规则和后端产出做交叉对比。只有当离线统计差异低于误差容限后，新分类器才能承接主流量。

路由过程产生的海量裁决日志，反向构成了闭环迭代的高价值燃料。系统持续沉淀 System 1 裁决、置信度分布与后续深思系统甚至人工介入的终审结论。一旦监控看板发现置信度分布发生异常漂移，报警流水线便会拉起重新校准作业。这套弱监督日志飞轮让网关反射层在不中断服务的情况下持续变强。

<!-- lang:en -->
Jev delivers value not by replacing large language models, but by placing a twenty-millisecond reflex arc directly in front of them. Many engineering teams crushed by generative latency and cloud invoices default to binary thinking. They attempt to replace heavy models with open-source alternatives, only to watch reasoning quality collapse across complex tasks. In modern systems engineering, the fastest computation is the one that never happened.

Why dump raw, unfiltered traffic straight into an expensive generation engine? Burning billions of parameters to classify whether a user prompt is a greeting or an injection attack represents sheer resource waste. Static regex patterns fail against ambiguous natural language, while generative models remain far too slow and costly. A single-step reflex tier occupies the vacant territory between rigid syntax rules and deliberate text generation.

### Hybrid Routing Blueprint

Production AI systems require tiered filtering rather than flat pipelines. Incoming traffic enters the API gateway and encounters a System 1 classifier designed for immediate single-step scoring. A decision router inspects the resulting label and calibrated confidence, steering the payload toward precomputed responses, deliberate LLM reasoning, or human review. Only ambiguous requests demanding complex causal deduction ever reach the heavy generative layer.

<!-- DIAGRAM: Hybrid architecture overview: API gateway routing through System 1 classifier into precomputed responses, deep LLM reasoning, and human escalation -->

Strict confidence boundaries dictate this routing topology. Standard queries and indexed answers trigger cached or precomputed branches within tens of milliseconds. When System 1 reports confidence scores below safety thresholds, requests reroute to fallback strategies or manual queues. This dynamic triage prevents generative backends from drowning under peak traffic loads.

### Real-World Cost and Latency Accounting

Infrastructure invoices expose the architectural health of any deployment. Consider a service handling 100,000 requests per day with an average prompt length of 800 tokens and an output length of 400 tokens. Routing every query directly through flagship models produces crushing bills and intolerable tail latencies. Introducing a System 1 reflex that filters 80% of routine requests cuts LLM volume from 100,000 down to 20,000 calls.

| Architecture Pattern | Daily LLM Volume | Daily Inference Spend (USD) | Monthly Spend (USD) | End-to-End P50 Latency | End-to-End P99 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Direct LLM Gateway (GPT-4o / Claude 3.5 Class) | 100,000 calls | $840.00 | $25,200.00 | 1,800 ms | 4,200 ms |
| System 1 Reflex + LLM Hybrid Routing | 20,000 calls | $171.36 | $5,140.80 | 25 ms | 2,100 ms |
| **Engineering Impact** | **-80.0%** | **-79.6%** | **-79.6%** | **-98.6%** | **-50.0%** |

Cost savings stem from eliminating unnecessary token generation. The 80,000 intercepted requests consume negligible evaluation fees on the Jev endpoint. Most users receive accurate responses within dozens of milliseconds instead of staring at sluggish streaming cursors.

### Three Gateway Archetypes

Production deployments have crystallized into three distinct gateway patterns. The interceptor pattern prescreens inbound payloads at the edge to block malicious inputs and jailbreak attempts. Disallowed traffic terminates within 20 milliseconds, keeping polluted contexts away from downstream generation models. This upgrades application firewalls from brittle string matching to semantic intent detection.

The router pattern focuses on precise intent classification. The gateway inspects multi-dimensional semantic tags to dispatch requests across specialized backends. Code refactoring dispatches to heavy reasoning clusters, while casual dialog routes to compact local weights. Teams avoid maintaining cumbersome decision trees because the classifier resolves destinations in milliseconds.

The guard pattern establishes a perimeter before autonomous agents execute privileged tools. When an agent attempts terminal shell commands or modifies protected configuration files, the guard enforces real-time authorization. Risky actions face millisecond circuit breaks before any destructive payload touches the operating system. This moves defensive perimeters from the external ingress directly to internal tool execution boundaries.

```typescript
const verdict = await jev.evaluate({
  state: `Command: ${command}; WorkingDir: ${cwd}`,
  primitive: { type: "choice", options: ["allow", "block", "escalate"] }
});
if (verdict.choice !== "allow") throw new SecurityViolationError(verdict);
```
See guard integration pattern in [`packages/pi-warden/src/guard.ts`](packages/pi-warden/src/guard.ts).

### Production Implementations

Several open-source and commercial systems already implement this operational blueprint. The `pi-warden` project isolates terminal sandboxes by intercepting dangerous Bash invocations and destructive file writes. Millisecond classification replaces brittle regex blacklists and stops subtle sandbox escapes.

The `pi-jev-auto-mode` system integrates single-step evaluation into developer environments. It measures session context complexity to switch dynamically between instantaneous reflex actions and deep reasoning models. This adaptive throttling eliminates interactive lag during day-to-day coding sessions.

In high-throughput dispatch, `jev-router` and `codex-router` demonstrate semantic traffic splitting at scale. They parse developer code intent in milliseconds to steer complex refactoring workloads to heavy backends. Vercel deployed `vercel/eve` at the edge to enforce security policies and dynamic dispatch with zero cold-start penalty. These systems prove that compact models operate effectively as control planes for distributed networks rather than mere endpoint destinations.

### ReflexGate Architecture

Packaging gateway decisions into a reusable architecture produces the ReflexGate pattern. Systems deploy 1B to 3B local models such as Qwen2.5-1.5B or Llama-3.2-1B directly on ingress nodes. The pipeline disables autoregressive token decoding and executes a single forward pass. This eliminates memory bandwidth saturation and KV-cache bloat, increasing per-GPU concurrency by thirty times.

<!-- DIAGRAM: ReflexGate architecture: 1B-3B local lightweight model executing zero-token-generation single forward pass with logits slicing and calibrated outputs -->

Eliminating text generation establishes a deterministic latency budget. Gateway engineers avoid open-ended streaming variance, projecting incoming tensor activations into discrete probability vectors. Edge layers finish security audits and intent categorization within ten to thirty milliseconds. Predictable hardware response times make neural components viable inside high-throughput microservice fabrics.

```python
# ReflexGate single forward pass logits extraction
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_token_ids]
    calibrated_probs = torch.softmax(logits / temperature, dim=-1)
```
See single-step forward evaluation in [`scripts/fast_decide.py`](scripts/fast_decide.py).

### Shadow Canary and Log Flywheel

Routing classifiers left unmonitored in production suffer steady accuracy drift. Teams implement shadow traffic pipelines to mirror production payloads across candidate evaluation models. The shadow classifier generates predictions asynchronously without delaying user requests, validating against production outcomes. New models receive live traffic only after divergence rates drop below strict statistical bounds.

High-volume routing logs provide continuous fuel for subsequent model iterations. Logging collectors capture System 1 choices, calibrated confidence scores, and downstream generative or human resolutions. When monitoring dashboards detect statistical confidence drift, automated pipelines trigger model recalibration. This weak-supervision flywheel strengthens gateway reflexes without requiring application downtime.
