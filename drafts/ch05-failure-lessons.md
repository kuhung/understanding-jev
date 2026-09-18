## 失败模式 / Failure Modes

<!-- lang:zh -->
明确技术的适用边界，往往比单纯看性能跑分更重要。单步分类模型在特定场景下有清晰的局限性。

### 缺少思维链

单步前向推导无法完成多层因果逻辑推理。在钓鱼邮件基准测试 [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) 中，面对包含多层转折与伪造身份的诱骗邮件，支持思维链推理的 Claude Haiku 判定准确率明显优于 Jev。Jev 出现了较多的漏判。

原因在于计算路径被压缩为一次矩阵乘法。大模型依赖自回归逐步推导来构建中间逻辑支撑，而单步打分必须一次性输出结论。一旦语义欺骗嵌套超过两层，单步模型往往力不从心。

```python
# 单步评估缺乏中间推理步骤，多步逻辑推导容易失准
decision = jev.evaluate(email_body, primitive={"type": "noul", "question": "Is this phishing?"})
```

### 选项顺序偏差

候选项的排列顺序会影响最终判定。Archer Hume 在提示词扰动测试中发现，当参考依据放在候选项之后时，正确率维持在较高水平；一旦将依据调整到开头或中间，正确率便会出现明显下滑。

这是因为自回归模型的单向注意力机制决定了靠后的 Token 能完整聚合前序信息。如果线索出现在序列最前方，其注意力权重在长文本中容易被稀释。因此在设计 Prompt 时，需要规范上下文排版，把参考信息尽量作为共享上下文前置。

### 无关项干扰

在多选一测试中，向枚举列表中加入一个完全无关的选项（如“天气”），原有业务选项之间的相对对数几率比（log-odds）会出现下滑。

这说明候选项之间并非完全独立打分。模型底层的全量注意力计算会让候选池内部产生竞争，无关选项同样会参与注意力权重分配。在对统计分布要求严苛的场景下，需要对候选集做严格清洗。

### 未校准风险

如果直接从自建开源小模型中提取未校准的裸 Logits 作为置信度，存在明显的安全隐患。Qwen 7B 裸读出的 Logits 与经过校准的商用接口一致性仅约 73.8%。

如果业务网关依据高置信度直接自动放行，只在低置信度时转人工复核，未校准模型的虚高置信度就会导致错误分类直接穿透网关，自动化防护机制形同虚设。

### 无文本生成

Jev 没有自回归解码通道，无法生成连贯的自然语言句子。它不能承担异常日志总结、代码编写或客服回复等生成任务。它的定位是流水线上的判别员。如果系统在拦截请求后需要向用户解释拦截原因，必须把上下文转交给后续的生成模型。

### 单步局限

这些局限的共同根源在于单步前向计算的固定容量。单个前向网络只能在固定深度的矩阵变换中处理特征。如果业务需要多步逻辑推导、长文本生成或严格的独立概率评估，单步模型无法替代自回归大模型。

<!-- lang:en -->
Knowing where it fits matters more than staring at a benchmark chart. Single-step classifiers fail in clear ways.

### Missing chain-of-thought

A single forward pass cannot run multi-hop causal logic. In [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench), emails with nested turns and fake identities favored Claude Haiku with chain-of-thought. Jev missed more of them.

The path is one matrix multiply. LLMs build intermediate steps while generating. Single-step scoring has to emit the answer at once. Past two layers of semantic bait, it often cannot keep up.

```python
# 单步评估缺乏中间推理步骤，多步逻辑推导容易失准
decision = jev.evaluate(email_body, primitive={"type": "noul", "question": "Is this phishing?"})
```

### Option order

Candidate order moves the decision. Archer Hume's prompt tests kept accuracy high when evidence sat after the options. Move that evidence to the front or the middle, and accuracy dropped.

Later tokens see everything before them. Evidence at the very start can get diluted in a long sequence. Put reference text in shared state, ahead of the options.

### Irrelevant options

Add a dummy option such as weather to a multiple-choice list, and log-odds among the real options slip.

Scoring is not independent. Full attention lets the candidate pool compete. Noise options take weight too. Tight statistical settings need a clean candidate set.

### Uncalibrated logits

Raw logits from a self-hosted small model are a safety problem if you treat them as confidence. Qwen 7B raw logits agreed with the calibrated commercial API only about 73.8% of the time.

If the gateway auto-allows high confidence and only reviews low confidence, inflated scores send wrong labels through. The safety net does not exist.

### No generation

Jev has no autoregressive decode. It cannot write a coherent sentence. Log summaries, code, and support replies are out of scope. It is a discriminator on the line. If you need to tell a user why a request was blocked, hand the context to a generator.

### Single-step ceiling

These limits share one cause: fixed capacity in one forward pass. The network only transforms features at a fixed depth. Multi-step logic, long text generation, or strict independent probabilities still need an autoregressive model.
