## 生态地图 / Ecosystem Map

<!-- lang:zh -->
Jev 发布后，开源社区迅速展开了多维度的复现与改造。从几千万参数的轻量网络到数百亿参数的模型，均有团队进行单步决策适配。

| 仓库 / 项目                                                  | 底座与架构           | 核心特性                                                     |
| ------------------------------------------------------------ | -------------------- | ------------------------------------------------------------ |
| [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) | Qwen-2.5-1B          | 并行约束解码（PCD），免重新训练，单步输出离散分布            |
| [AlexWortega/openjev](https://github.com/AlexWortega/openjev) | Qwen3.5-4B / 35B MoE | 基于 NLI 序列分类，提供 Qwen3.5-35B-A3B MoE 配套方案        |
| [heman10x/rlcd-modernbert-151m](https://github.com/heman10x/rlcd-modernbert-151m) | ModernBERT 151M      | 支持 25 个候选槽位，延迟小于 35ms，适配边缘推理              |
| [Mapika/decider-2b](https://github.com/Mapika/decider-2b)    | Qwen3.5-2B-Base      | 基于数十万标注样本完成全参数微调                             |
| [TheoLeeCJ/openjev](https://github.com/TheoLeeCJ/openjev) ([openjev.com](http://openjev.com)) | MiniCPM5-2B-GGUF     | 浏览器端纯本地 WebGPU 运行，无需后端服务                     |
| [vinnylarouge/jevlike](https://github.com/vinnylarouge/jevlike) | 微型字节编码器       | 采用交叉注意力解耦选项间干扰                                 |
| [DavidHatley/system-one-mini](https://github.com/DavidHatley/system-one-mini) | 自研紧凑网络         | 约 69M 参数量，验证低算力下的单步反射能力                    |

在具体应用场景上，社区主要集中在以下方向：
1. **GUI 自动化**：如 `browser-use/jev-ultrafast` 与 `droidrun/mobile-jev`，将屏幕状态判定与动作选择交给单步决策，仅在需要生成长文本时调用生成模型。
2. **安全网关**：如 `pi-warden`，在 Agent 调用命令前做权限判定。
3. **语义路由**：如 `jev-router`，在入口甄别任务难度并做模型分流。
4. **游戏微操**：如 `lukaske/jev-doom-agent`，利用毫秒级响应接管 DOOM 的实时走位。

<!-- lang:en -->
After launch, the community reproduced and forked the idea across sizes, from tens of millions of parameters to tens of billions.

| Repo | Base | Notes |
| ---- | ---- | ----- |
| [harshatheg/Qwen-2.5-1B-RLCD](https://github.com/harshatheg/Qwen-2.5-1B-RLCD) | Qwen-2.5-1B | Parallel constrained decoding, no retraining, discrete distribution in one step |
| [AlexWortega/openjev](https://github.com/AlexWortega/openjev) | Qwen3.5-4B / 35B MoE | NLI sequence classification, including a Qwen3.5-35B-A3B MoE setup |
| [heman10x/rlcd-modernbert-151m](https://github.com/heman10x/rlcd-modernbert-151m) | ModernBERT 151M | 25 candidate slots, under 35 ms, edge-friendly |
| [Mapika/decider-2b](https://github.com/Mapika/decider-2b) | Qwen3.5-2B-Base | Full-parameter fine-tune on hundreds of thousands of labeled samples |
| [TheoLeeCJ/openjev](https://github.com/TheoLeeCJ/openjev) ([openjev.com](http://openjev.com)) | MiniCPM5-2B-GGUF | In-browser WebGPU, no backend |
| [vinnylarouge/jevlike](https://github.com/vinnylarouge/jevlike) | Tiny byte encoder | Cross-attention to cut option interference |
| [DavidHatley/system-one-mini](https://github.com/DavidHatley/system-one-mini) | Custom compact net | About 69M params, single-step reflex on little compute |

Where people actually put it:

1. **GUI automation**: `browser-use/jev-ultrafast` and `droidrun/mobile-jev` hand screen state and action choice to a single-step model, and call a generator only for long text.
2. **Security gateway**: `pi-warden` checks permission before an agent runs a command.
3. **Semantic routing**: `jev-router` grades difficulty at ingress and splits models.
4. **Game control**: `lukaske/jev-doom-agent` drives DOOM movement at millisecond latency.
