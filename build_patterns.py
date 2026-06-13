#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_patterns.py — render patterns_data.py into patterns.html

A single long reference page: "72 Japanese Sentence Patterns", trilingual
(Japanese + Simplified Chinese + English). Each pattern is a self-contained
"double-spread" block — the Japanese pattern in focus (headword, formula,
note) followed by everyday example sentences shown in all three languages.

Reuses the site's tap-to-expand breakdown (.s / .bd) and furigana toggle
(body.no-furigana) components from graded-readers/chapter-01.html, styled
with a distinct pink/magenta accent (#ec4899).

Content lives in patterns_data.py (separation of content from template, in
the spirit of build_chapters.py). This script only renders + validates.
"""

import html
import os
import re

from patterns_data import PATTERNS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "patterns.html")

# --- furigana helpers --------------------------------------------------------
RUBY_RE = re.compile(r"<ruby>.*?</ruby>", re.S)


def strip_ruby(s):
    """Return the base text of a furigana string (drop <rt> readings, keep kanji)."""
    s = re.sub(r"<rt>.*?</rt>", "", s)
    s = s.replace("<ruby>", "").replace("</ruby>", "")
    return s


# --- validation --------------------------------------------------------------
def validate(patterns):
    assert len(patterns) == 72, f"expected 72 patterns, got {len(patterns)}"
    nums = [p["num"] for p in patterns]
    assert nums == list(range(1, 73)), f"nums must be 1..72 in order, got {nums}"
    ex_total = 0
    for p in patterns:
        for key in ("jp", "romaji", "name", "formula", "note", "examples"):
            assert p.get(key), f"pattern {p['num']} missing '{key}'"
        assert 2 <= len(p["examples"]) <= 3, (
            f"pattern {p['num']} has {len(p['examples'])} examples (want 2-3)"
        )
        for e in p["examples"]:
            for key in ("jp", "romaji", "en", "zh", "pinyin", "bd"):
                assert e.get(key), f"pattern {p['num']} example missing '{key}'"
            assert len(e["bd"]) >= 1, f"pattern {p['num']} example empty breakdown"
            ex_total += 1
    return ex_total


# --- rendering ---------------------------------------------------------------
def render_example(e):
    words = "".join(
        f'<span class="w"><span class="word">{w}</span>'
        f'<span class="gl">[{html.escape(g)}]</span></span>'
        for w, g in e["bd"]
    )
    return f"""        <div class="s">
          <p class="jp">{e['jp']}</p>
          <p class="zh">{html.escape(e['zh'])}<span class="pinyin">{html.escape(e['pinyin'])}</span></p>
          <p class="en">{html.escape(e['en'])}</p>
          <div class="bd" hidden>
            {words}
            <p class="romaji">{html.escape(e['romaji'])}</p>
          </div>
        </div>"""


def render_pattern(p):
    examples = "\n".join(render_example(e) for e in p["examples"])
    return f"""      <section class="pat" id="p{p['num']}">
        <div class="pat-head">
          <span class="pat-num">{p['num']:02d}</span>
          <div class="pat-headtext">
            <h2 class="pat-jp">{p['jp']}</h2>
            <p class="pat-romaji">{html.escape(p['romaji'])}</p>
          </div>
          <p class="pat-name">{html.escape(p['name'])}</p>
        </div>
        <div class="pattern-box"><span class="pb-label">Pattern</span>{p['formula']}</div>
        <p class="note">{p['note']}</p>
        <div class="examples">
{examples}
        </div>
        <p class="backtotop"><a href="#toc">↑ contents</a></p>
      </section>"""


def render_toc(patterns):
    items = "\n".join(
        f'      <a class="toc-item" href="#p{p["num"]}">'
        f'<span class="toc-num">{p["num"]:02d}</span>'
        f'<span class="toc-jp">{strip_ruby(p["jp"])}</span></a>'
        for p in patterns
    )
    return items


CSS = """
    :root { --accent: #ec4899; --accent-dark: #be185d; --accent-soft: #fdf2f8; }
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      max-width: 720px;
      margin: 0 auto;
      padding: 40px 20px 80px;
      line-height: 1.6;
      color: #1a1a1a;
    }
    .nav { padding: 10px 0; margin-bottom: 20px; border-bottom: 1px solid #ccc; }
    .nav a { color: #2563eb; text-decoration: none; font-size: 0.95rem; }
    .nav a:hover { text-decoration: underline; }
    .nav a + a { margin-left: 18px; }

    header { margin-bottom: 12px; padding-bottom: 20px; border-bottom: 2px solid #f0d9e7; }
    h1 { font-size: 1.85rem; font-weight: 700; margin: 0 0 6px; }
    h1 .jp-title { color: var(--accent-dark); }
    .subtitle { color: #666; font-size: 0.95rem; margin: 0 0 4px; }
    .lang-key { color: #999; font-size: 0.85rem; margin: 8px 0 0; }
    .lang-key b { color: var(--accent-dark); font-weight: 600; }

    /* Furigana toggle */
    .toggle-bar { display: flex; gap: 8px; align-items: center; margin: 18px 0 4px; }
    .toggle-label { font-size: 0.82rem; color: #888; }
    .toggle-btn {
      border: 1px solid #d1d5db; background: #fff; color: #555;
      border-radius: 20px; padding: 5px 14px; font-size: 0.82rem; cursor: pointer;
      transition: all 0.12s;
    }
    .toggle-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

    /* Table of contents */
    .toc { margin: 22px 0 10px; }
    .toc h2 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: #999; margin: 0 0 10px; }
    .toc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 2px 10px; }
    .toc-item { display: flex; gap: 8px; align-items: baseline; padding: 4px 6px; border-radius: 6px;
      text-decoration: none; color: #333; font-size: 0.9rem; }
    .toc-item:hover { background: var(--accent-soft); }
    .toc-num { color: var(--accent); font-weight: 700; font-size: 0.78rem; min-width: 20px; }
    .toc-jp { color: #333; }

    /* Pattern block */
    .pat {
      margin: 14px -16px; padding: 22px 16px 8px;
      border-top: 1px solid #f0e3eb; scroll-margin-top: 12px;
    }
    .pat-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
    .pat-num {
      font-size: 0.9rem; font-weight: 800; color: #fff; background: var(--accent);
      border-radius: 8px; padding: 3px 9px; letter-spacing: 0.02em;
    }
    .pat-headtext { flex: 1 1 auto; }
    .pat-jp { font-size: 1.6rem; font-weight: 700; margin: 0; color: #1a1a1a; line-height: 1.25; }
    .pat-romaji { margin: 2px 0 0; color: #999; font-size: 0.9rem; font-style: italic; }
    .pat-name { margin: 0; color: var(--accent-dark); font-weight: 600; font-size: 1rem; flex: 0 0 auto; }

    .pattern-box {
      background: var(--accent-soft); border-left: 4px solid var(--accent);
      border-radius: 8px; padding: 10px 14px; margin: 14px 0 6px;
      font-size: 1.05rem; line-height: 1.7;
    }
    .pb-label {
      display: inline-block; font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.07em;
      font-weight: 700; color: var(--accent-dark); margin-right: 10px; vertical-align: 1px;
    }
    .note { margin: 8px 0 14px; color: #444; font-size: 0.94rem; }

    /* Example cards (tap to expand) */
    .examples { margin-top: 4px; }
    .s {
      padding: 10px 12px; margin: 8px -12px; border-radius: 10px; cursor: pointer;
      border-left: 4px solid transparent; background: #fafafa;
      transition: background-color 0.12s, border-color 0.12s;
    }
    .s:hover { background-color: #f5f7fa; }
    .s.active { background-color: #fff; border-left-color: var(--accent); box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .jp { font-size: 1.2rem; margin: 0; line-height: 2.1; }
    .zh { font-size: 1.02rem; margin: 3px 0 0; color: #1f2937; }
    .zh .pinyin { color: #9ca3af; font-size: 0.82rem; margin-left: 8px; font-style: italic; }
    .en { margin: 3px 0 0; color: #6b7280; font-size: 0.92rem; font-style: italic; }
    ruby { ruby-position: over; }
    rt { font-size: 0.55em; color: #aaa; font-weight: 400; }
    body.no-furigana rt { display: none; }

    .bd { background: #f0f4f8; border-radius: 6px; padding: 10px 14px; margin-top: 8px; font-size: 0.9rem; line-height: 1.9; }
    .w { display: inline-block; margin: 2px 8px 2px 0; white-space: nowrap; }
    .word { font-weight: 600; }
    .gl { color: #555; font-size: 0.85em; }
    .romaji { margin: 6px 0 0; padding-top: 6px; border-top: 1px solid #dfe3e8; color: #888; font-size: 0.85em; font-style: italic; }

    .backtotop { margin: 10px 0 0; text-align: right; }
    .backtotop a { color: #c0c0c0; text-decoration: none; font-size: 0.78rem; }
    .backtotop a:hover { color: var(--accent); }

    @media (max-width: 768px) {
      body { padding: 20px 16px 60px; }
      .pat-name { flex-basis: 100%; }
    }
"""

JS = """
    // Tap a sentence to reveal its word-by-word breakdown (one open at a time).
    document.querySelectorAll('.s').forEach(function (s) {
      s.addEventListener('click', function (e) {
        if (e.target.closest('a')) return;
        var bd = s.querySelector('.bd');
        if (!bd) return;
        if (bd.hidden) {
          document.querySelectorAll('.bd:not([hidden])').forEach(function (other) {
            other.hidden = true;
            other.closest('.s').classList.remove('active');
          });
          bd.hidden = false;
          s.classList.add('active');
        } else {
          bd.hidden = true;
          s.classList.remove('active');
        }
      });
    });

    // Furigana toggle.
    (function () {
      var btn = document.getElementById('furi-toggle');
      btn.addEventListener('click', function () {
        document.body.classList.toggle('no-furigana');
        var on = !document.body.classList.contains('no-furigana');
        btn.classList.toggle('active', on);
        btn.textContent = on ? 'Furigana: on' : 'Furigana: off';
      });
    })();
"""


def build():
    ex_total = validate(PATTERNS)
    toc = render_toc(PATTERNS)
    blocks = "\n".join(render_pattern(p) for p in PATTERNS)

    doc = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>72 Japanese Sentence Patterns — Cure Dolly Textbook</title>
  <style>{CSS}  </style>
</head>
<body>

<div class="nav"><a href="index.html">← Home</a><a href="graded-readers/index.html">Graded Readers</a><a href="onomatopoeia.html">Onomatopoeia</a></div>

<header>
  <h1>72 Japanese Sentence Patterns</h1>
  <p class="subtitle">The most useful everyday patterns — each shown three ways, side by side.</p>
  <p class="lang-key">Every example appears in <b>日本語</b> (Japanese), <b>中文</b> (Simplified Chinese + pinyin), and English. Tap any sentence for a word-by-word breakdown.</p>
  <div class="toggle-bar">
    <span class="toggle-label">Reading aid:</span>
    <button id="furi-toggle" class="toggle-btn active" type="button">Furigana: on</button>
  </div>
</header>

<nav class="toc" id="toc">
  <h2>All 72 patterns</h2>
  <div class="toc-grid">
{toc}
  </div>
</nav>

<main>
{blocks}
</main>

<div class="nav" style="margin-top: 30px; border-top: 1px solid #ccc; border-bottom: none;"><a href="index.html">← Home</a><a href="#toc">↑ Contents</a></div>

<script>{JS}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)

    # post-write sanity: ids unique + every toc link resolves
    ids = re.findall(r'id="p(\d+)"', doc)
    assert len(ids) == len(set(ids)) == 72, "pattern ids not unique/72"
    for href in re.findall(r'href="#p(\d+)"', doc):
        assert f'id="p{href}"' in doc, f"dangling toc link #p{href}"

    print(f"wrote {OUT}")
    print(f"  patterns: {len(PATTERNS)}")
    print(f"  examples: {ex_total}")
    print(f"  bytes:    {len(doc.encode('utf-8'))}")


if __name__ == "__main__":
    build()
