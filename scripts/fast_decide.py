"""
Jev 核心原理本地最小验证脚本
Single-step Logits extraction — zero token generation
Run: uv run --with torch --with transformers python3 scripts/fast_decide.py
"""
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id, torch_dtype=torch.float32, device_map="auto"
)
model.eval()

context = "用户反馈：充值 100 元后账户余额没有变化，银行卡已扣款，要求立刻处理。"
prompt = f"""<|im_start|>system
你是一个工单分类引擎。根据用户输入，选择最合适的处理部门。<|im_end|>
<|im_start|>user
输入内容：{context}
请从以下选项中选择：
A. 账单与充值
B. 技术故障与崩溃
C. 商务与合作
选项：<|im_end|>
<|im_start|>assistant
"""

candidate_tokens = ["A", "B", "C"]
candidate_ids = [
    tokenizer.encode(tok, add_special_tokens=False)[-1] for tok in candidate_tokens
]
inputs = tokenizer(prompt, return_tensors="pt")

start_time = time.perf_counter()
with torch.no_grad():
    outputs = model(**inputs)
    next_token_logits = outputs.logits[0, -1, :]
    selected_logits = next_token_logits[candidate_ids]
    probs = torch.softmax(selected_logits, dim=-1)
elapsed_ms = (time.perf_counter() - start_time) * 1000

print(f"推理耗时: {elapsed_ms:.2f} ms")
for tok, prob in zip(candidate_tokens, probs):
    print(f"选项 {tok}: {prob.item() * 100:.2f}%")
