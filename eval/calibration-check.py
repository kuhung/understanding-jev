#!/usr/bin/env python3
"""Compare raw candidate softmax vs calibrated Jev outputs (see rorshopping/jev-on-a-laptop)."""

from __future__ import annotations

# Requires torch + a local Qwen checkpoint for full runs; snippet matches draft ch05.


def raw_confidence(qwen_logits, candidate_tokens):
    import torch

    probs = torch.softmax(qwen_logits[:, candidate_tokens], dim=-1)
    confidence = probs.max(dim=-1).values
    return confidence


if __name__ == "__main__":
    print("Import raw_confidence() inside your benchmark loop.")
