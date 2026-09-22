# 深入解读 Jev / Reading Jev

[中文](#中文) | [English](#english)

## 中文

单页长文。拆 Jev 的单步判定、本地实测、失败模式和生产边界。

线上页面可切中英：[understanding-jev.vercel.app](https://understanding-jev.vercel.app)

- 在线 Demo：[askjev.kuhung.me](https://askjev.kuhung.me/)（用 Jev 辅助生活微决策的交互原型）
- 仓库：[github.com/kuhung/understanding-jev](https://github.com/kuhung/understanding-jev)

### 本地预览

```bash
uv run --with markdown --with pygments python3 scripts/build_site.py
python3 -m http.server 8765
```

正文在 `drafts/`，中英对照。完整文稿见 `zh-manuscript.md` 与 `en-manuscript.md`。

---

## English

A single-page essay. Jev's one-step decisions, local tests, failure modes, and production limits.

The live page can switch between Chinese and English: [understanding-jev.vercel.app](https://understanding-jev.vercel.app)

- Live Demo: [askjev.kuhung.me](https://askjev.kuhung.me/) (An interactive micro-decision prototype powered by Jev)
- Repo: [github.com/kuhung/understanding-jev](https://github.com/kuhung/understanding-jev)

### Local preview

```bash
uv run --with markdown --with pygments python3 scripts/build_site.py
python3 -m http.server 8765
```

Source lives in `drafts/` as bilingual Markdown. Full manuscripts: `zh-manuscript.md` and `en-manuscript.md`.
