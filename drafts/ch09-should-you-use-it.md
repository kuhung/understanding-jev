## 该不该用 / Should You Use It

<!-- lang:zh -->
大多数团队的真实问题不是 Jev 好不好，而是当前场景到底需要 System 1 还是 System 2。翻开生产环境中的网关日志，工业界八成到九成的 LLM API 调用根本不需要生成优美长文。团队付着每百万 Token 几美元的高昂账单并忍受数秒延迟，仅仅是为了提取用户意图、打上分类标签或者决定网关放行。笔者在大量生产系统的重构现场看到，开发者对生成式大模型的滥用已经到了惊人的地步。

把生成模型当路由交换机使用，是当下 AI 架构中最普遍的算力错配。许多系统为了一句单薄的意图判断，盲目启动数百亿参数的自回归循环。System 1 的脊髓单步反射与 System 2 的大脑深思推演被混为一谈，导致系统吞吐量在流量高峰期瞬间瘫痪。认清这两种认知模式的边界，比盲目追求模型跑分要实在得多。

### 决策自检清单

业务请求中有多少比例是重复且可枚举的？如果九成以上的用户请求都在预设意图集合内打转，自回归模型逐字吐词纯属浪费电力。高频重复的流量只配享有脊髓反射的计算预算。只有真正游离在常规模式之外的长尾输入，才值得转交昂贵的大脑皮层进行深思。

下游依赖的分类标签到底有多稳定？业务团队如果每周都要推翻重构分类目，微调小模型的维护开销会迅速抹平微小的延迟收益。标签体系半年不变更的静态场景才配谈结构固化。频繁变动的动态业务必须依赖支持运行时动态候选项的开放接口。

业务流水线对分类错误的容忍度究竟有多高？如果分错类的代价仅仅是消耗几毫秒触发一次重试，单步快速放行就是最划算的工程赌注。一旦判定失误会引发资金穿透或不可逆的系统删库，单步前向矩阵绝不可能承担终审责任。高危业务链路永远需要规则兜底和降级审查通道。

工程团队手头到底沉淀了多少真实标注数据？缺少高质量的基准样本时，单步决策模型的评测与校准都会退化为盲人摸象。冷启动阶段强行上马自建微调方案，最后往往只能交付一堆过拟合的残次品。摸清数据家底是做出任何架构决策的前提。

### 三种决策范式权衡

技术选型从来不是非黑即白的站队游戏。传统 BERT 分类器、生成式大模型与以 Jev 为代表的 System 1 单步决策模型各自站在不同的权衡端点上。

| 评估维度 | 传统 BERT 分类器 | 生成式大模型 (LLM) | Jev / System 1 决策模型 |
| :--- | :--- | :--- | :--- |
| **运行时灵活性** | 极低（标签固化，增删需重训） | 极高（提示词自由定义输出） | 高（运行时动态传入候选选项） |
| **知识储备** | 弱（仅限垂直域监督信号） | 极丰富（海量通识与专业常识） | 丰富（继承大底座预训练通识） |
| **上下文长度** | 短（通常限制在 512 Token） | 极长（可达 128k 到 1M Token） | 中等（几千到数万 Token） |
| **推理速度** | 极快（通常小于 20ms） | 极慢（数百毫秒至数秒） | 快（20ms 至 200ms） |
| **输出稳定性** | 确定（固定分类概率分布） | 波动（受温度系数与采样扰动） | 确定（非自回归矩阵直出） |
| **置信度可信度** | 需额外后校准（易过度自信） | 差（自回归 logits 虚高严重） | 优（经专用校准训练后可信） |
| **深度推理能力** | 无（线性表征投影） | 极强（支持多步因果与思考链） | 弱（仅限单步前向特征模式匹配） |

BERT 便宜快速但缺乏现代通用常识，修改分类目更是漫长的工程噩梦。生成式大模型通晓万物且具备深厚推理，却背负着不可预测的延迟和漂移的置信度。Jev 这类单步决策模型剥离了生成头，用预训练通识支撑动态候选项，换取到了高确定性与毫秒级时延。

<!-- DIAGRAM: 决策模型选型光谱：BERT、Jev 单步决策与生成式 LLM 在灵活性、速度与推理深度上的权衡三棱镜 -->

### 适用与禁忌边界

哪些场景最适合单步决策模型大显身手？网关处的意图路由、海量内容审核预筛与 API 权限门禁是其发挥优势的天然阵地。在智能体运行循环中，工单分类、死循环检测、面对海量 DOM 节点的元素筛选以及安全拦截网关，都依赖单步决策在极低时延下给出确定判定。这些任务只需要干净的离散标签，任何自回归文字生成都是纯粹的资源浪费。

哪些场景坚决不能接入单步决策模型？业务如果需要向用户直接输出自然语言文本，单步网络在物理机制上无法胜任。涉及多步复杂推理、标签体系朝令夕改、需要给出透明解释理由以及包含复杂因果链的安全风控，单步前向传播必然失准。把充满层层伪装的攻击流量交给无思考链的单步网络，只会给整个系统埋下定时炸弹。

### 两个不舒服的工程结论

如果分类精度要求高于 90% 且问题依赖多步因果推导，老老实实调用 Claude 或 GPT 的思考链。缺乏自回归支架的单步前向计算在两层以上的逻辑反转面前会迅速崩溃。宁可忍受两秒等待并多付几十倍费用，也不要在没有思维链保护的高危决策上盲目冒险。认清算力规律能避免灾难性的生产事故。

如果手头连几百条干净的标注数据都拿不出来，不要急着部署 System 1 模型。最稳妥的路径是用通用大模型的少样本提示词跑通业务原型，顺带收集沉淀真实访问日志。等真实数据集清洗标注齐备，再考虑将其蒸馏压缩进单步决策模型。越过数据积累去追求轻量架构，属于典型的工程自嗨。

<!-- lang:en -->
The real dilemma facing engineering teams is rarely whether Jev is intrinsically good. The decisive question is whether your production workload demands System 1 reflex or System 2 deliberation. Examining production telemetry reveals an uncomfortable reality. Eighty to ninety percent of corporate LLM API requests do not require eloquent prose generation. Teams bleed budgets on multi-second latency and painful cloud invoices merely to classify an intent, stamp a boolean flag, or toggle a security gate.

Treating an autoregressive foundation model as a routing switch represents a massive architectural misallocation. Pipelines spin up tens of billions of parameters to output trivial conditional branching. Conflating spinal reflex with cerebral deduction inflates operating costs while degrading API throughput under load spikes. Recognizing boundaries between these cognitive layers matters far more than obsessing over benchmark leaderboards.

### Decision Checklist

What fraction of your production traffic falls into repetitive or enumerable patterns? When ninety percent of queries cycle through fixed intent clusters, autoregressive token generation wastes kilowatt-hours. Repetitive high-volume traffic deserves only the computational budget of a spinal reflex. Only edge cases that escape known distributions justify awakening the expensive cerebral cortex.

How stable is your target taxonomy over time? If your product team alters classification categories on a weekly basis, fine-tuning and deploying custom classifiers will quickly erode operational gains. Hardening weights only makes economic sense when taxonomies remain fixed for quarters. Dynamic environments with shifting business rules require interfaces that accept runtime candidate definitions without retraining.

What is your system's true fault tolerance, and what is the real cost of a misclassification? If a routing mistake costs only a few milliseconds of automated retry overhead, fast single-step evaluation represents a smart trade. If a false negative triggers financial leakage or accidental database corruption, a single forward pass must never serve as the final authority. High-stakes workflows demand deterministic guardrails and escalation paths.

How much clean, validated ground-truth data sits in your repositories? Without high-grade evaluation datasets, benchmarking and calibrating small decision models becomes an exercise in self-deception. Rushing into custom fine-tuning during the zero-data cold start yields brittle, overfitted weights. Knowing your data inventory determines when you can afford to transition architectures.

### Evaluating the Three Paradigms

Engineering decisions avoid absolute dogma. Traditional BERT classifiers, generative LLMs, and System 1 decision models occupy distinct coordinates across the trade-off space.

| Evaluation Dimension | Traditional BERT Classifier | Generative LLM | Jev / System 1 Decision Model |
| :--- | :--- | :--- | :--- |
| **Runtime Flexibility** | Minimal (fixed labels, requires retraining) | Maximal (arbitrary prompting and open output) | High (accepts dynamic candidates at runtime) |
| **World Knowledge** | Poor (limited to narrow task supervision) | Vast (broad commonsense and factual reasoning) | Rich (inherits large pre-trained base representations) |
| **Context Window** | Short (typically constrained to 512 tokens) | Massive (128k to 1M tokens) | Moderate (thousands to tens of thousands of tokens) |
| **Inference Latency** | Ultra-fast (typically under 20ms) | Slow (hundreds of milliseconds to seconds) | Fast (20ms to 200ms) |
| **Output Determinism** | Deterministic (fixed classification head logits) | Variable (subject to temperature and sampling noise) | Deterministic (direct non-autoregressive projection) |
| **Confidence Reliability** | Requires external calibration (prone to overconfidence) | Unreliable (autoregressive token logits drift heavily) | High (calibrated via explicit alignment objectives) |
| **Deep Reasoning Capacity** | None (linear feature projections) | Exceptional (multi-hop causal and chain-of-thought logic) | Weak (constrained to single-step pattern matching) |

BERT delivers sub-twenty-millisecond latency at minimal expense, but its brittle taxonomy demands engineering sprints for every schema modification. Generative models possess broad factual awareness and deep logic, yet their autoregressive decoding inflates latency and produces uncalibrated confidence scores. System 1 decision models discard text generation heads, leveraging pre-trained commonsense to score dynamic options with deterministic millisecond speed.

<!-- DIAGRAM: Decision model selection spectrum: trade-off prism across BERT, Jev System 1, and generative LLMs in flexibility, latency, and reasoning depth -->

### Where to Deploy and Where to Avoid

Where do single-step decision models deliver unmistakable value? Inbound intent routing, front-line content moderation, and fine-grained API permission gates represent their natural habitat. Production pipelines managing ticket classification, agentic loop detection, DOM node pruning, and perimeter security firewalls gain sub-second determinism without generational overhead. These workloads require discrete labels, making autoregressive token generation completely superfluous.

Where must teams avoid single-step decision models? Any application requiring natural language output to human users falls beyond the physical capability of non-autoregressive networks. Workloads demanding multi-step reasoning, frequently shifting taxonomy definitions, transparent decision rationales, or complex causal attribution fail under single forward passes. Routing sophisticated social-engineering attacks into a single-step network without reasoning chains invites operational catastrophe.

### Two Uncomfortable Engineering Truths

When a task demands classification precision above ninety percent alongside multi-hop causal deduction, deploy Claude or GPT with deliberate reasoning chains. Single forward-pass matrices collapse when deceptive inputs feature multiple layers of misdirection. Paying fifty times more compute for a two-second reasoning cycle beats gambling critical infrastructure on a model stripped of intermediate thought. Respecting physical compute constraints prevents catastrophic outages.

Teams lacking hundreds of validated ground-truth samples should resist deploying System 1 models prematurely. The pragmatic roadmap uses general-purpose LLMs and few-shot prompts to establish working prototypes while harvesting real user traffic. Once datasets reach critical mass and undergo rigorous cleaning, distillation into lightweight classifiers delivers compounding returns. Skipping data curation to chase low latency is architectural vanity.
