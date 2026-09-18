"""
Editorial line-art for the Jev playbook.

Nine chapter icons (table of contents) and nine chapter banners.
Stroke-based engineering sketches, not character illustrations.
"""

ICON_CHAPTERS = [
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
    "ch03-run-it-yourself": ("20行代码实测", "20 Lines of Code"),
    "ch04-10k-probes": ("压测数据分析", "Benchmark Data"),
    "ch05-failure-lessons": ("失败模式", "Failure Modes"),
    "ch06-four-patterns": ("四种设计模式", "Four Patterns"),
    "ch07-production-architecture": ("生产架构", "Production Architecture"),
    "ch08-ecosystem-map": ("生态地图", "Ecosystem Map"),
    "ch09-should-you-use-it": ("该不该用", "Should You Use It"),
}

BANNER_BG = {
    "ch01-what-is-jev": "#dff6fa",
    "ch02-under-the-hood": "#f3efe6",
    "ch03-run-it-yourself": "#eef2e8",
    "ch04-10k-probes": "#f4eee8",
    "ch05-failure-lessons": "#f3eaea",
    "ch06-four-patterns": "#eceef6",
    "ch07-production-architecture": "#e8f0ec",
    "ch08-ecosystem-map": "#f0eef6",
    "ch09-should-you-use-it": "#f6f1e8",
}

BANNER_ALIGN = {
    "ch01-what-is-jev": "left",
    "ch02-under-the-hood": "right",
    "ch03-run-it-yourself": "left",
    "ch04-10k-probes": "right",
    "ch05-failure-lessons": "left",
    "ch06-four-patterns": "right",
    "ch07-production-architecture": "left",
    "ch08-ecosystem-map": "right",
    "ch09-should-you-use-it": "left",
}

_STROKE = (
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"'
)


def _icon(body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" '
        f'{_STROKE} aria-hidden="true">{body}</svg>'
    )


def _banner(body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 280" '
        f'fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


ICONS = {
    "ch01-what-is-jev": _icon(
        '<rect x="16" y="14" width="48" height="16" rx="2"/>'
        '<rect x="16" y="32" width="48" height="16" rx="2"/>'
        '<rect x="16" y="50" width="48" height="16" rx="2"/>'
        '<circle cx="26" cy="22" r="3"/>'
        '<circle cx="26" cy="40" r="3" fill="currentColor" stroke="none"/>'
        '<circle cx="26" cy="58" r="3"/>'
        '<path d="M36 22h20M36 40h20M36 58h14"/>'
    ),
    "ch02-under-the-hood": _icon(
        '<rect x="10" y="26" width="28" height="28" rx="3"/>'
        '<path d="M18 34h12M18 40h8M18 46h10"/>'
        '<path d="M38 40h22"/>'
        '<path d="M52 32l10 8-10 8"/>'
        '<rect x="58" y="36" width="12" height="8" rx="1"/>'
    ),
    "ch03-run-it-yourself": _icon(
        '<rect x="12" y="16" width="56" height="48" rx="3"/>'
        '<path d="M12 26h56"/>'
        '<circle cx="20" cy="21" r="1.4" fill="currentColor" stroke="none"/>'
        '<circle cx="26" cy="21" r="1.4" fill="currentColor" stroke="none"/>'
        '<circle cx="32" cy="21" r="1.4" fill="currentColor" stroke="none"/>'
        '<path d="M22 38l8 6-8 6"/>'
        '<path d="M34 50h18"/>'
    ),
    "ch04-10k-probes": _icon(
        '<path d="M14 62V18h4"/>'
        '<path d="M14 62h54"/>'
        '<path d="M22 50 30 46 38 28 46 40 54 22 66 36"/>'
        '<circle cx="38" cy="28" r="2.2" fill="currentColor" stroke="none"/>'
        '<circle cx="54" cy="22" r="2.2" fill="currentColor" stroke="none"/>'
    ),
    "ch05-failure-lessons": _icon(
        '<path d="M18 28c0-6 5-10 11-10 5 0 9 3 10 8"/>'
        '<path d="M41 38c1 5 5 8 10 8 6 0 11-4 11-10 0-5-4-9-9-10"/>'
        '<path d="M34 36h12"/>'
        '<path d="M36 32l8 12M44 32l-8 12" opacity="0.85"/>'
    ),
    "ch06-four-patterns": _icon(
        '<rect x="14" y="14" width="24" height="24" rx="2"/>'
        '<rect x="42" y="14" width="24" height="24" rx="2"/>'
        '<rect x="14" y="42" width="24" height="24" rx="2"/>'
        '<rect x="42" y="42" width="24" height="24" rx="2"/>'
        '<path d="M20 26h12M26 20v12"/>'
        '<path d="M48 32l12-12"/>'
        '<circle cx="26" cy="54" r="4"/>'
        '<path d="M50 50h8v8"/>'
    ),
    "ch07-production-architecture": _icon(
        '<rect x="28" y="10" width="24" height="14" rx="2"/>'
        '<path d="M40 24v8"/>'
        '<path d="M18 48L40 32l22 16"/>'
        '<rect x="10" y="48" width="18" height="18" rx="2"/>'
        '<rect x="31" y="54" width="18" height="16" rx="2"/>'
        '<rect x="52" y="48" width="18" height="18" rx="2"/>'
    ),
    "ch08-ecosystem-map": _icon(
        '<circle cx="22" cy="24" r="3.2"/>'
        '<circle cx="50" cy="18" r="3.2"/>'
        '<circle cx="62" cy="42" r="3.2"/>'
        '<circle cx="40" cy="52" r="3.2"/>'
        '<circle cx="18" cy="48" r="3.2"/>'
        '<circle cx="36" cy="32" r="2.4"/>'
        '<path d="M22 24L36 32L50 18M36 32L40 52M36 32L18 48M40 52L62 42M50 18L62 42"/>'
    ),
    "ch09-should-you-use-it": _icon(
        '<path d="M40 14v40"/>'
        '<path d="M20 58h40"/>'
        '<path d="M18 30h44"/>'
        '<path d="M18 30l-8 16h16z"/>'
        '<path d="M62 30l-8 12h16z"/>'
        '<circle cx="40" cy="14" r="3"/>'
    ),
}


BANNERS = {
    "ch01-what-is-jev": _banner(
        '<path d="M20 230h520" opacity="0.45"/>'
        '<rect x="280" y="54" width="220" height="42" rx="4"/>'
        '<rect x="280" y="108" width="220" height="42" rx="4"/>'
        '<rect x="280" y="162" width="220" height="42" rx="4"/>'
        '<circle cx="304" cy="75" r="7"/>'
        '<circle cx="304" cy="129" r="7" fill="currentColor" stroke="none"/>'
        '<circle cx="304" cy="129" r="3" fill="#dff6fa" stroke="none"/>'
        '<circle cx="304" cy="183" r="7"/>'
        '<path d="M328 75h140M328 129h140M328 183h110"/>'
        '<path d="M250 129h22"/>'
        '<path d="M240 121l10 8-10 8"/>'
        '<rect x="70" y="88" width="160" height="86" rx="6"/>'
        '<path d="M90 112h120M90 128h88M90 144h104"/>'
    ),
    "ch02-under-the-hood": _banner(
        '<path d="M20 230h520" opacity="0.45"/>'
        '<rect x="48" y="70" width="150" height="130" rx="6"/>'
        '<path d="M72 96h102M72 114h76M72 132h90M72 150h64"/>'
        '<path d="M198 135h90"/>'
        '<path d="M268 119l28 16-28 16"/>'
        '<rect x="300" y="92" width="90" height="86" rx="6"/>'
        '<path d="M322 118h46M322 136h32"/>'
        '<path d="M390 135h70"/>'
        '<rect x="460" y="118" width="52" height="34" rx="3"/>'
        '<path d="M470 135h32"/>'
    ),
    "ch03-run-it-yourself": _banner(
        '<path d="M20 236h520" opacity="0.45"/>'
        '<rect x="90" y="40" width="380" height="180" rx="8"/>'
        '<path d="M90 68h380"/>'
        '<circle cx="112" cy="54" r="5" fill="currentColor" stroke="none" opacity="0.35"/>'
        '<circle cx="128" cy="54" r="5" fill="currentColor" stroke="none" opacity="0.35"/>'
        '<circle cx="144" cy="54" r="5" fill="currentColor" stroke="none" opacity="0.35"/>'
        '<path d="M120 100l18 12-18 12"/>'
        '<path d="M148 124h90"/>'
        '<path d="M120 154h220"/>'
        '<path d="M120 178h160"/>'
        '<rect x="120" y="196" width="10" height="14"/>'
    ),
    "ch04-10k-probes": _banner(
        '<path d="M40 230h500"/>'
        '<path d="M40 230V50h8"/>'
        '<path d="M70 190 120 170 170 92 230 148 290 70 360 118 430 64 500 96"/>'
        '<circle cx="170" cy="92" r="5" fill="currentColor" stroke="none"/>'
        '<circle cx="290" cy="70" r="5" fill="currentColor" stroke="none"/>'
        '<circle cx="430" cy="64" r="5" fill="currentColor" stroke="none"/>'
        '<path d="M170 92v138M290 70v160M430 64v166" opacity="0.2"/>'
    ),
    "ch05-failure-lessons": _banner(
        '<path d="M20 230h520" opacity="0.45"/>'
        '<path d="M90 150c0-34 28-56 60-56 26 0 48 16 54 40"/>'
        '<path d="M250 150c6 26 28 42 56 42 34 0 62-24 62-56 0-30-22-50-50-54"/>'
        '<path d="M214 148h70"/>'
        '<path d="M228 128l48 48M276 128l-48 48"/>'
        '<path d="M390 86l36 36M426 86l-36 36" opacity="0.7"/>'
        '<circle cx="408" cy="104" r="28"/>'
    ),
    "ch06-four-patterns": _banner(
        '<path d="M20 230h520" opacity="0.45"/>'
        '<rect x="70" y="48" width="180" height="150" rx="6"/>'
        '<rect x="270" y="48" width="180" height="150" rx="6"/>'
        '<path d="M100 90h120M160 60v120" opacity="0.7"/>'
        '<path d="M300 160 410 70"/>'
        '<circle cx="160" cy="123" r="10"/>'
        '<path d="M330 90h80v70"/>'
        '<rect x="70" y="210" width="80" height="8" rx="1" opacity="0.4"/>'
        '<rect x="270" y="210" width="80" height="8" rx="1" opacity="0.4"/>'
    ),
    "ch07-production-architecture": _banner(
        '<path d="M20 236h520" opacity="0.45"/>'
        '<rect x="210" y="28" width="140" height="36" rx="4"/>'
        '<path d="M280 64v28"/>'
        '<rect x="190" y="92" width="180" height="48" rx="6"/>'
        '<path d="M220 140 L90 186"/>'
        '<path d="M280 140v46"/>'
        '<path d="M340 140 L470 186"/>'
        '<rect x="40" y="186" width="110" height="40" rx="4"/>'
        '<rect x="225" y="186" width="110" height="40" rx="4"/>'
        '<rect x="410" y="186" width="110" height="40" rx="4"/>'
    ),
    "ch08-ecosystem-map": _banner(
        '<path d="M20 230h520" opacity="0.45"/>'
        '<circle cx="90" cy="150" r="8"/>'
        '<circle cx="170" cy="70" r="8"/>'
        '<circle cx="250" cy="160" r="8"/>'
        '<circle cx="330" cy="86" r="8"/>'
        '<circle cx="410" cy="150" r="8"/>'
        '<circle cx="480" cy="70" r="8"/>'
        '<circle cx="210" cy="110" r="5"/>'
        '<circle cx="370" cy="110" r="5"/>'
        '<path d="M90 150L170 70L210 110L250 160M170 70L330 86L370 110L410 150M330 86L480 70M250 160L410 150"/>'
        '<circle cx="250" cy="160" r="22" opacity="0.35"/>'
    ),
    "ch09-should-you-use-it": _banner(
        '<path d="M20 236h520" opacity="0.45"/>'
        '<path d="M280 36v160"/>'
        '<path d="M160 210h240"/>'
        '<path d="M120 96h320"/>'
        '<path d="M120 96L70 170h100z"/>'
        '<path d="M440 96l50 56h-100z"/>'
        '<circle cx="280" cy="36" r="10"/>'
        '<path d="M86 148h18M454 132h18" opacity="0.5"/>'
    ),
}


def render_icon_toc() -> str:
    def items(lang: str) -> str:
        bits = []
        for ch_id in ICON_CHAPTERS:
            zh, en = CHAPTER_TITLES[ch_id]
            label = zh if lang == "zh" else en
            bits.append(
                f'<li><a href="#{ch_id}" class="toc-item">'
                f'<div class="icon">{ICONS[ch_id]}</div>'
                f"<span>{label}</span></a></li>"
            )
        return "".join(bits)

    return f"""
<nav id="toc" aria-label="Chapters">
  <ul class="toc lang-zh">{items("zh")}</ul>
  <ul class="toc lang-en" style="display:none">{items("en")}</ul>
</nav>
"""


def render_banner(ch_id: str) -> str:
    zh, en = CHAPTER_TITLES[ch_id]
    align = BANNER_ALIGN[ch_id]
    bg = BANNER_BG[ch_id]
    art = BANNERS[ch_id]
    return f"""
<div class="chapter-banner align-{align}" style="background-color:{bg}" id="{ch_id}-banner">
  <div class="banner-inner">
    <h2 class="banner-title lang-zh">{zh}</h2>
    <h2 class="banner-title lang-en" style="display:none">{en}</h2>
    <div class="banner-art">{art}</div>
  </div>
</div>
"""
