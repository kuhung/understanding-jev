/**
 * examples/confidence-gate.ts
 * 置信度门控 (Confidence-Gated) 生产实现示例
 *
 * 核心原理：
 * 预测标签 (answer) 决定业务动作，置信度 (confidence) 决定自动化等级。
 * - >0.90: 全自动执行，免除人工干预
 * - 0.60-0.90: 异步记录并触发抽检告警
 * - <0.60: 熔断转人工，防范盲区事故
 */

interface EvaluationOutput {
  answer: "allow" | "reject" | "flag";
  confidence: number;
}

export type ActionStatus = "auto_executed" | "async_review_queued" | "circuit_broken_to_human";

export async function processWithConfidenceGate(
  contentId: string,
  result: EvaluationOutput
): Promise<{ status: ActionStatus; reason: string }> {
  // 自动化层级 1: 极高置信度直接执行
  if (result.confidence >= 0.90) {
    // 自动应用拦截或放行规则
    return {
      status: "auto_executed",
      reason: `High confidence (${(result.confidence * 100).toFixed(1)}%), action applied: ${result.answer}`
    };
  }

  // 自动化层级 2: 中等置信度暂缓执行，记录并触发抽检
  if (result.confidence >= 0.60) {
    // 写入低优先级审核流并记录安全告警
    return {
      status: "async_review_queued",
      reason: `Moderate confidence (${(result.confidence * 100).toFixed(1)}%), queued for audit: ${result.answer}`
    };
  }

  // 自动化层级 3: 低置信度立即熔断，转交人工专席
  return {
    status: "circuit_broken_to_human",
    reason: `Low confidence (${(result.confidence * 100).toFixed(1)}%), circuit break to manual tier`
  };
}
