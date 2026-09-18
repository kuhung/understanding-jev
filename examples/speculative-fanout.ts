/**
 * examples/speculative-fanout.ts
 * 推测性扇出 (Speculative Fan-out) 生产实现示例
 *
 * 核心原理：
 * 利用推理引擎前缀缓存（KV Cache 共享），同一份长文本仅 Prefill 一次。
 * 针对该长上下文并发挂载数十个子问题，端到端耗时逼近单次评估。
 */

interface FanOutQuestions {
  is_urgent: "noul";
  frustration_score: { type: "score"; min: 1; max: 10 };
  department: { type: "choice"; choices: string[] };
  severity_level: { type: "choice"; choices: string[] };
  requires_escalation: "noul";
}

interface BatchEvalResult {
  is_urgent: { answer: boolean; confidence: number };
  frustration_score: { answer: number; confidence: number };
  department: { answer: string; confidence: number };
  severity_level: { answer: string; confidence: number };
  requires_escalation: { answer: boolean; confidence: number };
}

export async function speculativeFanOutAudit(
  ticketContext: string
): Promise<BatchEvalResult> {
  const payload = {
    state: ticketContext,
    questions: {
      is_urgent: "noul",
      frustration_score: { type: "score", min: 1, max: 10 },
      department: {
        type: "choice",
        choices: ["billing", "tech_support", "account_security", "legal_compliance"]
      },
      severity_level: {
        type: "choice",
        choices: ["p0_blocker", "p1_critical", "p2_major", "p3_minor"]
      },
      requires_escalation: "noul"
    } satisfies FanOutQuestions
  };

  const response = await fetch("https://gateway.ai.cloudflare.com/v1/typesafe/jev", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.TYPESAFE_API_KEY}`
    },
    body: JSON.stringify(payload)
  });

  return (await response.json()) as BatchEvalResult;
}
