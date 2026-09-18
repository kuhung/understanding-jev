"""
Build script: converts all chapter Markdown drafts into a single-page
bilingual HTML document with high-end Silicon Valley technical whitepaper style.
Inspired by Stripe Docs, Linear, Vercel, The Twelve-Factor App, Resend.

Run: uv run --with markdown --with pygments python3 scripts/build_site.py
"""
import re
import html
import markdown
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "drafts"
OUTPUT = ROOT / "index.html"

CHAPTERS = [
    "ch00-hero",
    "ch01-what-is-jev",
    "ch02-under-the-hood",
    "ch03-run-it-yourself",
    "ch04-10k-probes",
    "ch05-failure-lessons",
    "ch06-four-patterns",
    "ch07-production-architecture",
    "ch08-ecosystem-map",
    "ch09-should-you-use-it",
]

CHAPTER_TITLES = {
    "ch00-hero": ("首页", "Overview"),
    "ch01-what-is-jev": ("Jev 是什么", "What Is Jev"),
    "ch02-under-the-hood": ("拆底层", "Under the Hood"),
    "ch03-run-it-yourself": ("20 行脚本跑一遍", "Run It Yourself"),
    "ch04-10k-probes": ("万次压测数据说话", "10,000 Probes"),
    "ch05-failure-lessons": ("失败课", "Failure Lessons"),
    "ch06-four-patterns": ("四大设计模式", "Four Patterns"),
    "ch07-production-architecture": ("生产架构", "Production Architecture"),
    "ch08-ecosystem-map": ("生态地图", "Ecosystem Map"),
    "ch09-should-you-use-it": ("该不该用", "Should You Use It"),
}

MD_EXTENSIONS = ["tables", "fenced_code", "codehilite", "toc"]


def split_bilingual(md_text: str) -> tuple[str, str]:
    """Split markdown by <!-- lang:zh --> and <!-- lang:en --> markers."""
    zh_parts = []
    en_parts = []
    current = None

    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped == "<!-- lang:zh -->":
            current = "zh"
            continue
        elif stripped == "<!-- lang:en -->":
            current = "en"
            continue

        if current == "zh":
            zh_parts.append(line)
        elif current == "en":
            en_parts.append(line)
        else:
            zh_parts.append(line)
            en_parts.append(line)

    return "\n".join(zh_parts), "\n".join(en_parts)


def render_rich_diagram(desc: str, lang: str = "zh") -> str:
    """Render authentic, high-precision SVG and interactive visual cards for each technical diagram."""
    d = desc.lower()

    # 1. Forward Pass vs Autoregressive Generation
    if "单次前向传播与自回归" in desc or "forward pass and autoregressive" in d:
        return f"""
        <div class="sv-card my-8 p-6 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-indigo-600"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"架构对比" if lang=="zh" else "Architecture Comparison"}</span>
            </div>
            <span class="text-xs font-mono text-indigo-600 font-semibold bg-indigo-50 px-2.5 py-1 rounded-full">20ms vs 2000ms</span>
          </div>
          <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/60">
              <div class="flex items-center justify-between mb-3">
                <span class="font-medium text-sm text-slate-800">{"传统 LLM (自回归解码)" if lang=="zh" else "Autoregressive LLM"}</span>
                <span class="text-xs font-mono text-rose-600 bg-rose-50 px-2 py-0.5 rounded">~2000ms</span>
              </div>
              <div class="space-y-2 text-xs font-mono text-slate-600">
                <div class="p-2 bg-white rounded border border-slate-200/60">1. Prefill State (计算全量输入)</div>
                <div class="p-2 bg-rose-50/50 rounded border border-rose-200/60 text-rose-700">2. Token 1 循环生成 (JSON '{{"')</div>
                <div class="p-2 bg-rose-50/50 rounded border border-rose-200/60 text-rose-700">3. Token 2 循环生成 ('"decision"')</div>
                <div class="p-2 bg-rose-50/50 rounded border border-rose-200/60 text-rose-700">4. 持续逐 Token 解码 (祈祷括号闭合)</div>
              </div>
            </div>
            <div class="p-4 rounded-xl bg-indigo-50/40 border border-indigo-200/60">
              <div class="flex items-center justify-between mb-3">
                <span class="font-medium text-sm text-indigo-950 font-semibold">{"Jev / 单步前向 (Single Pass)" if lang=="zh" else "Jev Single Forward Pass"}</span>
                <span class="text-xs font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded font-bold">~20ms · 0 Token</span>
              </div>
              <div class="space-y-2 text-xs font-mono text-slate-600">
                <div class="p-2 bg-white rounded border border-indigo-100">1. 单次矩阵前向前缀计算 (Single Pass)</div>
                <div class="p-2 bg-emerald-50 rounded border border-emerald-200 text-emerald-800 font-semibold">2. 末位 Logits 掩码直接投影到枚举槽位</div>
                <div class="p-2 bg-emerald-50 rounded border border-emerald-200 text-emerald-800 font-semibold">3. 局部 Softmax 输出真实校准概率</div>
                <div class="p-2 bg-white rounded border border-indigo-100 text-slate-500">生成步数 = 0 (零文本生成开销)</div>
              </div>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-400 text-center font-mono">Figure: Single Forward Pass vs Multi-token Autoregressive Loop</div>
        </div>
        """

    # 2. KV Cache Shared Prefill / Speculative Fan-out
    if "前缀缓存" in desc or "kv-cache" in d or "speculative fan-out" in d or "共享 prefill" in d:
        return f"""
        <div class="sv-card my-8 p-6 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"KV-Cache 前缀复用拓扑" if lang=="zh" else "KV-Cache Shared Prefill Topology"}</span>
            </div>
            <span class="text-xs font-mono text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-semibold">O(1) 边际开销</span>
          </div>
          <div class="mt-6 flex flex-col md:flex-row items-center gap-4">
            <div class="w-full md:w-5/12 p-4 rounded-xl bg-slate-900 text-white font-mono text-xs shadow-inner">
              <div class="text-slate-400 text-[11px] mb-1">SHARED CONTEXT (30,000 Tokens)</div>
              <div class="text-emerald-400 font-bold mb-2">⚡️ Prefill 仅计算 1 次</div>
              <div class="p-2 bg-slate-800/80 rounded border border-slate-700 text-slate-300">
                [Long Error Trace / System DOM / 30k Words Log]
              </div>
              <div class="mt-2 text-[10px] text-slate-400">固化在 GPU KV Cache 内存中</div>
            </div>
            <div class="text-slate-400 font-bold text-lg hidden md:block">➔ 并行扇出 ➔</div>
            <div class="w-full md:w-6/12 grid grid-cols-1 gap-2 text-xs font-mono">
              <div class="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-center justify-between">
                <span class="text-slate-700">Q1: is_urgent (noul)</span>
                <span class="text-indigo-600 font-bold text-[11px]">82ms</span>
              </div>
              <div class="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-center justify-between">
                <span class="text-slate-700">Q2: department (choice)</span>
                <span class="text-indigo-600 font-bold text-[11px]">85ms</span>
              </div>
              <div class="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-center justify-between">
                <span class="text-slate-700">Q3..50: 批量并发问题</span>
                <span class="text-indigo-600 font-bold text-[11px]">89ms 总耗时</span>
              </div>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-400 text-center font-mono">Figure: Shared Prefill KV-Cache enabling parallel questions with near-zero marginal latency</div>
        </div>
        """

    # 3. Confidence-Gated State Machine
    if "置信度门控" in desc or "confidence-gated" in d:
        return f"""
        <div class="sv-card my-8 p-6 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"置信度门控状态机" if lang=="zh" else "Confidence-Gated State Machine"}</span>
            </div>
            <span class="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">RLCD 统计对齐</span>
          </div>
          <div class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
            <div class="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/80 flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-emerald-800 text-sm">Confidence &gt; 0.90</span>
                  <span class="bg-emerald-200/80 text-emerald-900 text-[10px] px-1.5 py-0.5 rounded font-bold">全自动</span>
                </div>
                <p class="text-slate-600 mt-2">{"无缝放行 / 毫秒级直通执行。无须人工介入。" if lang=="zh" else "Direct auto-execution. Zero human overhead."}</p>
              </div>
              <div class="mt-4 pt-2 border-t border-emerald-200 text-emerald-700 text-[11px] font-semibold">{"80% 常见流量截停" if lang=="zh" else "80% Traffic Resolved"}</div>
            </div>
            <div class="p-4 rounded-xl bg-amber-50/60 border border-amber-200/80 flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-amber-800 text-sm">0.60 ~ 0.90</span>
                  <span class="bg-amber-200/80 text-amber-900 text-[10px] px-1.5 py-0.5 rounded font-bold">灰度审计</span>
                </div>
                <p class="text-slate-600 mt-2">{"正常执行但异步沉淀审计日志，触发抽检预警。" if lang=="zh" else "Execute with audit logging. Trigger spot checks."}</p>
              </div>
              <div class="mt-4 pt-2 border-t border-amber-200 text-amber-700 text-[11px] font-semibold">{"15% 边缘样本监测" if lang=="zh" else "15% Edge Auditing"}</div>
            </div>
            <div class="p-4 rounded-xl bg-rose-50/60 border border-rose-200/80 flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-rose-800 text-sm">Confidence &lt; 0.60</span>
                  <span class="bg-rose-200/80 text-rose-900 text-[10px] px-1.5 py-0.5 rounded font-bold">安全熔断</span>
                </div>
                <p class="text-slate-600 mt-2">{"主动熔断，无条件转交人工专席或深思大模型。" if lang=="zh" else "Circuit break to human or reasoning LLM."}</p>
              </div>
              <div class="mt-4 pt-2 border-t border-rose-200 text-rose-700 text-[11px] font-semibold">{"5% 高危异常兜底" if lang=="zh" else "5% Safety Fallback"}</div>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-400 text-center font-mono">Figure: Confidence-Gated Three-tier Safety Ladder</div>
        </div>
        """

    # 4. Cognitive Dual-System Architecture
    if "双系统" in desc or "dual-system" in d:
        return f"""
        <div class="sv-card my-8 p-6 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"双系统协同理论" if lang=="zh" else "System 1 vs System 2 Architecture"}</span>
            </div>
            <span class="text-xs font-mono text-slate-500">Kahneman Dual-Process Model</span>
          </div>
          <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div class="p-5 rounded-xl bg-gradient-to-br from-indigo-50/70 to-slate-50 border border-indigo-100/80">
              <div class="text-indigo-600 font-bold text-sm mb-1">{"⚡️ System 1 (脊髓反射弧)" if lang=="zh" else "⚡️ System 1: Reflex Arc"}</div>
              <div class="text-slate-500 text-[11px] mb-3">Jev / 轻量级单步决策模型</div>
              <ul class="space-y-1.5 text-slate-700">
                <li>• 响应延迟：<span class="font-bold text-emerald-600">20ms ~ 70ms</span></li>
                <li>• 单次调用开销：<span class="font-bold text-emerald-600">$0.00004</span></li>
                <li>• 专职范围：点击路由、敏感拦截、死循环检查</li>
                <li>• 特征：确定性强类型，零语法崩溃，无幻觉</li>
              </ul>
            </div>
            <div class="p-5 rounded-xl bg-slate-50 border border-slate-200/70">
              <div class="text-slate-900 font-bold text-sm mb-1">{"🧠 System 2 (大脑深思系统)" if lang=="zh" else "🧠 System 2: Deliberative"}</div>
              <div class="text-slate-500 text-[11px] mb-3">Claude 3.5 Sonnet / GPT-4o / o1</div>
              <ul class="space-y-1.5 text-slate-700">
                <li>• 响应延迟：<span class="text-slate-500">2000ms ~ 5000ms</span></li>
                <li>• 单次调用开销：<span class="text-slate-500">$0.01 ~ $0.15</span></li>
                <li>• 专职范围：因果规划、长代码编写、深度推演</li>
                <li>• 特征：自回归慢思考，高智商与复杂推理</li>
              </ul>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-400 text-center font-mono">Figure: Brain (System 2) vs Spinal Reflex (System 1) Engineering Partition</div>
        </div>
        """

    # 5. Production Interception Gateway
    if "生产架构" in desc or "reflexgate" in d or "hybrid architecture" in d or "混合" in desc:
        return f"""
        <div class="sv-card my-8 p-6 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-indigo-600"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"生产级混合拦截拓扑" if lang=="zh" else "Production Hybrid Interception Gateway"}</span>
            </div>
            <span class="text-xs font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded font-bold">{"成本削减 79.6%" if lang=="zh" else "-79.6% Cost"}</span>
          </div>
          <div class="mt-6 flex flex-col items-center gap-3 text-xs font-mono">
            <div class="w-full p-3 rounded-lg bg-slate-100 border border-slate-200 text-center font-bold text-slate-800">
              [API Gateway Ingress · 日均 100,000 请求]
            </div>
            <div class="text-indigo-600 font-bold">↓ 15ms 极速打分</div>
            <div class="w-full p-4 rounded-xl bg-indigo-50/80 border border-indigo-200 text-center">
              <div class="text-indigo-950 font-bold text-sm">System 1 ReflexGate (1B~3B Local Model / Jev)</div>
              <div class="text-indigo-700 text-[11px] mt-1">单次前向传播 · 0 生成 Token · RLCD 校准置信度</div>
            </div>
            <div class="w-full grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
              <div class="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-center">
                <div class="font-bold text-emerald-900">80,000 请求 (80%)</div>
                <div class="text-emerald-700 text-[11px] mt-1">预计算 / 拦截 / 缓存直出</div>
                <div class="text-slate-400 text-[10px] mt-1">&lt;30ms · 零 LLM 开销</div>
              </div>
              <div class="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-center">
                <div class="font-bold text-indigo-900">18,000 请求 (18%)</div>
                <div class="text-indigo-700 text-[11px] mt-1">透传至 Claude / GPT-4o</div>
                <div class="text-slate-400 text-[10px] mt-1">深思系统因果生成</div>
              </div>
              <div class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-center">
                <div class="font-bold text-rose-900">2,000 请求 (2%)</div>
                <div class="text-rose-700 text-[11px] mt-1">低置信度熔断转人工</div>
                <div class="text-slate-400 text-[10px] mt-1">安全审计与回流沉淀</div>
              </div>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-400 text-center font-mono">Figure: Enterprise High-Throughput Reflex Interceptor Pattern</div>
        </div>
        """

    # Generic Fallback Card (Clean and Structured)
    clean_desc = html.escape(desc)
    return f"""
    <div class="sv-card my-8 p-5 bg-slate-50/80 border border-slate-200/80 rounded-xl shadow-sm">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-sm">
          📊
        </div>
        <div>
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">{"技术架构示意" if lang=="zh" else "Architecture Diagram"}</div>
          <div class="text-sm font-medium text-slate-800 mt-0.5">{clean_desc}</div>
        </div>
      </div>
    </div>
    """


def convert_diagrams(html_text: str, lang: str = "zh") -> str:
    """Replace all DIAGRAM placeholders with rich cards."""
    pattern = r"<!--\s*DIAGRAM:\s*(.+?)\s*-->"
    return re.sub(pattern, lambda m: render_rich_diagram(m.group(1).strip(), lang), html_text)


def build_toc_html() -> str:
    items_zh = []
    items_en = []
    for ch_id in CHAPTERS:
        zh_title, en_title = CHAPTER_TITLES[ch_id]
        items_zh.append(f'<a href="#{ch_id}" class="toc-link block py-1 px-2.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 text-[13px] transition-colors">{zh_title}</a>')
        items_en.append(f'<a href="#{ch_id}" class="toc-link block py-1 px-2.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 text-[13px] transition-colors">{en_title}</a>')

    zh_html = "\n".join(items_zh)
    en_html = "\n".join(items_en)

    return f"""
    <nav id="desktop-toc" class="hidden xl:block fixed top-24 right-8 w-60 p-4 bg-white/80 backdrop-blur-md border border-slate-200/80 rounded-2xl shadow-sm z-30 font-sans">
      <div class="text-xs font-semibold tracking-wider uppercase text-slate-400 mb-3 px-2.5">{"目录导航" if True else "Contents"}</div>
      <div class="lang-zh space-y-0.5">{zh_html}</div>
      <div class="lang-en space-y-0.5" style="display:none">{en_html}</div>
    </nav>
    """


def build():
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    sections = []

    for ch_id in CHAPTERS:
        filepath = DRAFTS / f"{ch_id}.md"
        raw = filepath.read_text(encoding="utf-8")
        zh_md, en_md = split_bilingual(raw)

        zh_html = convert_diagrams(md.convert(zh_md), "zh")
        md.reset()
        en_html = convert_diagrams(md.convert(en_md), "en")
        md.reset()

        section_class = "hero-section pb-16 pt-8" if ch_id == "ch00-hero" else "chapter-section py-16 border-t border-slate-200/80"
        sections.append(f"""
        <section id="{ch_id}" class="{section_class}">
          <div class="lang-zh prose-custom">{zh_html}</div>
          <div class="lang-en prose-custom" style="display:none">{en_html}</div>
        </section>
        """)

    toc = build_toc_html()
    content = "\n".join(sections)

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN" class="scroll-smooth">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Understanding Jev — 单步决策模型工程拆解</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>
body {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background-color: #fafafa;
  color: #334155;
  line-height: 1.8;
  font-size: 16.5px;
}}

/* Subtle Silicon Valley Grid Background */
.sv-grid-bg {{
  background-color: #ffffff;
  background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
  background-size: 24px 24px;
}}

/* Typography Refinements */
.prose-custom h2 {{
  font-size: 1.85rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.03em;
  margin-bottom: 1.5rem;
}}

.prose-custom h3 {{
  font-size: 1.3rem;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.02em;
  margin-top: 2.25rem;
  margin-bottom: 1rem;
}}

.prose-custom p {{
  margin-bottom: 1.25rem;
  color: #334155;
}}

.prose-custom a {{
  color: #4f46e5;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 0.15s;
}}

.prose-custom a:hover {{
  color: #4338ca;
}}

/* Stripe/Linear Style Tables */
.prose-custom table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.75rem 0;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  overflow: hidden;
  font-size: 0.9rem;
  background: #ffffff;
}}

.prose-custom th {{
  background-color: #f8fafc;
  color: #0f172a;
  font-weight: 600;
  text-align: left;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}}

.prose-custom td {{
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  color: #475569;
}}

.prose-custom tr:last-child td {{
  border-bottom: none;
}}

.prose-custom tr:hover td {{
  background-color: #f8fafc;
}}

/* Code Blocks with macOS styling */
.prose-custom code {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.86em;
  background-color: #f1f5f9;
  color: #0f172a;
  padding: 0.2em 0.4em;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
}}

.prose-custom pre {{
  position: relative;
  background-color: #0f172a;
  color: #f8fafc;
  padding: 1.25rem;
  padding-top: 2.25rem;
  border-radius: 0.875rem;
  overflow-x: auto;
  margin: 1.5rem 0;
  font-size: 0.88rem;
  line-height: 1.6;
  border: 1px solid #1e293b;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}}

.prose-custom pre::before {{
  content: "";
  position: absolute;
  top: 0.85rem;
  left: 1rem;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 16px 0 #eab308, 32px 0 #22c55e;
}}

.prose-custom pre code {{
  background: transparent;
  color: inherit;
  padding: 0;
  border: none;
  font-size: inherit;
}}

/* TOC Link Active State */
.toc-link.active {{
  color: #4f46e5 !important;
  font-weight: 600;
  background-color: #eef2ff !important;
}}
</style>
</head>
<body class="sv-grid-bg antialiased text-slate-700 min-h-screen">

<!-- Sticky Glassmorphic Header -->
<header class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/80">
  <div class="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
        J
      </div>
      <div>
        <a href="#ch00-hero" class="font-bold text-slate-900 tracking-tight hover:text-indigo-600 transition-colors">Understanding Jev</a>
        <span class="ml-2 text-xs font-mono text-slate-400 hidden sm:inline">System 1 Teardown</span>
      </div>
    </div>
    
    <div class="flex items-center gap-3">
      <div class="inline-flex rounded-lg p-1 bg-slate-100 border border-slate-200 text-xs font-semibold">
        <button id="btn-zh" class="px-3 py-1 rounded-md bg-white text-slate-900 shadow-sm transition-all" onclick="switchLang('zh')">中文</button>
        <button id="btn-en" class="px-3 py-1 rounded-md text-slate-500 hover:text-slate-900 transition-all" onclick="switchLang('en')">EN</button>
      </div>
      <a href="https://github.com/kuhung" target="_blank" class="text-xs font-medium text-slate-500 hover:text-slate-900 px-2 py-1 transition-colors hidden sm:block">
        kuhung.me
      </a>
    </div>
  </div>
</header>

{toc}

<!-- Main Reading Container -->
<main class="max-w-3xl mx-auto px-6 py-12">
{content}
<footer class="mt-24 pt-8 border-t border-slate-200 text-center text-xs text-slate-400 font-mono">
  <p>understanding-jev · 独立旁观者与架构拆解者笔记</p>
</footer>
</main>

<script>
function switchLang(lang) {{
  document.querySelectorAll('.lang-zh').forEach(el => {{
    el.style.display = lang === 'zh' ? '' : 'none';
  }});
  document.querySelectorAll('.lang-en').forEach(el => {{
    el.style.display = lang === 'en' ? '' : 'none';
  }});
  
  const bZh = document.getElementById('btn-zh');
  const bEn = document.getElementById('btn-en');
  if (lang === 'zh') {{
    bZh.className = "px-3 py-1 rounded-md bg-white text-slate-900 shadow-sm transition-all";
    bEn.className = "px-3 py-1 rounded-md text-slate-500 hover:text-slate-900 transition-all";
  }} else {{
    bEn.className = "px-3 py-1 rounded-md bg-white text-slate-900 shadow-sm transition-all";
    bZh.className = "px-3 py-1 rounded-md text-slate-500 hover:text-slate-900 transition-all";
  }}
}}

// TOC Intersection Observer
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{
      document.querySelectorAll('.toc-link').forEach(link => {{
        link.classList.toggle('active', link.getAttribute('href') === '#' + entry.target.id);
      }});
    }}
  }});
}}, {{ threshold: 0.2 }});

document.querySelectorAll('section').forEach(s => observer.observe(s));
</script>
</body>
</html>"""

    OUTPUT.write_text(full_html, encoding="utf-8")
    print(f"Successfully compiled Silicon Valley style {OUTPUT} ({len(full_html):,} bytes)")


if __name__ == "__main__":
    build()
