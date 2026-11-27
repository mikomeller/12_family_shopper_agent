#!/usr/bin/env python3
"""
Author:    mikomeller
Version:   0.1.0
Filename:  build_html.py
Pathname:  pitch/build_html.py
Purpose:   Turn pitch/pitch.md (Marp Markdown) into pitch/pitch.html: one self-contained file, no internet needed,
           arrow keys / space / click to move, N toggles speaker notes, F for full screen.
Usage:     pip install markdown && python3 pitch/build_html.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / "pitch.md", HERE / "pitch.html"

CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#0f172a;font-family:system-ui,-apple-system,Segoe UI,sans-serif}
.slide{display:none;position:absolute;inset:0;margin:auto;width:min(100vw,177.78vh);height:min(56.25vw,100vh);
background:#fff;color:#0f172a;padding:5vh 6vh;overflow:hidden;font-size:min(2.1vw,3.7vh)}
.slide.on{display:block}.slide.title{background:linear-gradient(135deg,#1e3a8a,#0f766e);color:#fff}
.slide.title h1{font-size:2.6em;margin-top:18vh}.slide.title code{color:#fff;background:rgba(255,255,255,.15)}
h1{font-size:1.9em;margin:.2em 0 .4em}h2{font-size:1.45em;margin:.1em 0 .6em;color:#1e3a8a}.title h2{color:#a7f3d0}
em{color:#0f766e;font-style:normal}.title em{color:#a7f3d0}strong{color:#b91c1c}.title strong{color:#fde68a}
table{border-collapse:collapse;width:100%;font-size:.78em;margin:.4em 0}th,td{border-bottom:1px solid #cbd5e1;padding:.35em .5em;text-align:left}
th{background:#e2e8f0}pre{background:#0f172a;color:#e2e8f0;padding:.6em 1em;border-radius:8px;font-size:.62em;line-height:1.25;margin:.2em 0}
code{background:#e2e8f0;padding:0 .2em;border-radius:4px}pre code{background:none;padding:0}li{margin:.25em 0}
.notes{display:none;position:absolute;left:0;right:0;bottom:0;background:#fef3c7;color:#78350f;font-size:.6em;padding:.6em 1em}
body.shownotes .notes{display:block}.num{position:absolute;right:2vh;bottom:1.5vh;font-size:.55em;color:#64748b}
"""
JS = """
const s=[...document.querySelectorAll('.slide')];let i=Math.max(0,Math.min(s.length-1,(parseInt(location.hash.slice(1))||1)-1));
function show(){s.forEach((e,k)=>e.classList.toggle('on',k===i));location.hash=i+1}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key))i=Math.min(s.length-1,i+1);
else if(['ArrowLeft','PageUp'].includes(e.key))i=Math.max(0,i-1);else if(e.key==='Home')i=0;else if(e.key==='End')i=s.length-1;
else if(e.key==='n'||e.key==='N')document.body.classList.toggle('shownotes');
else if(e.key==='f'||e.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}
else return;show()});document.addEventListener('click',e=>{i=e.clientX<innerWidth/3?Math.max(0,i-1):Math.min(s.length-1,i+1);show()});show();
"""


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)          # Marp front matter
    text = re.sub(r"\A\s*<!--\s*\nAuthor:.*?-->\n", "", text, flags=re.S)  # file header
    title = "Family Shopper Agent — pitch"
    slides = []
    for n, chunk in enumerate(re.split(r"\n---\n", text), start=1):
        notes = " ".join(m.strip() for m in re.findall(r"<!--(.*?)-->", chunk, flags=re.S))
        body = re.sub(r"<!--.*?-->", "", chunk, flags=re.S)
        inner = markdown.markdown(body, extensions=["tables", "fenced_code"])
        cls = "slide title" if n == 1 else "slide"
        note_html = f'<div class="notes">{html.escape(notes)}</div>' if notes else ""
        slides.append(f'<section class="{cls}">{inner}{note_html}<div class="num">{n}</div></section>')
    OUT.write_text(
        "<!DOCTYPE html>\n<!--\nAuthor:    mikomeller\nVersion:   0.1.0\nFilename:  pitch.html\n"
        "Pathname:  pitch/pitch.html\nPurpose:   Generated from pitch/pitch.md by pitch/build_html.py; do not edit by hand.\n-->\n"
        f'<html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>'
        f"<body>{''.join(slides)}<script>{JS}</script></body></html>\n",
        encoding="utf-8",
    )
    print(f"{OUT.name}: {len(slides)} slides")


if __name__ == "__main__":
    main()
