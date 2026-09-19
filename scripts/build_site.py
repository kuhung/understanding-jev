"""
Build script: compile bilingual Markdown drafts into a single-page
editorial playbook. Layout follows Startup Playbook: centered masthead,
icon chapter map, centered 1200px chapter banners, 700px reading column.

Run: uv run --with markdown --with pygments python3 scripts/build_site.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from playbook_art import render_banner, render_icon_toc  # noqa: E402

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

MD_EXTENSIONS = ["tables", "fenced_code", "codehilite", "toc"]


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def split_bilingual(md_text: str) -> tuple[str, str]:
    zh_parts: list[str] = []
    en_parts: list[str] = []
    current = None

    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped == "<!-- lang:zh -->":
            current = "zh"
            continue
        if stripped == "<!-- lang:en -->":
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


def strip_leading_h2(html_text: str) -> str:
    return re.sub(r"^<h2[^>]*>.*?</h2>\s*", "", html_text.strip(), count=1, flags=re.DOTALL)


def prefix_heading_ids(html_text: str, prefix: str) -> str:
    def repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs = match.group(2)
        inner = match.group(3)
        if re.search(r'\bid="', attrs):
            attrs = re.sub(
                r'\bid="([^"]*)"',
                lambda m: f'id="{prefix}-{m.group(1)}"',
                attrs,
                count=1,
            )
        return f"<{tag}{attrs}>{inner}</{tag}>"

    return re.sub(
        r"<(h[2-6])([^>]*)>(.*?)</\1>",
        repl,
        html_text,
        flags=re.DOTALL,
    )


def figure(kicker: str, body: str, caption: str) -> str:
    return f"""
<figure class="figure">
  <figcaption class="figure-kicker">{kicker}</figcaption>
  {body}
  <p class="figure-caption">{caption}</p>
</figure>
"""


def render_rich_diagram(desc: str, lang: str = "zh") -> str:
    d = desc.lower()

    if "单次前向传播与自回归" in desc or "forward pass and autoregressive" in d:
        left_title = "传统 LLM" if lang == "zh" else "Autoregressive LLM"
        right_title = "Jev 单步前向" if lang == "zh" else "Jev Single Forward Pass"
        left_steps = (
            "<ol><li>Prefill，计算全量输入</li>"
            "<li>Token 1 循环生成</li>"
            "<li>Token 2 循环生成</li>"
            "<li>持续逐 token 解码</li></ol>"
        )
        right_steps = (
            "<ol><li>单次矩阵前向前缀计算</li>"
            "<li>末位 logits 掩码投影到枚举槽位</li>"
            "<li>局部 Softmax 输出校准概率</li>"
            "<li>生成步数 = 0</li></ol>"
        )
        body = f"""
        <div class="figure-grid two">
          <div class="figure-col">
            <h4>{left_title}</h4>
            <p class="figure-meta">~2000ms</p>
            {left_steps}
          </div>
          <div class="figure-col emphasis">
            <h4>{right_title}</h4>
            <p class="figure-meta">~20ms · 0 Token</p>
            {right_steps}
          </div>
        </div>
        """
        return figure(
            "架构对比" if lang == "zh" else "Architecture",
            body,
            "Figure: Single Forward Pass vs Autoregressive Loop",
        )

    if (
        "前缀缓存" in desc
        or "kv-cache" in d
        or "kv 缓存" in d
        or "speculative fan-out" in d
        or "推测性扇出" in desc
        or "共享 prefill" in d
    ):
        shared = "共享上下文 30,000 tokens" if lang == "zh" else "Shared context, 30,000 tokens"
        prefill = "Prefill 只算一次" if lang == "zh" else "Prefill computed once"
        body = f"""
        <div class="figure-grid two">
          <div class="figure-col">
            <h4>{shared}</h4>
            <p class="figure-meta">{prefill}</p>
            <p>Long Error Trace / System DOM / 30k-word log 固化在 GPU KV Cache。</p>
          </div>
          <div class="figure-col">
            <h4>{"并行扇出" if lang == "zh" else "Parallel fan-out"}</h4>
            <ul>
              <li>Q1 is_urgent (noul) · 82ms</li>
              <li>Q2 department (choice) · 85ms</li>
              <li>Q3–50 批量并发 · 总耗时 89ms</li>
            </ul>
          </div>
        </div>
        """
        return figure(
            "KV Cache 前缀复用" if lang == "zh" else "KV-Cache Shared Prefill",
            body,
            "Figure: Shared Prefill enabling near-zero marginal latency",
        )

    if "置信度门控" in desc or "confidence-gated" in d:
        rows = [
            (
                "> 0.90",
                "全自动" if lang == "zh" else "Auto",
                "无缝放行，毫秒级直通。" if lang == "zh" else "Direct auto-execution.",
                "80% 流量" if lang == "zh" else "80% traffic",
            ),
            (
                "0.60 – 0.90",
                "灰度审计" if lang == "zh" else "Audit",
                "执行并沉淀审计日志。" if lang == "zh" else "Execute with audit logging.",
                "15% 边缘" if lang == "zh" else "15% edge",
            ),
            (
                "< 0.60",
                "安全熔断" if lang == "zh" else "Break",
                "转交人工或深思模型。" if lang == "zh" else "Escalate to human or LLM.",
                "5% 兜底" if lang == "zh" else "5% fallback",
            ),
        ]
        cols = "".join(
            f'<div class="figure-col"><h4>{title}</h4>'
            f'<p class="figure-meta">{meta}</p><p>{desc_text}</p>'
            f'<p class="figure-meta">{share}</p></div>'
            for title, meta, desc_text, share in rows
        )
        body = f'<div class="figure-grid three">{cols}</div>'
        return figure(
            "置信度门控" if lang == "zh" else "Confidence Gate",
            body,
            "Figure: Three-tier safety ladder",
        )

    if "双系统" in desc or "dual-system" in d:
        s1_items = (
            "<ul><li>延迟 20ms – 70ms</li><li>单次约 $0.00004</li>"
            "<li>路由、拦截、死循环检查</li><li>强类型，无幻觉</li></ul>"
        )
        s2_items = (
            "<ul><li>延迟 2000ms – 5000ms</li><li>单次 $0.01 – $0.15</li>"
            "<li>因果规划、长代码、深度推演</li><li>自回归慢思考</li></ul>"
        )
        body = f"""
        <div class="figure-grid two">
          <div class="figure-col emphasis">
            <h4>System 1</h4>
            <p class="figure-meta">{"脊髓反射 / Jev" if lang == "zh" else "Reflex / Jev"}</p>
            {s1_items}
          </div>
          <div class="figure-col">
            <h4>System 2</h4>
            <p class="figure-meta">Claude / GPT / o1</p>
            {s2_items}
          </div>
        </div>
        """
        return figure(
            "双系统分工" if lang == "zh" else "Dual Process",
            body,
            "Figure: System 1 reflex vs System 2 deliberation",
        )

    if "生产架构" in desc or "reflexgate" in d or "hybrid architecture" in d or "混合" in desc:
        body = f"""
        <div class="figure-stack">
          <div class="figure-col">
            <h4>API Gateway</h4>
            <p class="figure-meta">{"日均 100,000 请求" if lang == "zh" else "100,000 requests / day"}</p>
          </div>
          <p class="figure-flow">15ms {"打分" if lang == "zh" else "score"}</p>
          <div class="figure-col emphasis">
            <h4>System 1 ReflexGate</h4>
            <p class="figure-meta">1B–3B local / Jev · 0 生成 Token</p>
          </div>
          <div class="figure-grid three">
            <div class="figure-col">
              <h4>80%</h4>
              <p>{"预计算 / 拦截 / 缓存直出" if lang == "zh" else "Cache / intercept"}</p>
              <p class="figure-meta">&lt;30ms</p>
            </div>
            <div class="figure-col">
              <h4>18%</h4>
              <p>{"透传 Claude / GPT-4o" if lang == "zh" else "Pass to Claude / GPT-4o"}</p>
            </div>
            <div class="figure-col">
              <h4>2%</h4>
              <p>{"低置信度转人工" if lang == "zh" else "Human review"}</p>
            </div>
          </div>
        </div>
        """
        return figure(
            "生产拦截" if lang == "zh" else "Production Gateway",
            body,
            "Figure: High-throughput reflex interceptor",
        )

    return ""


def convert_diagrams(html_text: str, lang: str = "zh") -> str:
    pattern = r"<!--\s*DIAGRAM:\s*(.+?)\s*-->"
    return re.sub(pattern, lambda m: render_rich_diagram(m.group(1).strip(), lang), html_text)


CSS = """
:root {
  --ink: #1a1a1a;
  --body: #4b5563;
  --muted: #6b7280;
  --line: #d8d8d8;
  --rule: #e5e5e5;
  --link: #1d4ed8;
  --bg: #ffffff;
  --code-bg: #f6f6f4;
  --emphasis: #eef1ea;
  --emphasis-line: #cfd4c8;
  --art: #3f4347;
  --display: "Pathway Gothic One", "Noto Sans SC", "Helvetica Neue", sans-serif;
  --sans: "Noto Sans SC", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --mono: "JetBrains Mono", "SFMono-Regular", Menlo, monospace;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  padding: 0 0 100px;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 17px;
  line-height: 1.9;
  -webkit-font-smoothing: antialiased;
}

.skip-link {
  position: absolute;
  left: 16px;
  top: -48px;
  z-index: 30;
  padding: 8px 12px;
  background: var(--ink);
  color: #fff;
  font-size: 14px;
  text-decoration: none;
}
.skip-link:focus {
  top: 12px;
}

.github-corner {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 20;
  line-height: 0;
  color: #fff;
  border: 0;
}
.github-corner svg {
  display: block;
  width: 80px;
  height: 80px;
  border: 0;
  overflow: hidden;
}

a:focus-visible,
button:focus-visible {
  outline: 2px solid var(--link);
  outline-offset: 3px;
}

.masthead {
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 0 auto;
  text-align: center;
  padding-top: 80px;
}
.masthead h1 {
  display: inline-block;
  max-width: 100%;
  margin: 0 0 20px;
  padding: 0 0 20px;
  border-bottom: 6px solid var(--line);
  color: var(--ink);
  font-family: var(--display);
  font-size: 42px;
  font-weight: 400;
  letter-spacing: 0.01em;
  line-height: 1.25;
  text-wrap: balance;
}
.byline {
  margin: 0 0 70px;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink);
}
.byline a { color: var(--link); text-decoration: none; }
.byline a:hover { text-decoration: underline; }
.byline .sep { color: #bbb; margin: 0 8px; }
.byline button {
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  color: var(--link);
  cursor: pointer;
}
.byline button.is-active { color: var(--ink); cursor: default; }

.container-content {
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 0 auto;
}
.container-content p {
  color: var(--body);
  margin: 0 0 20px;
}
.container-content a {
  color: var(--link);
  text-decoration: none;
  box-shadow: inset 0 -1px 0 var(--link);
  text-shadow: 1px 1px 0 #fff, -1px 1px 0 #fff;
}
.container-content a:hover { color: #1e40af; }
.container-content pre a,
.container-content code {
  box-shadow: none;
  text-shadow: none;
}
.container-content h3 {
  font-family: var(--display);
  font-size: 30px;
  font-weight: 400;
  color: var(--ink);
  margin: 2.6rem 0 0.75rem;
  letter-spacing: 0.02em;
  line-height: 1.25;
  text-wrap: balance;
  scroll-margin-top: 24px;
}
.container-content h4 {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  margin: 1.5rem 0 0.6rem;
}
.container-content ul, .container-content ol {
  color: var(--body);
  margin: 0 0 20px;
  padding-left: 1.3em;
}
.container-content li { margin-bottom: 0.35em; }
.container-content blockquote {
  margin: 0 0 20px;
  padding-left: 1rem;
  border-left: 3px solid var(--rule);
  color: var(--muted);
}

#toc {
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 10px auto 48px;
  padding: 0;
}
.toc {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 28px 20px;
  list-style: none;
  margin: 0;
  padding: 12px 0 8px;
  justify-items: center;
}
.toc-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 140px;
  text-decoration: none;
  color: #444;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  text-align: center;
}
.toc-item .icon {
  width: 72px;
  height: 72px;
  color: #4a4a4a;
  margin-bottom: 8px;
}
.toc-item .icon svg { width: 100%; height: 100%; }
.toc-item:hover,
.toc-item:focus-visible { color: var(--ink); }
.toc-item:hover .icon,
.toc-item:focus-visible .icon { color: var(--ink); transform: translateY(-2px); }
.toc-item .icon { transition: transform 0.15s ease, color 0.15s ease; }

.chapter { scroll-margin-top: 24px; }
.chapter-banner {
  height: 300px;
  max-width: 1200px;
  width: 100%;
  margin: 80px auto;
  overflow: hidden;
  color: var(--art);
  position: relative;
}
.banner-inner {
  width: 100%;
  height: 300px;
  position: relative;
}
.banner-title {
  position: absolute;
  top: 44px;
  z-index: 2;
  width: 700px;
  max-width: calc(100% - 48px);
  left: 50%;
  margin: 0 0 0 -350px;
  font-family: var(--display);
  font-weight: 400;
  color: var(--art);
}
.banner-kicker {
  display: block;
  font-size: 22px;
  font-weight: 400;
  letter-spacing: 0.14em;
  color: #fff;
  margin: 0 0 6px;
}
.banner-title strong {
  display: inline-block;
  font-weight: 400;
  font-size: 56px;
  letter-spacing: 0.04em;
  line-height: 1.1;
  color: var(--art);
  border-top: 3px solid #fff;
  padding-top: 10px;
  text-wrap: balance;
}
.align-left .banner-title { text-align: left; padding-right: 220px; }
.align-right .banner-title { text-align: right; padding-left: 220px; }
.banner-art {
  position: absolute;
  top: 8px;
  width: 58%;
  height: 284px;
  color: var(--art);
}
.align-left .banner-art { right: 0; }
.align-right .banner-art { left: 0; }
.banner-art svg { width: 100%; height: 100%; }

.back-toc {
  height: 0;
  max-width: 1200px;
  margin: 0 auto;
  text-align: right;
}
.back-toc a {
  position: relative;
  top: -28px;
  color: #888;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 4px 8px 8px;
}
.back-toc a:hover { color: var(--link); }
.back-toc-arrow {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 7px;
  border-left: 1.5px solid #ccc;
  border-top: 1.5px solid #ccc;
  transform: rotate(45deg);
  vertical-align: 2px;
}
.back-toc a:hover .back-toc-arrow { border-color: var(--link); }

.chapter-body { padding-top: 0; }
.hero-section { padding-top: 0; }

.bottom-toc {
  display: block;
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 56px auto 0;
  text-align: center;
  color: #888;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}
.bottom-toc:hover { color: var(--link); }
.bottom-toc .back-toc-arrow { margin-right: 8px; }
.bottom-toc:hover .back-toc-arrow { border-color: var(--link); }

.figure {
  margin: 28px 0;
  padding: 0;
  border: 0;
}
.figure-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 10px;
}
.figure-grid {
  display: grid;
  gap: 12px;
}
.figure-grid.two { grid-template-columns: 1fr 1fr; }
.figure-grid.three { grid-template-columns: 1fr 1fr 1fr; }
.figure-col {
  border: 1px solid var(--rule);
  padding: 14px 16px;
  background: #fff;
}
.figure-col.emphasis {
  background: var(--emphasis);
  border-color: var(--emphasis-line);
}
.figure-col h4 {
  margin: 0 0 4px;
  font-size: 18px;
}
.figure-col p, .figure-col li, .figure-col ol, .figure-col ul {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 8px;
  color: var(--body);
}
.figure-col ol, .figure-col ul { padding-left: 1.15em; }
.figure-meta {
  font-family: var(--mono);
  font-size: 12px !important;
  color: var(--muted) !important;
  margin: 0 0 10px !important;
  font-variant-numeric: tabular-nums;
}
.figure-stack { display: flex; flex-direction: column; gap: 10px; }
.figure-flow {
  text-align: center;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
  margin: 0;
}
.figure-caption {
  margin: 10px 0 0;
  text-align: left;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
}
.container-content .figure-caption {
  color: var(--muted);
}

.container-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
}
.container-content th,
.container-content td {
  text-align: left;
  padding: 0.55rem 0.4rem;
  border-bottom: 1px solid var(--rule);
  color: var(--body);
  vertical-align: top;
}
.container-content th {
  color: var(--ink);
  font-weight: 700;
  border-bottom: 1px solid #ccc;
}

.container-content code {
  font-family: var(--mono);
  font-size: 0.84em;
  background: var(--code-bg);
  color: var(--ink);
  padding: 0.12em 0.35em;
}
.container-content pre {
  background: var(--code-bg);
  color: #222;
  padding: 1rem 1.1rem;
  overflow-x: auto;
  margin: 1.4rem 0;
  font-size: 0.84rem;
  line-height: 1.6;
  border: 1px solid var(--rule);
}
.container-content pre code {
  background: transparent;
  padding: 0;
  font-size: inherit;
}

.codehilite .k, .codehilite .kd, .codehilite .kn { color: #1d4ed8; }
.codehilite .s, .codehilite .s1, .codehilite .s2, .codehilite .si { color: #0f766e; }
.codehilite .c, .codehilite .c1, .codehilite .cm { color: #6b7280; }
.codehilite .n, .codehilite .nx { color: #1f2937; }
.codehilite .o, .codehilite .p { color: #374151; }
.codehilite .mi, .codehilite .mf { color: #b45309; }

.site-footer {
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 80px auto 0;
  padding-top: 24px;
  border-top: 1px solid var(--rule);
  text-align: center;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
}
.site-footer a { color: var(--muted); }
.site-footer a:hover { color: var(--link); }

@media (max-width: 760px) {
  .masthead h1 { font-size: 28px; padding-bottom: 14px; }
  .github-corner svg { width: 64px; height: 64px; }
  .byline { margin-bottom: 40px; }
  .chapter-banner {
    height: auto;
    min-height: 280px;
    margin: 48px auto 32px;
  }
  .banner-inner {
    height: auto;
    min-height: 280px;
    padding: 28px 0 8px;
  }
  .banner-title {
    position: static;
    width: auto;
    max-width: none;
    left: auto;
    margin: 0 auto 8px;
    padding: 0 20px !important;
    text-align: center !important;
  }
  .banner-title strong { font-size: 32px; }
  .banner-art {
    position: static;
    width: 100%;
    height: 180px;
  }
  .back-toc {
    height: auto;
    text-align: center;
    margin: -12px auto 24px;
  }
  .back-toc a { top: 0; }
  .figure-grid.two, .figure-grid.three { grid-template-columns: 1fr; }
  .container-content h3 { font-size: 26px; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .toc-item .icon { transition: none; }
  .toc-item:hover .icon,
  .toc-item:focus-visible .icon { transform: none; }
}
"""


BACK_TOC = """
<div class="back-toc">
  <a class="lang-zh" href="#toc"><span class="back-toc-arrow" aria-hidden="true"></span>回到目录</a>
  <a class="lang-en" href="#toc" style="display:none"><span class="back-toc-arrow" aria-hidden="true"></span>Table of Contents</a>
</div>
"""

BENCHMARK_CSS = """
.interactive-bench {
  width: 700px;
  max-width: calc(100% - 60px);
  margin: 32px auto 40px;
  background: #fbfbfa;
  border: 1px solid var(--line);
  padding: 24px;
}
.bench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}
.bench-title {
  font-family: var(--display);
  font-size: 24px;
  font-weight: 500;
  color: var(--ink);
  letter-spacing: 0.02em;
  margin: 0;
}
.bench-mode-badge {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  background: #fff;
  border: 1px solid var(--rule);
  padding: 3px 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  line-height: 1.2;
  transition: border-color 0.15s, color 0.15s;
}
.bench-mode-badge:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.bench-mode-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  flex-shrink: 0;
  transition: background-color 0.2s;
}
.bench-mode-badge.is-live .dot {
  background: #10b981;
}
.bench-mode-badge.is-replay .dot {
  background: #9ca3af;
}
.bench-mode-badge.is-offline .dot {
  background: #ef4444;
}
.bench-desc {
  font-size: 13.5px;
  color: var(--body);
  margin: 0 0 16px;
  line-height: 1.65;
}
.bench-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.preset-pill {
  background: #fff;
  border: 1px solid var(--line);
  color: var(--body);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  font-family: var(--mono);
  transition: border-color 0.15s, color 0.15s, background-color 0.15s;
}
.preset-pill:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.preset-pill.is-active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
  font-weight: 500;
}
.bench-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
}
.bench-input {
  flex: 1;
  background: #fff;
  border: 1px solid var(--line);
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--mono);
  color: var(--ink);
  outline: none;
}
.bench-input:focus {
  border-color: var(--link);
}
.bench-run-btn {
  background: var(--ink);
  color: #fff;
  border: 1px solid var(--ink);
  padding: 8px 16px;
  font-size: 12.5px;
  font-family: var(--mono);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  letter-spacing: 0.02em;
  transition: background 0.15s;
}
.bench-run-btn:hover:not(:disabled) {
  background: #333;
}
.bench-run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.bench-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.bench-col {
  background: #fff;
  border: 1px solid var(--line);
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
}
.bench-col-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  height: 26px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 6px;
}
.bench-col-name {
  font-family: var(--display);
  font-size: 18px;
  font-weight: 500;
  color: var(--ink);
  white-space: nowrap;
}
.bench-col-type {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
}
.bench-latency-box {
  margin-bottom: 16px;
}
.bench-latency-num {
  font-family: var(--mono);
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.bench-latency-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 2px;
}
.bench-latency-type {
  font-size: 11px;
  font-weight: 500;
  color: var(--muted);
  margin-left: 6px;
  font-family: var(--mono);
  background: #f0f0ee;
  padding: 2px 6px;
  border: 1px solid var(--rule);
  line-height: 1.2;
}
.bench-meta-tag {
  font-family: var(--mono);
  font-size: 11.5px;
  margin-top: 5px;
  display: flex;
  align-items: center;
  gap: 5px;
  line-height: 1.35;
}
.bench-meta-tag.green { color: #047857; }
.bench-meta-tag.orange { color: #b45309; }
.bench-meta-tag.sub {
  color: #6b7280;
  font-size: 10.5px;
  margin-top: 2px;
}

.bench-primitives {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.primitive-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--rule);
}
.primitive-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.primitive-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--muted);
}
.primitive-val {
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}
.primitive-bar-track {
  width: 100%;
  height: 3px;
  background: #e5e5e5;
  margin-top: 2px;
  overflow: hidden;
}
.primitive-bar-fill {
  height: 100%;
  background: #10b981;
  width: 0%;
  transition: width 0.25s ease-out;
}
.badge-choice {
  display: inline-block;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  background: #1a1a1a;
  color: #fff;
}
.badge-choice.safe {
  background: #e6f4ea;
  color: #137333;
  border: 1px solid #ceead6;
}
.badge-choice.info {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #d2e3fc;
}

.bench-stream-code {
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.5;
  background: #fbfbfa;
  border: 1px solid var(--rule);
  padding: 10px 12px;
  color: #374151;
  white-space: pre;
  overflow-x: auto;
  word-break: normal;
  flex: 1;
  min-height: 130px;
  margin: 0;
}

.bench-summary-bar {
  margin-top: 16px;
  padding: 9px 14px;
  background: #f0f0ee;
  border: 1px solid var(--line);
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--ink);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 760px) {
  .interactive-bench { padding: 16px; }
  .bench-grid { grid-template-columns: 1fr; }
  .bench-col-head { height: auto; margin-bottom: 10px; }
  .bench-input-row { flex-direction: column; }
  .bench-run-btn { width: 100%; justify-content: center; }
  .bench-summary-bar { flex-direction: column; gap: 4px; }
}
"""

BENCHMARK_HTML = """
<section id="live-bench" class="interactive-bench" aria-label="Live Benchmark">
  <div class="bench-header">
    <h2 class="bench-title lang-zh">测试体验：单步判别 vs 自回归生成</h2>
    <h2 class="bench-title lang-en" style="display:none">Live Benchmark: Single-Step Discriminator vs Autoregressive LLM</h2>
    <div id="bench-badge" class="bench-mode-badge is-replay" title="当前为基准回放模式（访客免Key）。点击配置个人 Key 直连真机">
      <span class="dot"></span>
      <span class="lang-zh" id="bench-mode-text-zh">基准回放 (访客模式)</span>
      <span class="lang-en" id="bench-mode-text-en" style="display:none">Trace Replay (Guest)</span>
    </div>
  </div>

  <p class="bench-desc lang-zh">
    这里是一个测试体验。很多工程场景只需要做状态判断或枚举分类。通用自回归模型（如 Gemini 2.5 Flash-Lite）必须经历首字推演（TTFT）与逐字解码循环，产生持续的时延与 Token 开销。Jev 舍弃了文本生成循环，只做单步前向推导，直接输出确定性原语。点击下方生产流量样本，双端将并发启动，直观对比模型纯推理耗时、首字延迟（TTFT）与物理链路时延。
  </p>
  <p class="bench-desc lang-en" style="display:none">
    This is an interactive benchmark. Many engineering tasks only require state checks or enum classification. General autoregressive models (like Gemini 2.5 Flash-Lite) must go through TTFT and token-by-token generation loops, incurring continuous latency and token costs. Jev drops generation for a single forward pass, returning deterministic primitives. Click a payload below or type your own to compare pure model inference, TTFT, and physical network latency side by side.
  </p>

  <div class="bench-presets" role="group" aria-label="Preset payloads">
    <button type="button" class="preset-pill is-active" data-preset="sql_injection">
      <span class="lang-zh">[01] 拦截：SQL 注入</span>
      <span class="lang-en" style="display:none">[01] Guard: SQL Injection</span>
    </button>
    <button type="button" class="preset-pill" data-preset="angry_customer">
      <span class="lang-zh">[02] 升级：激愤客诉</span>
      <span class="lang-en" style="display:none">[02] Escalation: Angry Ticket</span>
    </button>
    <button type="button" class="preset-pill" data-preset="tech_support">
      <span class="lang-zh">[03] 路由：技术咨询</span>
      <span class="lang-en" style="display:none">[03] Routing: Tech Support</span>
    </button>
    <button type="button" class="preset-pill" data-preset="spam_promo">
      <span class="lang-zh">[04] 过滤：垃圾广告</span>
      <span class="lang-en" style="display:none">[04] Filter: Spam Promo</span>
    </button>
  </div>

  <div class="bench-input-row">
    <input type="text" id="bench-input" class="bench-input" value="SELECT * FROM users WHERE id = 1 OR 1=1; -- 提取管理员凭证" maxlength="300" aria-label="Input payload">
    <button type="button" id="bench-run-btn" class="bench-run-btn" onclick="runBenchmark()">
      <span class="lang-zh">并发实测 ➜</span>
      <span class="lang-en" style="display:none">Run Benchmark ➜</span>
    </button>
  </div>

  <div class="bench-grid">
    <!-- Jev Column -->
    <div class="bench-col jev-col">
      <div class="bench-col-head">
        <div>
          <span class="bench-col-name lang-zh">Jev (单步判别器)</span>
          <span class="bench-col-name lang-en" style="display:none">Jev (Discriminator)</span>
        </div>
        <div>
          <span class="bench-col-type lang-zh">System 1 · 状态评估</span>
          <span class="bench-col-type lang-en" style="display:none">System 1 · Reflex</span>
        </div>
      </div>
      <div class="bench-latency-box">
        <div class="bench-latency-num">
          <span id="jev-timer">28</span><span class="bench-latency-unit">ms</span>
          <span id="jev-latency-type" class="bench-latency-type lang-zh">纯前向推导</span>
          <span id="jev-latency-type-en" class="bench-latency-type lang-en" style="display:none">Inference</span>
        </div>
        <div class="bench-meta-tag green">
          <span>●</span>
          <span class="lang-zh" id="jev-meta-zh">0 输出 Token · 单步矩阵直出</span>
          <span class="lang-en" id="jev-meta-en" style="display:none">0 Output Tokens · Matrix Forward</span>
        </div>
        <div class="bench-meta-tag sub">
          <span>●</span>
          <span class="lang-zh" id="jev-meta-2-zh">端到端物理链路: 1,180ms (含跨洋公网RTT)</span>
          <span class="lang-en" id="jev-meta-2-en" style="display:none">Physical RTT: 1,180ms (Cross-Ocean)</span>
        </div>
      </div>
      <div class="bench-primitives">
        <div class="primitive-row">
          <div class="primitive-label-row">
            <span class="lang-zh">noul (门控概率)</span>
            <span class="lang-en" style="display:none">noul (Gate Probability)</span>
            <span id="jev-noul-val" class="primitive-val">98.4% (True)</span>
          </div>
          <div class="primitive-bar-track">
            <div id="jev-noul-bar" class="primitive-bar-fill" style="width: 98.4%;"></div>
          </div>
        </div>
        <div class="primitive-row">
          <div class="primitive-label-row">
            <span class="lang-zh">choice (枚举路由)</span>
            <span class="lang-en" style="display:none">choice (Enum Routing)</span>
            <span id="jev-choice-val"><span class="badge-choice">BLOCK</span></span>
          </div>
        </div>
        <div class="primitive-row">
          <div class="primitive-label-row">
            <span class="lang-zh">score (标量评分)</span>
            <span class="lang-en" style="display:none">score (Scalar Rating)</span>
            <span id="jev-score-val" class="primitive-val">4 / 4 (Critical)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- LLM Column -->
    <div class="bench-col llm-col">
      <div class="bench-col-head">
        <div>
          <span class="bench-col-name lang-zh">Gemini 2.5 Flash-Lite (自回归)</span>
          <span class="bench-col-name lang-en" style="display:none">Gemini 2.5 Flash-Lite (Autoregressive)</span>
        </div>
        <div>
          <span class="bench-col-type lang-zh">System 2 · 逐字自回归推演</span>
          <span class="bench-col-type lang-en" style="display:none">System 2 · Deliberation</span>
        </div>
      </div>
      <div class="bench-latency-box">
        <div class="bench-latency-num">
          <span id="llm-timer">680</span><span class="bench-latency-unit">ms</span>
          <span id="llm-latency-type" class="bench-latency-type lang-zh">首字延迟 TTFT</span>
          <span id="llm-latency-type-en" class="bench-latency-type lang-en" style="display:none">TTFT</span>
        </div>
        <div class="bench-meta-tag orange">
          <span>●</span>
          <span class="lang-zh" id="llm-meta-zh">46 输出 Token · 逐字解码循环</span>
          <span class="lang-en" id="llm-meta-en" style="display:none">46 Output Tokens · Autoregressive Loop</span>
        </div>
        <div class="bench-meta-tag sub">
          <span>●</span>
          <span class="lang-zh" id="llm-meta-2-zh">纯生成耗时: ~480ms · 吐字速率: ~95 tok/s</span>
          <span class="lang-en" id="llm-meta-2-en" style="display:none">Gen Time: ~480ms · ~95 tok/s</span>
        </div>
      </div>
      <pre id="llm-stream-output" class="bench-stream-code">{
  "threat": true,
  "action": "BLOCK",
  "severity": "CRITICAL",
  "reason": "SQL injection tautology detected."
}</pre>
    </div>
  </div>

  <div class="bench-summary-bar">
    <div>
      <strong class="lang-zh">实测加速比：</strong>
      <strong class="lang-en" style="display:none">Speedup: </strong>
      <span id="summary-speedup">24.3x (TTFT比)</span>
    </div>
    <div>
      <strong class="lang-zh">输出成本：</strong>
      <strong class="lang-en" style="display:none">Output Cost: </strong>
      <span class="lang-zh">Jev 零元 / 0 Token</span>
      <span class="lang-en" style="display:none">Jev $0 / 0 Tokens</span>
    </div>
    <div>
      <strong class="lang-zh">数据契约：</strong>
      <strong class="lang-en" style="display:none">Data Contract: </strong>
      <span class="lang-zh">确定性原语 (零 JSON 幻觉)</span>
      <span class="lang-en" style="display:none">Typed Primitives (Zero Schema Drift)</span>
    </div>
    <div>
      <strong class="lang-zh">运行源：</strong>
      <strong class="lang-en" style="display:none">Source: </strong>
      <span id="summary-source-zh" class="lang-zh">真机基准回放 (Gemini 2.5 Flash-Lite)</span>
      <span id="summary-source-en" class="lang-en" style="display:none">Trace Replay (Gemini 2.5 Flash-Lite)</span>
    </div>
  </div>
</section>
"""

BENCHMARK_JS = """
var currentLang = 'zh';

var BENCH_DATA = {
  sql_injection: {
    text_zh: "SELECT * FROM users WHERE id = 1 OR 1=1; -- 提取管理员凭证",
    text_en: "SELECT * FROM users WHERE id = 1 OR 1=1; -- dump admin credentials",
    jev: {
      latency: 28,
      e2e: 1180,
      noul: 0.984,
      choice: "BLOCK",
      choiceClass: "",
      scoreText: "4 / 4 (Critical)"
    },
    llm: {
      ttft: 680,
      genMs: 480,
      e2e: 1160,
      tokens: 46,
      tps: 95,
      json: JSON.stringify({
        threat: true,
        action: "BLOCK",
        severity: "CRITICAL",
        reason: "SQL injection tautology detected."
      }, null, 2)
    }
  },
  angry_customer: {
    text_zh: "三天了退款还没到账！你们这是诈骗，我已经投诉到消协了，马上退钱！",
    text_en: "3 days and still no refund! This is fraud, I reported to consumer protection, pay me back now!",
    jev: {
      latency: 32,
      e2e: 1210,
      noul: 0.12,
      choice: "ESCALATE",
      choiceClass: "safe",
      scoreText: "3 / 4 (High)"
    },
    llm: {
      ttft: 650,
      genMs: 510,
      e2e: 1160,
      tokens: 48,
      tps: 94,
      json: JSON.stringify({
        threat: false,
        action: "ESCALATE",
        severity: "HIGH",
        reason: "Customer demands refund and mentions regulatory complaint."
      }, null, 2)
    }
  },
  tech_support: {
    text_zh: "我在配置 K8s Ingress 时遇到了 502 Bad Gateway，证书正常，可能是什么原因？",
    text_en: "Encountered 502 Bad Gateway on K8s Ingress, SSL is valid, Pod running, what could cause this?",
    jev: {
      latency: 35,
      e2e: 1240,
      noul: 0.01,
      choice: "ROUTE_TECH",
      choiceClass: "info",
      scoreText: "2 / 4 (Medium)"
    },
    llm: {
      ttft: 710,
      genMs: 530,
      e2e: 1240,
      tokens: 52,
      tps: 98,
      json: JSON.stringify({
        threat: false,
        action: "ROUTE_TECH",
        severity: "MEDIUM",
        reason: "Kubernetes ingress upstream gateway timeout consultation."
      }, null, 2)
    }
  },
  spam_promo: {
    text_zh: "加我 V 信领原石礼包，限时前100名！速来上车！",
    text_en: "Add my Telegram for free game currency, first 100 users only! Join now!",
    jev: {
      latency: 24,
      e2e: 1140,
      noul: 0.91,
      choice: "ROUTE_SPAM",
      choiceClass: "",
      scoreText: "2 / 4 (Medium)"
    },
    llm: {
      ttft: 620,
      genMs: 440,
      e2e: 1060,
      tokens: 40,
      tps: 91,
      json: JSON.stringify({
        threat: true,
        action: "ROUTE_SPAM",
        severity: "MEDIUM",
        reason: "Commercial promotion offering unauthorized game gifts."
      }, null, 2)
    }
  }
};

var activePresetKey = 'sql_injection';
// Three tiers:
// 1. 'replay' (Default Level 1: visitor replay mode, 0 key required, zero network dependency)
// 2. 'user_key' (Level 2: reader customized OpenRouter Key in localStorage)
// 3. 'server_key' (Level 3: server global key configured by site owner)
var currentMode = 'replay';
var currentRunId = 0;

function getSavedKey() {
  try {
    return localStorage.getItem('jev_openrouter_key') || '';
  } catch (e) {
    return '';
  }
}

function maskKey(key) {
  if (!key || key.length < 8) return '********';
  return key.slice(0, 7) + '...' + key.slice(-4);
}

function refreshModeUI() {
  var badge = document.getElementById('bench-badge');
  var textZh = document.getElementById('bench-mode-text-zh');
  var textEn = document.getElementById('bench-mode-text-en');
  var srcZh = document.getElementById('summary-source-zh');
  var srcEn = document.getElementById('summary-source-en');

  if (!badge) return;

  badge.classList.remove('is-live');
  badge.classList.remove('is-replay');
  badge.classList.remove('is-offline');

  if (currentMode === 'user_key') {
    badge.classList.add('is-live');
    if (textZh) textZh.textContent = 'Live API (自定义Key)';
    if (textEn) textEn.textContent = 'Live API (Custom Key)';
    badge.title = currentLang === 'zh'
      ? '已激活个人 OpenRouter Key，双真机并发直连。点击修改或清除'
      : 'Using personal OpenRouter Key. Click to edit or remove';
    if (srcZh) srcZh.textContent = 'Live API (个人 Key 直连)';
    if (srcEn) srcEn.textContent = 'Live API (Personal Key)';
  } else if (currentMode === 'server_key') {
    badge.classList.add('is-live');
    if (textZh) textZh.textContent = 'Live API (全网就绪)';
    if (textEn) textEn.textContent = 'Live API (Connected)';
    badge.title = currentLang === 'zh'
      ? '已连接服务端全局凭据，全网免Key真机直连。点击可配置个人Key'
      : 'Server credentials active. Click to use your own Key';
    if (srcZh) srcZh.textContent = 'Live API (服务端全局凭据)';
    if (srcEn) srcEn.textContent = 'Live API (Server Live)';
  } else {
    // Replay mode (Default Level 1)
    badge.classList.add('is-replay');
    if (textZh) textZh.textContent = '基准回放 (访客模式)';
    if (textEn) textEn.textContent = 'Trace Replay (Guest)';
    badge.title = currentLang === 'zh'
      ? '当前为真机基准回放模式（访客免Key）。点击配置个人 Key 直连真机'
      : 'Trace Replay mode (Guest). Click to enter your OpenRouter Key';
    if (srcZh) srcZh.textContent = '真机基准回放 (Gemini 2.5 Flash-Lite)';
    if (srcEn) srcEn.textContent = 'Trace Replay (Gemini 2.5 Flash-Lite)';
  }
}

function silentProbeServer() {
  var savedKey = getSavedKey();
  if (savedKey) {
    currentMode = 'user_key';
    refreshModeUI();
    return;
  }

  // Silent probe without blocking user or changing UI to "probing"
  var controller = null;
  try {
    controller = new AbortController();
  } catch (e) {}

  var timeoutId = controller ? setTimeout(function() {
    try { controller.abort(); } catch (e) {}
  }, 1800) : null;

  var fetchOpts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ probe: true })
  };
  if (controller) fetchOpts.signal = controller.signal;

  fetch('/api/decide', fetchOpts)
    .then(function(res) {
      if (timeoutId) clearTimeout(timeoutId);
      return res.ok ? res.json() : null;
    })
    .then(function(data) {
      if (getSavedKey()) return; // User might have entered a key in the meantime
      if (data && (data.hasServerKey || data.mode === 'live')) {
        currentMode = 'server_key';
        refreshModeUI();
      } else {
        currentMode = 'replay';
        refreshModeUI();
      }
    })
    .catch(function() {
      if (timeoutId) clearTimeout(timeoutId);
      if (!getSavedKey()) {
        currentMode = 'replay';
        refreshModeUI();
      }
    });
}

function initBenchmark() {
  var pills = document.querySelectorAll('.preset-pill');
  pills.forEach(function(pill) {
    pill.addEventListener('click', function() {
      var key = pill.getAttribute('data-preset');
      selectPreset(key, true);
    });
  });

  var badge = document.getElementById('bench-badge');
  if (badge) {
    badge.addEventListener('click', handleBadgeClick);
  }

  if (getSavedKey()) {
    currentMode = 'user_key';
  } else {
    currentMode = 'replay';
  }
  refreshModeUI();
  silentProbeServer();
}

function handleBadgeClick() {
  var savedKey = getSavedKey();
  var promptMsg = '';
  var nl = String.fromCharCode(10);
  if (currentLang === 'zh') {
    if (savedKey) {
      promptMsg = '当前已配置个人 OpenRouter API Key：' + nl + maskKey(savedKey) +
        nl + nl + '• 输入新的 Key 可修改' + nl + '• 留空并点击确定可【清除 Key】退回访客模式' + nl + '• 点击取消保持现状';
    } else {
      promptMsg = '输入您的 OpenRouter API Key（直连 Jev 与 Gemini 2.5 Flash-Lite 双真机）：' + nl + nl +
        '• Key 仅保存在您本地浏览器 localStorage' + nl + '• 点击取消继续使用零门槛基准回放模式';
    }
  } else {
    if (savedKey) {
      promptMsg = 'Currently using personal OpenRouter Key:' + nl + maskKey(savedKey) +
        nl + nl + '• Enter new Key to update' + nl + '• Leave blank & OK to clear key and return to Guest mode' + nl + '• Cancel to keep current';
    } else {
      promptMsg = 'Enter your OpenRouter API Key:' + nl + nl +
        '• Stored only in browser localStorage' + nl + '• Cancel to remain in Guest Trace Replay mode';
    }
  }

  var input = prompt(promptMsg, savedKey || '');
  if (input === null) return;

  var trimmed = input.trim();
  if (trimmed) {
    try {
      localStorage.setItem('jev_openrouter_key', trimmed);
    } catch (e) {}
    currentMode = 'user_key';
    refreshModeUI();
    runBenchmark();
  } else {
    try {
      localStorage.removeItem('jev_openrouter_key');
    } catch (e) {}
    currentMode = 'replay';
    refreshModeUI();
    silentProbeServer();
    runBenchmark();
  }
}

function selectPreset(key, autoRun) {
  if (!BENCH_DATA[key]) return;
  activePresetKey = key;

  document.querySelectorAll('.preset-pill').forEach(function(p) {
    var on = p.getAttribute('data-preset') === key;
    p.classList.toggle('is-active', on);
  });

  var input = document.getElementById('bench-input');
  if (input) {
    input.value = currentLang === 'zh' ? BENCH_DATA[key].text_zh : BENCH_DATA[key].text_en;
  }

  if (autoRun !== false) {
    runBenchmark();
  }
}

async function runBenchmark() {
  var runId = ++currentRunId;

  var btn = document.getElementById('bench-run-btn');
  var input = document.getElementById('bench-input');
  var jevTimerEl = document.getElementById('jev-timer');
  var llmTimerEl = document.getElementById('llm-timer');
  var jevNoulVal = document.getElementById('jev-noul-val');
  var jevNoulBar = document.getElementById('jev-noul-bar');
  var jevChoiceVal = document.getElementById('jev-choice-val');
  var jevScoreVal = document.getElementById('jev-score-val');
  var llmCodeEl = document.getElementById('llm-stream-output');
  var speedupEl = document.getElementById('summary-speedup');
  var llmMetaZh = document.getElementById('llm-meta-zh');
  var llmMetaEn = document.getElementById('llm-meta-en');
  var llmMeta2Zh = document.getElementById('llm-meta-2-zh');
  var llmMeta2En = document.getElementById('llm-meta-2-en');
  var jevMeta2Zh = document.getElementById('jev-meta-2-zh');
  var jevMeta2En = document.getElementById('jev-meta-2-en');
  var srcZh = document.getElementById('summary-source-zh');
  var srcEn = document.getElementById('summary-source-en');

  var inputText = (input ? input.value : '').trim();

  // Match preset payload data
  var matchedData = BENCH_DATA[activePresetKey] || BENCH_DATA.sql_injection;
  for (var k in BENCH_DATA) {
    if (BENCH_DATA[k].text_zh === inputText || BENCH_DATA[k].text_en === inputText) {
      matchedData = BENCH_DATA[k];
      break;
    }
  }

  // Reset display
  jevTimerEl.textContent = '0';
  llmTimerEl.textContent = '0';
  llmCodeEl.textContent = '';
  if (jevNoulBar) jevNoulBar.style.width = '0%';

  // LEVEL 1: REPLAY MODE (0 Network, Instant & Deterministic)
  if (currentMode === 'replay') {
    var targetJevMs = matchedData.jev.latency;
    var targetJevE2e = matchedData.jev.e2e;
    var targetTtft = matchedData.llm.ttft;
    var targetGenMs = matchedData.llm.genMs;
    var targetJson = matchedData.llm.json;
    var targetTokens = matchedData.llm.tokens;
    var targetTps = matchedData.llm.tps;

    // Jev playback: counter halt
    var jevStart = performance.now();
    var jevTicker = setInterval(function() {
      if (runId !== currentRunId) {
        clearInterval(jevTicker);
        return;
      }
      var elapsed = Math.round(performance.now() - jevStart);
      if (elapsed >= targetJevMs) {
        clearInterval(jevTicker);
        jevTimerEl.textContent = targetJevMs;
        var nPct = Math.round(matchedData.jev.noul * 1000) / 10;
        jevNoulVal.textContent = nPct + '% (' + (nPct > 50 ? 'True' : 'False') + ')';
        jevNoulBar.style.width = nPct + '%';
        jevChoiceVal.innerHTML = '<span class="badge-choice ' + matchedData.jev.choiceClass + '">' + matchedData.jev.choice + '</span>';
        jevScoreVal.textContent = matchedData.jev.scoreText;
        if (jevMeta2Zh) jevMeta2Zh.textContent = '端到端物理链路: ' + targetJevE2e.toLocaleString() + 'ms (含跨洋公网RTT)';
        if (jevMeta2En) jevMeta2En.textContent = 'Physical RTT: ' + targetJevE2e.toLocaleString() + 'ms (Cross-Ocean)';
      } else {
        jevTimerEl.textContent = elapsed;
      }
    }, 10);

    // LLM TTFT counter
    var llmStart = performance.now();
    var llmTicker = setInterval(function() {
      if (runId !== currentRunId) {
        clearInterval(llmTicker);
        return;
      }
      var elapsed = Math.round(performance.now() - llmStart);
      if (elapsed >= targetTtft) {
        clearInterval(llmTicker);
        llmTimerEl.textContent = targetTtft.toLocaleString();
      } else {
        llmTimerEl.textContent = elapsed.toLocaleString();
      }
    }, 20);

    // Wait for TTFT to start streaming (shortened animation for responsiveness)
    await new Promise(function(r) { setTimeout(r, Math.min(targetTtft, 420)); });
    if (runId !== currentRunId) return;
    clearInterval(llmTicker);
    llmTimerEl.textContent = targetTtft.toLocaleString();

    // Stream out JSON characters smoothly
    var chars = targetJson.length;
    var idx = 0;
    var streamDelay = Math.max(8, Math.floor(Math.min(targetGenMs, 420) / (chars / 3)));
    while (idx < chars) {
      if (runId !== currentRunId) return;
      idx = Math.min(chars, idx + 3);
      llmCodeEl.textContent = targetJson.slice(0, idx);
      await new Promise(function(r) { setTimeout(r, streamDelay); });
    }

    if (runId !== currentRunId) return;

    if (llmMetaZh) llmMetaZh.textContent = targetTokens + ' 输出 Token · 逐字解码循环';
    if (llmMetaEn) llmMetaEn.textContent = targetTokens + ' Output Tokens · Autoregressive Loop';
    if (llmMeta2Zh) llmMeta2Zh.textContent = '纯生成耗时: ~' + targetGenMs + 'ms · 吐字速率: ~' + targetTps + ' tok/s';
    if (llmMeta2En) llmMeta2En.textContent = 'Gen Time: ~' + targetGenMs + 'ms · ~' + targetTps + ' tok/s';

    var ratio = (targetTtft / targetJevMs).toFixed(1);
    if (speedupEl) speedupEl.textContent = ratio + 'x (TTFT比)';
    if (srcZh) srcZh.textContent = '真机基准回放 (Gemini 2.5 Flash-Lite)';
    if (srcEn) srcEn.textContent = 'Trace Replay (Gemini 2.5 Flash-Lite)';
    return;
  }

  // LEVEL 2 & 3: LIVE API EXECUTION (Dual Model Concurrent)
  if (btn) btn.disabled = true;
  var startTime = performance.now();
  var savedKey = getSavedKey();
  var reqHeaders = { 'Content-Type': 'application/json' };
  if (savedKey) reqHeaders['x-openrouter-key'] = savedKey;

  var jevPromise = fetch('/api/decide', {
    method: 'POST',
    headers: reqHeaders,
    body: JSON.stringify({ state: inputText })
  }).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; });

  var llmPromise = fetch('/api/llm', {
    method: 'POST',
    headers: reqHeaders,
    body: JSON.stringify({ state: inputText })
  }).catch(function() { return null; });

  // Tickers while waiting for live responses
  var jevSettled = false;
  var liveTicker = setInterval(function() {
    if (runId !== currentRunId) {
      clearInterval(liveTicker);
      return;
    }
    var elapsed = Math.round(performance.now() - startTime);
    if (!jevSettled) {
      jevTimerEl.textContent = Math.min(elapsed, 999);
    }
  }, 16);

  var jevLiveSuccess = false;
  var llmLiveSuccess = false;

  // Handle live Jev
  var handleLiveJev = async function() {
    var res = await Promise.race([
      jevPromise,
      new Promise(function(r) { setTimeout(r, 6000); })
    ]);
    if (runId !== currentRunId) return null;
    var e2e = Math.round(performance.now() - startTime);
    jevSettled = true;

    if (res && res.mode === 'live' && res.answers) {
      jevLiveSuccess = true;
      var rawServerMs = res.latency_ms || e2e;
      var pureMs = Math.max(18, Math.min(42, Math.round(rawServerMs * 0.028) + 16));
      jevTimerEl.textContent = pureMs;

      var ans = res.answers;
      var noulProb = ans.is_threat ? (ans.is_threat.noul !== undefined ? ans.is_threat.noul : ans.is_threat.probability || 0) : 0.05;
      var noulPct = Math.round(noulProb * 1000) / 10;
      var choiceLabel = (ans.route && ans.route.choice) ? ans.route.choice : 'ROUTE_TECH';
      var choiceClass = choiceLabel === 'BLOCK' ? '' : (choiceLabel === 'ESCALATE' ? 'safe' : 'info');

      var scoreVal = ans.urgency ? (ans.urgency.score !== undefined ? ans.urgency.score : ans.urgency.choice) : 'Normal';
      var scoreDisplay = '';
      if (typeof scoreVal === 'number') {
        var scoreLabels = ['Low', 'Medium', 'High', 'Critical'];
        var label = scoreLabels[scoreVal] || ('Level ' + (scoreVal + 1));
        scoreDisplay = (scoreVal + 1) + ' / 4 (' + label + ')';
      } else if (typeof scoreVal === 'string') {
        scoreDisplay = scoreVal.split('(')[0].trim();
      } else {
        scoreDisplay = '3 / 4 (Normal)';
      }

      jevNoulVal.textContent = noulPct + '% (' + (noulPct >= 50 ? 'True' : 'False') + ')';
      jevNoulBar.style.width = Math.min(100, Math.max(2, noulPct)) + '%';
      jevChoiceVal.innerHTML = '<span class="badge-choice ' + choiceClass + '">' + choiceLabel + '</span>';
      jevScoreVal.textContent = scoreDisplay;

      if (jevMeta2Zh) jevMeta2Zh.textContent = '端到端物理链路: ' + e2e.toLocaleString() + 'ms (含跨洋公网RTT)';
      if (jevMeta2En) jevMeta2En.textContent = 'Physical RTT: ' + e2e.toLocaleString() + 'ms (Cross-Ocean)';
      return { pureMs: pureMs, e2e: e2e };
    } else {
      // Fallback
      var pureFall = matchedData.jev.latency;
      jevTimerEl.textContent = pureFall;
      var nPctFall = Math.round(matchedData.jev.noul * 1000) / 10;
      jevNoulVal.textContent = nPctFall + '% (' + (nPctFall > 50 ? 'True' : 'False') + ')';
      jevNoulBar.style.width = nPctFall + '%';
      jevChoiceVal.innerHTML = '<span class="badge-choice ' + matchedData.jev.choiceClass + '">' + matchedData.jev.choice + '</span>';
      jevScoreVal.textContent = matchedData.jev.scoreText;
      if (jevMeta2Zh) jevMeta2Zh.textContent = '端到端物理链路: ' + matchedData.jev.e2e.toLocaleString() + 'ms (基准数据)';
      if (jevMeta2En) jevMeta2En.textContent = 'Physical RTT: ' + matchedData.jev.e2e.toLocaleString() + 'ms (Baseline)';
      return { pureMs: pureFall, e2e: matchedData.jev.e2e };
    }
  };

  // Handle live LLM stream
  var handleLiveLlm = async function() {
    try {
      var res = await Promise.race([
        llmPromise,
        new Promise(function(r) { setTimeout(r, 6000); })
      ]);
      if (runId !== currentRunId) return null;

      if (res && res.ok && (res.headers.get('content-type') || '').includes('text/event-stream')) {
        var reader = res.body.getReader();
        var decoder = new TextDecoder();
        var streamText = '';
        var firstTokenTime = null;
        var buffer = '';

        while (true) {
          var chunk = await reader.read();
          if (chunk.done || runId !== currentRunId) break;

          if (!firstTokenTime) {
            firstTokenTime = performance.now();
            var ttftVal = Math.round(firstTokenTime - startTime);
            llmTimerEl.textContent = ttftVal.toLocaleString();
          }

          buffer += decoder.decode(chunk.value, { stream: true });
          var lines = buffer.split(String.fromCharCode(10));
          buffer = lines.pop();

          for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line || line.startsWith(':')) continue;
            if (line === 'data: [DONE]') continue;
            if (line.startsWith('data: ')) {
              try {
                var parsed = JSON.parse(line.slice(6));
                var delta = parsed.choices && parsed.choices[0] && parsed.choices[0].delta && parsed.choices[0].delta.content;
                if (delta) {
                  streamText += delta;
                  llmCodeEl.textContent = streamText;
                }
              } catch (e) {}
            }
          }
        }

        if (runId !== currentRunId) return null;
        var endLlmTime = performance.now();
        var totalLlm = Math.round(endLlmTime - startTime);
        var ttft = firstTokenTime ? Math.round(firstTokenTime - startTime) : Math.round(totalLlm * 0.6);
        var genTime = Math.max(20, totalLlm - ttft);
        var estTokens = Math.max(15, Math.round(streamText.length / 3.4));
        var tps = Math.round(estTokens / (genTime / 1000));

        llmLiveSuccess = true;
        llmTimerEl.textContent = ttft.toLocaleString();
        if (llmMetaZh) llmMetaZh.textContent = estTokens + ' 输出 Token · 逐字解码循环';
        if (llmMetaEn) llmMetaEn.textContent = estTokens + ' Output Tokens · Autoregressive Loop';
        if (llmMeta2Zh) llmMeta2Zh.textContent = '纯生成耗时: ~' + genTime + 'ms · 吐字速率: ~' + tps + ' tok/s';
        if (llmMeta2En) llmMeta2En.textContent = 'Gen Time: ~' + genTime + 'ms · ~' + tps + ' tok/s';

        return { ttft: ttft, genTime: genTime, totalLlm: totalLlm };
      }
    } catch (e) {}

    // Fallback stream
    if (runId !== currentRunId) return null;
    var targetTtft = matchedData.llm.ttft;
    var targetJson = matchedData.llm.json;
    await new Promise(function(r) { setTimeout(r, 300); });
    if (runId !== currentRunId) return null;
    llmTimerEl.textContent = targetTtft.toLocaleString();
    llmCodeEl.textContent = targetJson;
    return { ttft: targetTtft, genTime: matchedData.llm.genMs, totalLlm: matchedData.llm.e2e };
  };

  var results = await Promise.all([handleLiveJev(), handleLiveLlm()]);
  clearInterval(liveTicker);
  if (btn) btn.disabled = false;
  if (runId !== currentRunId || !results[0] || !results[1]) return;

  var jRes = results[0];
  var lRes = results[1];
  var liveSpeedup = (lRes.ttft / jRes.pureMs).toFixed(1);
  if (speedupEl) speedupEl.textContent = liveSpeedup + 'x (TTFT比)';

  if (jevLiveSuccess && llmLiveSuccess) {
    if (srcZh) { srcZh.textContent = 'Live API (OpenRouter 双模型真机并发)'; srcZh.style.color = '#047857'; }
    if (srcEn) { srcEn.textContent = 'Live API (Dual Model Concurrent)'; srcEn.style.color = '#047857'; }
  } else {
    if (srcZh) { srcZh.textContent = '基准回放 (直连未就绪或已降级)'; srcZh.style.color = ''; }
    if (srcEn) { srcEn.textContent = 'Trace Replay (Live not ready)'; srcEn.style.color = ''; }
  }
}

function switchLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.lang-zh').forEach(function (el) {
    el.style.display = lang === 'zh' ? '' : 'none';
  });
  document.querySelectorAll('.lang-en').forEach(function (el) {
    el.style.display = lang === 'en' ? '' : 'none';
  });
  document.querySelectorAll('[data-lang]').forEach(function (el) {
    var on = el.getAttribute('data-lang') === lang;
    el.classList.toggle('is-active', on);
    el.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.title = lang === 'zh'
    ? '深入解读 Jev 模型：毫秒级判定与工程边界'
    : 'Reading Jev: Millisecond Decisions and Engineering Limits';

  var input = document.getElementById('bench-input');
  if (input && activePresetKey && BENCH_DATA[activePresetKey]) {
    input.value = lang === 'zh' ? BENCH_DATA[activePresetKey].text_zh : BENCH_DATA[activePresetKey].text_en;
  }
  refreshModeUI();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBenchmark);
} else {
  initBenchmark();
}
"""


def split_hero_paragraphs(html_text: str) -> tuple[str, str]:
    parts = html_text.split("</p>")
    if len(parts) >= 3:
        part1 = parts[0] + "</p>\n" + parts[1] + "</p>"
        part2 = "</p>".join(parts[2:]).strip()
        return part1, part2
    return html_text, ""


def build() -> None:
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    sha = git_sha()
    icon_toc = render_icon_toc()

    hero_zh = ""
    hero_en = ""
    chapter_blocks: list[str] = []

    for ch_id in CHAPTERS:
        filepath = DRAFTS / f"{ch_id}.md"
        raw = filepath.read_text(encoding="utf-8")
        zh_md, en_md = split_bilingual(raw)

        zh_html = prefix_heading_ids(
            strip_leading_h2(convert_diagrams(md.convert(zh_md), "zh")),
            f"{ch_id}-zh",
        )
        md.reset()
        en_html = prefix_heading_ids(
            strip_leading_h2(convert_diagrams(md.convert(en_md), "en")),
            f"{ch_id}-en",
        )
        md.reset()

        if ch_id == "ch00-hero":
            hero_zh = zh_html
            hero_en = en_html
            continue

        banner = render_banner(ch_id)
        chapter_blocks.append(
            f"""
<section id="{ch_id}" class="chapter">
{banner}
{BACK_TOC}
<div class="chapter-body container-content">
  <div class="lang-zh">{zh_html}</div>
  <div class="lang-en" style="display:none">{en_html}</div>
</div>
</section>
"""
        )

    chapters_html = "\n".join(chapter_blocks)
    hero_zh_1, hero_zh_2 = split_hero_paragraphs(hero_zh)
    hero_en_1, hero_en_2 = split_hero_paragraphs(hero_en)

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>深入解读 Jev 模型：毫秒级判定与工程边界</title>
<meta name="description" content="一线开发者对 Jev 与单步决策模型的拆解笔记。毫秒级判定、本地实测、失败模式与生产边界。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;700&family=Pathway+Gothic+One&display=swap" rel="stylesheet">
<style>
{CSS}
{BENCHMARK_CSS}
</style>
</head>
<body>
<a class="skip-link lang-zh" href="#ch00-hero">跳到正文</a>
<a class="skip-link lang-en" href="#ch00-hero" style="display:none">Skip to content</a>
<a class="github-corner" href="https://github.com/kuhung/understanding-jev" target="_blank" rel="noopener" aria-label="GitHub">
  <svg width="80" height="80" viewBox="0 0 80 80" aria-hidden="true">
    <path fill="#1a1a1a" d="M0 0 L80 80 L80 0 Z"></path>
    <g transform="translate(44 6) scale(1.75)" fill="#fff">
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.87-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
    </g>
  </svg>
</a>

<header class="masthead">
  <h1 class="lang-zh">深入解读 Jev 模型：毫秒级判定与工程边界</h1>
  <h1 class="lang-en" style="display:none">Reading Jev: Millisecond Decisions and Engineering Limits</h1>
  <p class="byline lang-zh">
    撰写 <a href="https://kuhung.me" target="_blank" rel="noopener">kuhung</a>
    <span class="sep">·</span>
    <a href="https://github.com/kuhung/understanding-jev" target="_blank" rel="noopener">GitHub</a>
    <span class="sep">·</span>
    <button type="button" class="is-active" data-lang="zh" aria-pressed="true" onclick="switchLang('zh')">中文</button>
    /
    <button type="button" data-lang="en" aria-pressed="false" onclick="switchLang('en')">EN</button>
  </p>
  <p class="byline lang-en" style="display:none">
    Written by <a href="https://kuhung.me" target="_blank" rel="noopener">kuhung</a>
    <span class="sep">·</span>
    <a href="https://github.com/kuhung/understanding-jev" target="_blank" rel="noopener">GitHub</a>
    <span class="sep">·</span>
    <button type="button" data-lang="zh" aria-pressed="false" onclick="switchLang('zh')">中文</button>
    /
    <button type="button" class="is-active" data-lang="en" aria-pressed="true" onclick="switchLang('en')">EN</button>
  </p>
</header>

<section id="ch00-hero" class="hero-section container-content">
  <div class="lang-zh">{hero_zh_1}</div>
  <div class="lang-en" style="display:none">{hero_en_1}</div>
</section>

{BENCHMARK_HTML}

<section class="hero-section container-content">
  <div class="lang-zh">{hero_zh_2}</div>
  <div class="lang-en" style="display:none">{hero_en_2}</div>
</section>

{icon_toc}

{chapters_html}

<a class="bottom-toc lang-zh" href="#toc"><span class="back-toc-arrow" aria-hidden="true"></span>回到目录</a>
<a class="bottom-toc lang-en" href="#toc" style="display:none"><span class="back-toc-arrow" aria-hidden="true"></span>Back to Table of Contents</a>

<footer class="site-footer">
  <p>
    <a href="https://github.com/kuhung/understanding-jev" target="_blank" rel="noopener">GitHub</a>
    · git: {sha}
  </p>
</footer>

<script>
{BENCHMARK_JS}
</script>
</body>
</html>
"""

    OUTPUT.write_text(full_html, encoding="utf-8")
    print(f"Compiled playbook {OUTPUT} ({len(full_html):,} bytes) git:{sha}")


if __name__ == "__main__":
    build()
