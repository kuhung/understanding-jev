## 该不该用 / Should You Use It

<!-- lang:zh -->
在做架构设计时，首先要明确业务究竟需要的是快速的直觉判断，还是深度的因果推演。很多系统为了做一次枚举分类，让数百亿参数的模型去逐字生成，本质上是算力错配。

### 选型四问

1. **请求是否高度可枚举？** 如果绝大多数请求都在预设类别内，直接用单步判别模型更经济；如果是开放长尾输入，则需要大模型。
2. **标签体系是否稳定？** 频繁变更的分类标签需要动态传入候选集；长期稳定的标签更适合离线轻量化微调。
3. **分类错误的容错成本多高？** 如果容错率低（如涉及资金支付），必须有规则引擎兜底或人工复核机制。
4. **是否有基准标注数据？** 缺少基准数据时很难检验分类与校准效果，贸然自建模型容易过拟合。

### 三种范式权衡

| 评估维度         | 传统 BERT 分类器             | 生成式大模型 (LLM)            | Jev / 单步判别模型             |
| ---------------- | ---------------------------- | ----------------------------- | ------------------------------ |
| **运行时灵活性** | 较低（标签固定，增删需重训） | 极高（提示词自由定义输出）    | 较高（运行时动态传入候选选项） |
| **通用常识储备** | 较弱（依赖垂直域监督信号）   | 极丰富（海量通用常识）        | 丰富（继承大模型预训练常识）   |
| **上下文长度**   | 短（通常 512 Tokens）        | 极长（可达数十万 Tokens）     | 中长（依赖底座长文本缓存）     |
| **推理延迟**     | 极快（通常小于 20ms）        | 较慢（数百毫秒至数秒）        | 快（20ms 至 200ms）            |
| **输出形式**     | 固定分类概率分布             | 生成文本（易产生格式波动）    | 结构化离散概率直出             |
| **置信度质量**   | 需额外标定                   | 原始 logits 虚高较普遍        | 经校准训练后较为可信           |
| **深度推理能力** | 无                           | 极强（支持多步思维链）        | 弱（仅限单步模式匹配）         |

### 适用与不适用

适合使用单步判别模型的场景：
- 入口处的意图识别与路由分发
- 高并发内容合规预筛
- 敏感 API 与终端命令权限审查
- 流程中固定的枚举状态流转

不适合使用的场景：
- 需要向用户直接输出自然语言解释
- 依赖两步以上因果推理的任务
- 涉及多层伪装的安全风控
- 缺乏明确候选选项的开放式生成

### 两点工程建议

第一，如果分类准确率要求极高且依赖多步推导，建议直接使用具备思维链的大模型。单步前向推导缺少中间思考过程，遇到多层转折容易失准。

第二，冷启动阶段如果缺少标注数据，可以先用通用大模型的 Few-shot 提示词跑通业务流程，顺带沉淀真实访问日志。等数据积累到一定规模并完成标注后，再考虑用单步判别模型做替换或蒸馏。

### 相关项目索引

- Archer Hume Jev 接口压测记录
- [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) - 裸 Qwen Logits 与 Jev 一致性对比
- [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) - 钓鱼邮件单步 vs 思考链基准测试
- [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) - Logits 掩码与 PCD 复现
- [AlexWortega/openjev](https://github.com/AlexWortega/openjev) - NLI 交叉编码器实现
- [multimodalart/jev-reproductions-tracker](https://huggingface.co/spaces/multimodalart/jev-reproductions-tracker) - 社区复现追踪
- [AnotiaWang/awesome-jev](https://github.com/AnotiaWang/awesome-jev) - Jev 生态索引
- [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) - 浏览器自动化实验
- [droidrun/mobile-jev](https://github.com/droidrun/mobile-jev) - 移动端 Agent 实验
- [DevMortimer/pi-warden](https://github.com/DevMortimer/pi-warden) - 命令守卫网关

<!-- lang:en -->
When you design the architecture, first decide whether the job needs fast instinct or slow causal work. Many systems spin a tens-of-billions model to emit one enum. That is a compute mismatch.

### Four questions

1. **Are requests highly enumerable?** If most traffic sits in a known set, a single-step discriminator is cheaper. Open-ended tails still need a large model.
2. **Is the label set stable?** Labels that change often should be passed in at runtime. Stable labels can be distilled offline.
3. **What does a wrong label cost?** Low tolerance work, payments included, needs rules or a human behind it.
4. **Do you have gold labels?** Without them, you cannot check accuracy or calibration. Homegrown models overfit easily.

### Three-way trade-off

| Dimension | Classic BERT | Generative LLM | Jev / single-step |
| --------- | ------------ | -------------- | ----------------- |
| **Runtime flexibility** | Low. Labels are frozen. Adds need retraining. | High. Prompt defines the output. | Higher. Candidates arrive at runtime. |
| **World knowledge** | Weak. Needs in-domain labels. | Very rich. | Rich. Inherits pretraining. |
| **Context length** | Short. Often 512 tokens. | Very long. Hundreds of thousands. | Mid-long. Depends on the base cache. |
| **Latency** | Very fast. Often under 20 ms. | Slow. Hundreds of ms to seconds. | Fast. 20 to 200 ms. |
| **Output** | Fixed class distribution | Generated text, format can drift | Structured discrete probabilities |
| **Confidence** | Needs extra calibration | Raw logits often too high | More usable after calibration training |
| **Deep reasoning** | None | Strong. Multi-step chains. | Weak. Single-step pattern match. |

### Fit and non-fit

Use a single-step discriminator for:

- Intent and routing at the door
- High-volume compliance prefilter
- Sensitive API and shell permission checks
- Fixed enum state machines

Skip it for:

- Natural language explanations to users
- Work that needs two or more causal hops
- Security cases with stacked disguise
- Open generation with no candidate list

### Two notes

If you need very high accuracy plus multi-step deduction, use a model with chain-of-thought. A single forward pass has no scratchpad. Nested turns throw it off.

If you have almost no labels, run the product on a general LLM with few-shot prompts and keep the logs. After you have a cleaned set, distill or replace with a single-step discriminator.

### Index

- Archer Hume Jev API load tests
- [rorshopping/jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) - raw Qwen logits vs Jev
- [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) - phishing, single-step vs chain-of-thought
- [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) - logit mask and PCD
- [AlexWortega/openjev](https://github.com/AlexWortega/openjev) - NLI cross-encoder
- [multimodalart/jev-reproductions-tracker](https://huggingface.co/spaces/multimodalart/jev-reproductions-tracker) - community tracker
- [AnotiaWang/awesome-jev](https://github.com/AnotiaWang/awesome-jev) - ecosystem index
- [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) - browser automation
- [droidrun/mobile-jev](https://github.com/droidrun/mobile-jev) - mobile agent
- [DevMortimer/pi-warden](https://github.com/DevMortimer/pi-warden) - command guard
