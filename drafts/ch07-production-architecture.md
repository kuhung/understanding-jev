## 生产架构 / Production Architecture

<!-- lang:zh -->
在生产架构中，将低时延的判别模型作为前置网关，可以拦截大量不必要的生成请求。

### 混合路由

生产系统的请求在穿过 API 网关后，首先进入单步分类器。路由依据分类标签与置信度将流量分流：常规查询命中预计算或缓存，安全违规直接拦截，只有多步推理任务才唤醒后端的生成式大模型。

<!-- DIAGRAM: 混合生产架构全景图：API 网关入口通过 System 1 极速分类器分流至预计算响应、LLM 深度生成与人工复核三种后端 -->

### 成本与延迟

我们以日均 10 万次请求的在线服务为例做测算（假设输入均长 800 Token，输出均长 400 Token）：

| 架构方案                               | 日均 LLM 调用量 | 日均推理费用 (USD) | 月度总支出 (USD) | 端到端 P50 延迟 | 端到端 P99 延迟 |
| -------------------------------------- | --------------- | ------------------ | ---------------- | --------------- | --------------- |
| 全量 LLM 直连 (GPT-4o / Claude 级别)   | 100,000 次      | $840.00            | $25,200.00       | 1,800 ms        | 4,200 ms        |
| 判别模型前置 + LLM 混合路由            | 20,000 次       | $171.36            | $5,140.80        | 25 ms           | 2,100 ms        |
| **优化幅度**                           | **-80.0%**      | **-79.6%**         | **-79.6%**       | **-98.6%**      | **-50.0%**      |

如果约 80% 的常规请求能在前置判别层直接分流或命中缓存，透传至大模型的调用量将大幅缩减，既降低了开销，也避免了用户经历无谓的等待。

### 三种网关形态

1. 拦截器形态：在流量入口对恶意输入进行毫秒级预筛，直接切断注入攻击。
2. 路由器形态：识别用户意图，将高难度任务导向重型推理集群，简单闲聊或固定问答分发给本地轻量模型。
3. 守卫形态：在 Agent 执行 Shell 命令或修改敏感配置前进行动态鉴权，对越权操作即刻阻断。

```tsx
const verdict = await jev.evaluate({
  state: `Command: ${command}; WorkingDir: ${cwd}`,
  primitive: { type: "choice", options: ["allow", "block", "escalate"] }
});
if (verdict.choice !== "allow") throw new SecurityViolationError(verdict);
```

### 生产落地案例

社区中已有一些将该思路落地的开源项目：
- `pi-warden`：拦截 Agent 运行时的文件覆写与终端命令，替代传统的关键词黑名单。
- `pi-jev-auto-mode`：根据任务难度与上下文长短，动态决定启用极速单步执行还是启动深度推理。
- `jev-router` / `codex-router`：在入口处解析代码意图，实现语义切流。

### ReflexGate 方案

把网关决策沉淀为标准化中间件，通常称为 ReflexGate 方案。接入层挂载 1B 到 3B 参数量的本地轻量模型（如 Qwen2.5-1.5B），关闭自回归生成，只执行确定性的单步前向推理。单卡吞吐量大幅提高，网关可以在 10 到 30 毫秒内完成安全检查与意图打分。

```python
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_token_ids]
    calibrated_probs = torch.softmax(logits / temperature, dim=-1)
```

### 影子流量校验

分流模型上线前，建议采用影子流量进行验证。将生产流量旁路复制给新分类器，与现有主流程决策做对比。当统计差异在容限范围内且置信度表现稳定后，再切入主链路。

<!-- lang:en -->
Put a low-latency discriminator in front of the gateway and you stop a lot of generation you never needed.

### Hybrid routing

Traffic hits the API gateway, then a single-step classifier. Labels and confidence split the flow. Routine queries hit cache or precomputed answers. Policy violations stop there. Only multi-step reasoning wakes the generative model.

<!-- DIAGRAM: Hybrid architecture overview: API gateway routing through System 1 classifier into precomputed responses, deep LLM reasoning, and human escalation -->

### Cost and latency

A service at 100,000 requests per day, 800 input tokens and 400 output tokens on average:

| Architecture | Daily LLM calls | Daily inference (USD) | Monthly (USD) | P50 latency | P99 latency |
| ------------ | --------------- | --------------------- | ------------- | ----------- | ----------- |
| All traffic to GPT-4o / Claude class | 100,000 | $840.00 | $25,200.00 | 1,800 ms | 4,200 ms |
| Discriminator in front + LLM | 20,000 | $171.36 | $5,140.80 | 25 ms | 2,100 ms |
| **Change** | **-80.0%** | **-79.6%** | **-79.6%** | **-98.6%** | **-50.0%** |

If about 80% of routine requests stop at the discriminator or the cache, LLM volume drops. Cost drops. Users wait less.

### Three gateway shapes

1. Interceptor: millisecond prefilter at ingress, cut injection there.
2. Router: read intent, send hard work to a heavy cluster, send small talk and canned Q&A to a local small model.
3. Guard: authorize before an agent runs a shell command or edits sensitive config. Block overreach immediately.

```tsx
const verdict = await jev.evaluate({
  state: `Command: ${command}; WorkingDir: ${cwd}`,
  primitive: { type: "choice", options: ["allow", "block", "escalate"] }
});
if (verdict.choice !== "allow") throw new SecurityViolationError(verdict);
```

### Production cases

A few public repos already ship this idea:

- `pi-warden`: intercepts file overwrites and terminal commands, instead of a keyword denylist.
- `pi-jev-auto-mode`: picks single-step speed or deep reasoning from task difficulty and context length.
- `jev-router` / `codex-router`: parse code intent at the door and split traffic.

### ReflexGate

Package the decision as middleware and people call it ReflexGate. Hang a 1B to 3B local model such as Qwen2.5-1.5B on ingress. Turn generation off. Run one deterministic forward pass. Per-GPU throughput goes up. Safety checks and intent scores finish in 10 to 30 ms.

```python
with torch.no_grad():
    logits = model(inputs.input_ids).logits[0, -1, candidate_token_ids]
    calibrated_probs = torch.softmax(logits / temperature, dim=-1)
```

### Shadow traffic

Before cutover, copy live traffic to the new classifier and compare with the current path. Move it onto the main line when divergence stays inside tolerance and confidence looks stable.
