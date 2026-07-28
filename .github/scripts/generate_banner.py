#!/usr/bin/env python3
"""
Generate dark.svg and light.svg animated hero banners for the GitHub profile.

Design: Terminal-style window with animated gradient name, floating particles,
cycling tech tags, pulsing cursor, and accent gradient line.

Output: Pure SVG with SMIL animations — no embedded images, no external fonts,
no JavaScript. Renders correctly on GitHub via raw.githubusercontent.com.
Target file size: < 150 KB each.
"""

import os
import math
import random

random.seed(42)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H = 1180, 320

THEMES = {
    "dark": {
        "bg":       "#0A101F",
        "bg2":      "#0C1426",
        "bar":      "#0B1222",
        "frame":    "#1E293B",
        "cyan":     "#22D3EE",
        "violet":   "#A78BFA",
        "emerald":  "#10B981",
        "text":     "#F8FAFC",
        "muted":    "#94A3B8",
        "dim":      "#334155",
        "particle": "#22D3EE",
    },
    "light": {
        "bg":       "#F8FAFC",
        "bg2":      "#FFFFFF",
        "bar":      "#F1F5F9",
        "frame":    "#E2E8F0",
        "cyan":     "#0891B2",
        "violet":   "#7C3AED",
        "emerald":  "#059669",
        "text":     "#0F172A",
        "muted":    "#475569",
        "dim":      "#CBD5E1",
        "particle": "#0891B2",
    },
}

TAGS_A = ["Terraform", "Kubernetes", "ArgoCD", "Docker", "AWS ECS", "GitHub Actions"]
TAGS_B = ["AWS EKS",   "Helm",       "Python",  "Grafana", "Ansible", "Prometheus"]

FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(theme_name: str) -> str:
    t = THEMES[theme_name]
    random.seed(42)
    out = []
    a = out.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"'
      f' width="{W}" height="{H}" role="img"'
      f' aria-label="Surya Prakash – Cloud &amp; Platform Engineer">')

    # ── DEFS ─────────────────────────────────────────────────────────────────
    a('<defs>')

    # Background gradient
    a(f'<linearGradient id="bgG" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0%" stop-color="{t["bg"]}"/>'
      f'<stop offset="100%" stop-color="{t["bg2"]}"/>'
      f'</linearGradient>')

    # Name gradient (animated colour-cycle)
    a(f'<linearGradient id="nameG" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0%"   stop-color="{t["cyan"]}">'
      f'<animate attributeName="stop-color" dur="6s" repeatCount="indefinite"'
      f' values="{t["cyan"]};{t["violet"]};{t["emerald"]};{t["cyan"]}"/></stop>'
      f'<stop offset="100%" stop-color="{t["violet"]}">'
      f'<animate attributeName="stop-color" dur="6s" repeatCount="indefinite"'
      f' values="{t["violet"]};{t["emerald"]};{t["cyan"]};{t["violet"]}"/></stop>'
      f'</linearGradient>')

    # Accent line gradient
    a(f'<linearGradient id="acG" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0%"   stop-color="{t["violet"]}"/>'
      f'<stop offset="50%"  stop-color="{t["cyan"]}"/>'
      f'<stop offset="100%" stop-color="{t["emerald"]}"/>'
      f'</linearGradient>')

    # Glow filter
    a('<filter id="glow" x="-20%" y="-40%" width="140%" height="180%">'
      '<feGaussianBlur stdDeviation="4" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
      '</filter>')

    a('</defs>')

    # ── BACKGROUND ───────────────────────────────────────────────────────────
    a(f'<rect width="{W}" height="{H}" fill="url(#bgG)"/>')

    # ── PARTICLES (80 dots — keeps file small) ────────────────────────────────
    for _ in range(80):
        px  = random.randint(15, W - 15)
        py  = random.randint(15, H - 15)
        r   = round(random.uniform(0.7, 2.2), 1)
        dur = round(random.uniform(5, 14), 1)
        dy  = random.randint(-25, 25)
        dx  = random.randint(-18, 18)
        dly = round(random.uniform(0, dur), 1)
        op  = round(random.uniform(0.06, 0.28), 2)
        op2 = round(min(op * 2.2, 0.55), 2)
        a(f'<circle cx="{px}" cy="{py}" r="{r}" fill="{t["particle"]}" opacity="{op}">'
          f'<animate attributeName="cy" values="{py};{py+dy};{py}" dur="{dur}s"'
          f' begin="-{dly}s" repeatCount="indefinite"/>'
          f'<animate attributeName="cx" values="{px};{px+dx};{px}" dur="{dur*1.3:.1f}s"'
          f' begin="-{dly}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="{op};{op2};{op}" dur="{dur}s"'
          f' begin="-{dly}s" repeatCount="indefinite"/>'
          f'</circle>')

    # ── TERMINAL CHROME ───────────────────────────────────────────────────────
    # Card background
    a(f'<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="12"'
      f' fill="{t["bg"]}" opacity="0.6"/>')
    a(f'<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="12"'
      f' fill="none" stroke="{t["frame"]}" stroke-width="1.5"/>')

    # Title bar
    a(f'<rect x="20" y="20" width="{W-40}" height="42" rx="12" fill="{t["bar"]}"/>')
    a(f'<rect x="20" y="50" width="{W-40}" height="12" fill="{t["bar"]}"/>')

    # Window buttons
    for bx, bc in ((44, "#EF4444"), (64, "#F59E0B"), (84, "#10B981")):
        a(f'<circle cx="{bx}" cy="41" r="6" fill="{bc}"/>')

    # Title bar label
    a(f'<text x="{W//2}" y="47" text-anchor="middle"'
      f' font-family="{FONT}" font-size="13" fill="{t["muted"]}">'
      f'profile.sh --animated --live</text>')

    # @Handle pill (right of buttons)
    a(f'<rect x="108" y="28" width="124" height="25" rx="5"'
      f' fill="{t["cyan"]}" opacity="0.12"/>')
    a(f'<rect x="108" y="28" width="124" height="25" rx="5"'
      f' fill="none" stroke="{t["cyan"]}" stroke-width="1" opacity="0.6"/>')
    a(f'<text x="170" y="44" text-anchor="middle"'
      f' font-family="{FONT}" font-size="12" fill="{t["cyan"]}" font-weight="bold">'
      f'@Aries-Surya</text>')

    # LIVE badge
    a(f'<circle cx="{W-60}" cy="41" r="5" fill="#EF4444">'
      f'<animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/>'
      f'</circle>')
    a(f'<text x="{W-50}" y="45" font-family="{FONT}" font-size="11"'
      f' fill="#EF4444" font-weight="bold">LIVE</text>')

    # ── MAIN CONTENT ──────────────────────────────────────────────────────────
    cy_name = 143

    # Name (big, gradient, glowing)
    a(f'<text x="{W//2}" y="{cy_name}" text-anchor="middle"'
      f' font-family="{FONT}" font-size="58" font-weight="900"'
      f' fill="url(#nameG)" filter="url(#glow)">Surya Prakash</text>')

    # Role subtitle
    cy_role = cy_name + 38
    a(f'<text x="{W//2}" y="{cy_role}" text-anchor="middle"'
      f' font-family="{FONT}" font-size="19" fill="{t["muted"]}">'
      f'Cloud &amp; Platform Engineer  ·  DevOps  ·  MLOps</text>')

    # Terminal prompt line
    cy_prompt = cy_role + 34
    prompt_x = W // 2 - 360
    a(f'<text x="{prompt_x}" y="{cy_prompt}"'
      f' font-family="{FONT}" font-size="14" fill="{t["cyan"]}" font-weight="bold">'
      f'aries-surya@cloud:~$</text>')
    a(f'<text x="{prompt_x + 185}" y="{cy_prompt}"'
      f' font-family="{FONT}" font-size="14" fill="{t["text"]}">'
      f' ./stack.sh --show-all</text>')

    # Blinking cursor
    cur_x = prompt_x + 328
    a(f'<rect x="{cur_x}" y="{cy_prompt-13}" width="9" height="16" fill="{t["cyan"]}">'
      f'<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/>'
      f'</rect>')

    # ── TECH TAG PILLS (two groups cycling) ───────────────────────────────────
    cy_tags = cy_prompt + 32
    total_dur = 10  # seconds per full cycle

    def tag_pill_group(tags, t_begin, t_on):
        widths = [len(tag) * 8.6 + 28 for tag in tags]
        total_w = sum(widths) + (len(tags) - 1) * 10
        tx = W // 2 - int(total_w // 2)
        for tag, tw in zip(tags, widths):
            tw = int(tw)
            # Pill background
            kf_op_bg = f"0;0;0.18;0.18;0"
            kf_time  = f"0;{t_begin/total_dur:.3f};{(t_begin+0.6)/total_dur:.3f};" \
                       f"{(t_begin+t_on)/total_dur:.3f};{(t_begin+t_on+0.8)/total_dur:.3f}"
            a(f'<rect x="{tx}" y="{cy_tags-16}" width="{tw}" height="22" rx="11"'
              f' fill="{t["violet"]}" opacity="0">'
              f'<animate attributeName="opacity" values="{kf_op_bg}"'
              f' keyTimes="{kf_time}" dur="{total_dur}s" repeatCount="indefinite"/>'
              f'</rect>')
            # Tag text
            kf_op_tx = f"0;0;1;1;0"
            a(f'<text x="{tx + tw//2}" y="{cy_tags}" text-anchor="middle"'
              f' font-family="{FONT}" font-size="13" fill="{t["violet"]}" opacity="0">'
              f'<animate attributeName="opacity" values="{kf_op_tx}"'
              f' keyTimes="{kf_time}" dur="{total_dur}s" repeatCount="indefinite"/>'
              f'{esc(tag)}</text>')
            tx += tw + 10

    tag_pill_group(TAGS_A, t_begin=0,   t_on=4.2)
    tag_pill_group(TAGS_B, t_begin=5.2, t_on=4.2)

    # ── ACCENT BOTTOM LINE ────────────────────────────────────────────────────
    a(f'<rect x="20" y="{H-24}" width="{W-40}" height="3" rx="1.5"'
      f' fill="url(#acG)">'
      f'<animate attributeName="opacity" values="0.6;1;0.6" dur="3s" repeatCount="indefinite"/>'
      f'</rect>')

    a('</svg>')
    return "\n".join(out)


if __name__ == "__main__":
    for theme in ("dark", "light"):
        svg_content = build(theme)
        out_path = os.path.join(ROOT, f"{theme}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  {theme}.svg  ->  {size_kb:.1f} KB  ({out_path})")
    print("Done.")
