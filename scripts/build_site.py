"""
Build script: compile bilingual Markdown drafts into a single-page
editorial playbook. Layout follows Startup Playbook: centered masthead,
icon chapter map, full-bleed chapter banners, 700px reading column.

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
.container-content a { color: var(--link); }
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
  width: 100%;
  margin: 80px 0 0;
  overflow: hidden;
  color: var(--art);
  position: relative;
}
.banner-inner {
  width: min(1200px, 100%);
  margin: 0 auto;
  height: 300px;
  position: relative;
}
.banner-title {
  position: absolute;
  top: 52px;
  z-index: 2;
  width: 700px;
  max-width: calc(100% - 48px);
  left: 50%;
  margin: 0 0 0 -350px;
  font-family: var(--display);
  font-size: 42px;
  font-weight: 400;
  letter-spacing: 0.04em;
  line-height: 1.15;
  color: var(--ink);
  text-wrap: balance;
}
.align-left .banner-title { text-align: left; padding-right: 240px; }
.align-right .banner-title { text-align: right; padding-left: 240px; }
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

.chapter-body { padding-top: 36px; }
.hero-section { padding-top: 0; }

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

@media (max-width: 760px) {
  .masthead h1 { font-size: 28px; padding-bottom: 14px; }
  .byline { margin-bottom: 40px; }
  .chapter-banner {
    height: auto;
    min-height: 280px;
    margin-top: 48px;
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
    font-size: 32px;
  }
  .banner-art {
    position: static;
    width: 100%;
    height: 180px;
  }
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
<div class="chapter-body container-content">
  <div class="lang-zh">{zh_html}</div>
  <div class="lang-en" style="display:none">{en_html}</div>
</div>
</section>
"""
        )

    chapters_html = "\n".join(chapter_blocks)

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
</style>
</head>
<body>
<a class="skip-link lang-zh" href="#ch00-hero">跳到正文</a>
<a class="skip-link lang-en" href="#ch00-hero" style="display:none">Skip to content</a>

<header class="masthead">
  <h1 class="lang-zh">深入解读 Jev 模型：毫秒级判定与工程边界</h1>
  <h1 class="lang-en" style="display:none">Reading Jev: Millisecond Decisions and Engineering Limits</h1>
  <p class="byline lang-zh">
    撰写 <a href="https://kuhung.me" target="_blank" rel="noopener">kuhung</a>
    <span class="sep">·</span>一线拆解
    <span class="sep">·</span>
    <button type="button" class="is-active" data-lang="zh" aria-pressed="true" onclick="switchLang('zh')">中文</button>
    /
    <button type="button" data-lang="en" aria-pressed="false" onclick="switchLang('en')">EN</button>
  </p>
  <p class="byline lang-en" style="display:none">
    Written by <a href="https://kuhung.me" target="_blank" rel="noopener">kuhung</a>
    <span class="sep">·</span>
    <button type="button" data-lang="zh" aria-pressed="false" onclick="switchLang('zh')">中文</button>
    /
    <button type="button" class="is-active" data-lang="en" aria-pressed="true" onclick="switchLang('en')">EN</button>
  </p>
</header>

<section id="ch00-hero" class="hero-section container-content">
  <div class="lang-zh">{hero_zh}</div>
  <div class="lang-en" style="display:none">{hero_en}</div>
</section>

{icon_toc}

{chapters_html}

<footer class="site-footer">
  <p>understanding-jev · git: {sha}</p>
</footer>

<script>
function switchLang(lang) {{
  document.querySelectorAll('.lang-zh').forEach(function (el) {{
    el.style.display = lang === 'zh' ? '' : 'none';
  }});
  document.querySelectorAll('.lang-en').forEach(function (el) {{
    el.style.display = lang === 'en' ? '' : 'none';
  }});
  document.querySelectorAll('[data-lang]').forEach(function (el) {{
    var on = el.getAttribute('data-lang') === lang;
    el.classList.toggle('is-active', on);
    el.setAttribute('aria-pressed', on ? 'true' : 'false');
  }});
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.title = lang === 'zh'
    ? '深入解读 Jev 模型：毫秒级判定与工程边界'
    : 'Reading Jev: Millisecond Decisions and Engineering Limits';
}}
</script>
</body>
</html>
"""

    OUTPUT.write_text(full_html, encoding="utf-8")
    print(f"Compiled playbook {OUTPUT} ({len(full_html):,} bytes) git:{sha}")


if __name__ == "__main__":
    build()
