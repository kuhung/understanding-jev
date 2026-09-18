#!/usr/bin/env python3
"""
examples/composite-scoring.py
复合评分 (Composite Scoring) 生产实现示例

核心原理：
模型仅承担原子维度的离散打分 (0-10)。
所有多因子加权公式、安全硬规则与惩罚系数完全由确定性代码执行。
"""

from typing import Dict


WEIGHT_CONFIG: Dict[str, float] = {
    "device_risk": 0.40,
    "address_anomaly": 0.35,
    "chat_urgency": 0.25,
}

HARD_STOP_DEVICE_CEILING = 9


def evaluate_composite_risk(
    atomic_scores: Dict[str, int]
) -> Dict[str, object]:
    """
    接收 Jev 单项原子读数，由确定性代码执行风控数学计算
    """
    device = atomic_scores.get("device_risk", 0)
    address = atomic_scores.get("address_anomaly", 0)
    chat = atomic_scores.get("chat_urgency", 0)

    # 1. 业务硬规则单票否决
    if device >= HARD_STOP_DEVICE_CEILING:
        return {
            "blocked": True,
            "composite_score": 100.0,
            "reason": f"Device risk ceiling breached ({device} >= {HARD_STOP_DEVICE_CEILING})",
        }

    # 2. 确定性加权求和
    raw_weighted = (
        device * WEIGHT_CONFIG["device_risk"]
        + address * WEIGHT_CONFIG["address_anomaly"]
        + chat * WEIGHT_CONFIG["chat_urgency"]
    )
    # 归一化至 100 分制
    composite_score = round(raw_weighted * 10.0, 2)

    # 3. 风险阈值判定
    is_blocked = composite_score >= 70.0
    return {
        "blocked": is_blocked,
        "composite_score": composite_score,
        "reason": "Threshold breached" if is_blocked else "Normal checkout approved",
    }
