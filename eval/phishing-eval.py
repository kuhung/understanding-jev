#!/usr/bin/env python3
"""Minimal harness: single-step noul eval vs multi-hop phishing (see anisselbd/jev-phishing-bench)."""

from __future__ import annotations

# Wire to your Jev client or HTTP gateway; this file documents the call shape only.


def evaluate_phishing(email_body: str) -> dict:
    return {
        "primitive": {"type": "noul", "question": "Is this phishing?"},
        "state": email_body,
    }


if __name__ == "__main__":
    sample = "Urgent: verify payroll — click here before EOD."
    print(evaluate_phishing(sample))
