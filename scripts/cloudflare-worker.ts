/**
 * Cloudflare Workers 调用 Jev 示例
 * Demonstrates choice / score / noul output primitives
 * Deploy: wrangler deploy
 */

export interface Env {
  AI: Ai;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const ticketContent =
      "用户反馈：充值后账户余额没有到账，已扣款，情绪非常激动，要求立刻退款！";

    // 单次请求同时完成三种维度的判定
    const response = await env.AI.run("typesafe/jev", {
      state: ticketContent,
      questions: {
        is_urgent: {
          type: "noul",
          instructions: "该问题是否属于高紧急度？",
          criteria: {
            true: "涉及资产丢失或强烈客诉",
            false: "一般咨询",
          },
        },
        department: {
          type: "choice",
          instructions: "该工单应分流给哪个团队？",
          criteria: {
            billing: "涉及充值、退款、发票",
            technical: "技术 Bug、系统白屏",
            support: "普通新手引导",
          },
        },
        frustration: {
          type: "score",
          instructions: "用户情绪愤怒程度评估",
          criteria: ["心平气和", "有些焦躁", "极度愤怒"],
        },
      },
    });

    return Response.json(response);
  },
};

/*
 * 等效 curl 调用:
 *
 * curl -X POST \
 *   "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run" \
 *   -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
 *   -H "Content-Type: application/json" \
 *   -d '{
 *     "model": "typesafe/jev",
 *     "input": {
 *       "state": "用户反馈：充值后余额没到账...",
 *       "questions": {
 *         "is_urgent": { "type": "noul", "instructions": "..." },
 *         "department": { "type": "choice", "instructions": "..." }
 *       }
 *     }
 *   }'
 */
