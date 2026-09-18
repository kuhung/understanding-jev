/**
 * examples/eval-route.ts
 * Cloudflare / Vercel 网关上的 Jev choice 路由最小调用示例
 */

import { experimental_evaluate } from "@ai-sdk/typesafe-ai";

export async function routeTicket(contextText: string) {
  const result = await experimental_evaluate({
    model: "typesafe-ai/jev",
    prompt: contextText,
    primitive: { type: "choice", options: ["allow", "block", "escalate"] },
  });
  return result;
}
