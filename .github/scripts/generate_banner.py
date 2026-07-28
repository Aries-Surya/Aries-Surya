#!/usr/bin/env python3
"""
GitHub Profile Banner Generator — Full Portrait Line-by-Line Printing Loop.

Design:
  - Left panel (380×485): Complete, full dithered portrait of Surya Prakash (no grid lines, no cropping to eyes)
  - Animation: Matrix / Holographic print effect — scans and prints line-by-line from top to bottom,
    holds full portrait, then smoothly resets in a continuous loop.
  - NO third-party logos (no Python, Docker, Git logos)
  - Right panel (680×485): SYSTEM.INFO terminal details with dotted leaders & textLength locking
"""

import os, math, random
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from scipy.ndimage import distance_transform_edt, binary_closing, binary_fill_holes, label

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT        = os.path.dirname(os.path.dirname(SCRIPT_DIR))   # repo root
ASSETS      = os.path.join(ROOT, "assets")

# ── Palette ────────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":           "#0A101F",
        "frame":        "#1E293B",
        "bar":          "#0B1222",
        "label":        "#94A3B8",
        "value":        "#F8FAFC",
        "leader":       "#334155",
        "header_text":  "#E2E8F0",
        "chrome":       "#22D3EE",
        "portrait_col": "#A78BFA",
        "laser":        "#22D3EE",
        "pill_text":    "#0A101F",
    },
    "light": {
        "bg":           "#F8FAFC",
        "frame":        "#E2E8F0",
        "bar":          "#F1F5F9",
        "label":        "#64748B",
        "value":        "#0F172A",
        "leader":       "#CBD5E1",
        "header_text":  "#0F172A",
        "chrome":       "#0891B2",
        "portrait_col": "#7C3AED",
        "laser":        "#0891B2",
        "pill_text":    "#FFFFFF",
    },
}

# ── Layout constants ───────────────────────────────────────────────────────────
SVG_W, SVG_H  = 1180, 610
LEFT_X, LEFT_Y, LEFT_W, LEFT_H = 40, 85, 380, 485
INFO_X, INFO_Y, INFO_W, INFO_H = 460, 85, 680, 485
PORTRAIT_CX, PORTRAIT_CY       = 230, 305   # center of left panel

PRINT_LOOP_DUR = 6.0   # seconds per full print loop

# ── Floyd-Steinberg dithering ──────────────────────────────────────────────────
def dither_fs(arr_float: np.ndarray) -> np.ndarray:
    a   = arr_float.copy().astype(float)
    h, w = a.shape
    out  = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        rev = (y % 2 == 1)
        xs  = range(w-1, -1, -1) if rev else range(w)
        for x in xs:
            old = a[y, x]
            new = 255 if old > 127 else 0
            out[y, x] = new
            err = old - new
            if not rev:
                if x+1 < w:                     a[y, x+1]   += err * 7/16
                if y+1 < h and x-1 >= 0:        a[y+1, x-1] += err * 3/16
                if y+1 < h:                     a[y+1, x]   += err * 5/16
                if y+1 < h and x+1 < w:         a[y+1, x+1] += err * 1/16
            else:
                if x-1 >= 0:                     a[y, x-1]   += err * 7/16
                if y+1 < h and x+1 < w:         a[y+1, x+1] += err * 3/16
                if y+1 < h:                     a[y+1, x]   += err * 5/16
                if y+1 < h and x-1 >= 0:        a[y+1, x-1] += err * 1/16
    return out

def path_from_dots(dots: np.ndarray) -> str:
    return "".join(f"M{int(x)} {int(y)}h1.8v1.8h-1.8z" for x, y in dots)

def generate(mode: str) -> str:
    t    = THEMES[mode]
    dark = (mode == "dark")
    svg  = []
    w    = svg.append

    print(f"  [{mode}] processing full portrait (removing grid lines & restoring full image) …")
    img_pil = Image.open(os.path.join(ASSETS, "image.png")).convert("RGB")
    
    # 1. Resize full image to 150x170 for portrait box
    img_full = img_pil.resize((150, 170), Image.LANCZOS)
    arr_full = np.array(img_full)

    # 2. Identify red background and red grid line pixels
    bg_red = np.array([238, 36, 38], dtype=float)
    dist_to_red = np.linalg.norm(arr_full.astype(float) - bg_red, axis=2)
    mask_subject = dist_to_red > 45   # True = subject pixel, False = red bg / grid line

    # 3. Inpaint grid line gaps from nearest subject pixels using Euclidean distance transform
    indices = distance_transform_edt(~mask_subject, return_distances=False, return_indices=True)
    arr_inpainted = arr_full[tuple(indices)]

    # 4. Image contrast & unsharp mask on clean inpainted image
    img_clean = Image.fromarray(arr_inpainted)
    img_clean = ImageOps.autocontrast(img_clean, cutoff=1)
    img_clean = ImageEnhance.Contrast(img_clean).enhance(1.4)
    img_clean = img_clean.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    arr_clean = np.array(img_clean)
    gray_clean = np.array(img_clean.convert("L"), dtype=float)

    # 5. Final subject mask
    dist_clean = np.linalg.norm(arr_clean.astype(float) - bg_red, axis=2)
    mask_final = dist_clean > 45
    mask_final = binary_closing(mask_final, iterations=2)
    mask_final = binary_fill_holes(mask_final)

    if dark:
        gray_final = np.where(mask_final, gray_clean, 0.0)
    else:
        gray_final = np.where(mask_final, 255.0 - gray_clean, 0.0)

    # 6. Floyd-Steinberg dithering
    dithered = dither_fs(gray_final)
    rows, cols = np.where(dithered == 255)
    dot_x   = PORTRAIT_CX - 150 + cols * 2
    dot_y   = PORTRAIT_CY - 170 + rows * 2
    all_dots = np.column_stack((dot_x, dot_y))
    print(f"  [{mode}] total portrait dots: {len(all_dots)}")

    # ── Group dots by y-coordinate (scanlines for printing) ────────────────────
    unique_y = np.unique(all_dots[:, 1])
    unique_y.sort()
    
    lines_list = []
    for y_val in unique_y:
        pts_in_row = all_dots[all_dots[:, 1] == y_val]
        lines_list.append((y_val, pts_in_row))
    
    num_lines = len(lines_list)
    print(f"  [{mode}] total scanlines: {num_lines}")

    min_y = float(unique_y.min())
    max_y = float(unique_y.max())

    # ── SVG header ─────────────────────────────────────────────────────────────
    w(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}"'
      f' width="{SVG_W}" height="{SVG_H}"'
      f' role="img" aria-label="Surya Prakash – Cloud &amp; Platform Engineer">')

    w('<style>')
    w(f'.bg{{fill:{t["bg"]}}}')
    w(f'.frm{{stroke:{t["frame"]};stroke-width:1.5;fill:none}}')
    w(f'.bar{{fill:{t["bar"]}}}')
    w(f'.th{{font-family:"Courier New",monospace;font-weight:bold;font-size:14px;fill:{t["header_text"]}}}')
    w(f'.lb{{font-family:"Courier New",monospace;font-size:14px;fill:{t["label"]}}}')
    w(f'.vl{{font-family:"Courier New",monospace;font-size:14px;fill:{t["value"]};font-weight:bold}}')
    w(f'.fl{{font-family:"Courier New",monospace;font-size:11px;fill:{t["label"]}}}')
    w(f'.dl{{stroke:{t["leader"]};stroke-dasharray:2 4;stroke-width:1.5;opacity:.4}}')
    w(f'.cp{{fill:{t["chrome"]}}}')
    w(f'.pt{{font-family:"Courier New",monospace;font-size:12px;fill:{t["pill_text"]};font-weight:bold}}')
    w('@keyframes pulse{0%{opacity:.3}50%{opacity:1}100%{opacity:.3}}')
    w('.live{fill:#EF4444;animation:pulse 2s infinite ease-in-out}')
    w('</style>')

    # ── Background ─────────────────────────────────────────────────────────────
    w(f'<rect width="{SVG_W}" height="{SVG_H}" class="bg" rx="12"/>')

    # ── Terminal chrome ─────────────────────────────────────────────────────────
    w(f'<rect x="5" y="5" width="{SVG_W-10}" height="45" class="bar" rx="8"/>')
    w(f'<rect x="5" y="25" width="{SVG_W-10}" height="25" class="bar"/>')
    w('<circle cx="28" cy="28" r="6" fill="#EF4444"/>')
    w('<circle cx="48" cy="28" r="6" fill="#F59E0B"/>')
    w('<circle cx="68" cy="28" r="6" fill="#10B981"/>')
    w(f'<text x="{SVG_W//2}" y="33" text-anchor="middle" class="th">profile.sh --live</text>')
    w(f'<circle cx="{SVG_W-100}" cy="28" r="5" class="live"/>')
    w(f'<text x="{SVG_W-88}" y="32" class="th" style="font-size:11px;fill:#EF4444">LIVE</text>')
    w(f'<rect x="110" y="16" width="110" height="24" class="cp" rx="4"/>')
    w(f'<text x="165" y="32" text-anchor="middle" class="pt">@Aries-Surya</text>')

    # ── VISUAL.MAP frame ────────────────────────────────────────────────────────
    w(f'<rect x="{LEFT_X}" y="{LEFT_Y}" width="{LEFT_W}" height="{LEFT_H}" class="frm" rx="6"/>')
    w(f'<rect x="{LEFT_X+20}" y="{LEFT_Y-8}" width="90" height="15" class="bg"/>')
    w(f'<text x="{LEFT_X+25}" y="{LEFT_Y+4}" class="fl">VISUAL.MAP</text>')

    # ── Laser Scan Beam ─────────────────────────────────────────────────────────
    scan_y_start = min_y - 10
    scan_y_end   = max_y + 10
    w(f'<line x1="{PORTRAIT_CX-80}" y1="{scan_y_start}" x2="{PORTRAIT_CX+80}" y2="{scan_y_start}"'
      f' stroke="{t["laser"]}" stroke-width="2" opacity="0.95">')
    w(f'  <animate attributeName="y1" values="{scan_y_start};{scan_y_end};{scan_y_end};{scan_y_start}"'
      f' keyTimes="0;0.5833;0.90;1" dur="{PRINT_LOOP_DUR}s" repeatCount="indefinite"/>')
    w(f'  <animate attributeName="y2" values="{scan_y_start};{scan_y_end};{scan_y_end};{scan_y_start}"'
      f' keyTimes="0;0.5833;0.90;1" dur="{PRINT_LOOP_DUR}s" repeatCount="indefinite"/>')
    w(f'  <animate attributeName="opacity" values="0.95;0.95;0;0"'
      f' keyTimes="0;0.5833;0.65;1" dur="{PRINT_LOOP_DUR}s" repeatCount="indefinite"/>')
    w('</line>')

    # ── Line-by-Line Printed Portrait ─────────────────────────────────────────
    w('<g id="portrait-lines">')
    for idx, (y_val, pts) in enumerate(lines_list):
        d_str = path_from_dots(pts)
        row_frac = 0.5833 * (idx / max(num_lines - 1, 1))
        kt_appear = f"{row_frac:.4f}"
        kt_hold   = "0.8333"
        kt_fade   = "0.9500"
        
        w(f'<path d="{d_str}" fill="{t["portrait_col"]}" shape-rendering="crispEdges" opacity="0">')
        w(f'  <animate attributeName="opacity" values="0;0;1;1;0;0"'
          f' keyTimes="0;{kt_appear};{kt_appear};{kt_hold};{kt_fade};1"'
          f' dur="{PRINT_LOOP_DUR}s" repeatCount="indefinite"/>')
        w('</path>')
    w('</g>')

    # ── SYSTEM.INFO frame ───────────────────────────────────────────────────────
    w(f'<rect x="{INFO_X}" y="{INFO_Y}" width="{INFO_W}" height="{INFO_H}" class="frm" rx="6"/>')
    w(f'<rect x="{INFO_X+20}" y="{INFO_Y-8}" width="90" height="15" class="bg"/>')
    w(f'<text x="{INFO_X+25}" y="{INFO_Y+4}" class="fl">SYSTEM.INFO</text>')

    # Info rows
    rows_data = [
        ("Subject",       "Surya Prakash"),
        ("Role",          "Cloud & Platform Engineer @ ZEB"),
        ("Origin",        "Chennai, India"),
        ("Education",     "B.E. Computer Science"),
        ("Status",        "Building + Learning + Shipping"),
        ("ToolChain",     "Terraform, Kubernetes, ArgoCD, Docker"),
        ("Core.Lang",     "Python, C, Java, PowerShell, JS, TS"),
        ("Core.Frontend", "Angular, React, HTML5"),
        ("Core.Backend",  "NodeJS, Django, Flask, FastAPI"),
        ("Core.Database", "MySQL, MongoDB"),
        ("Core.Infra",    "AWS (ECS, EKS, Lambda), Terraform, ArgoCD"),
        ("Grid.Mail",     "suryaprakash.g.official@gmail.com"),
        ("Grid.Portfolio","suryaprakash-portfolio.vercel.app"),
        ("Grid.LinkedIn", "linkedin.com/in/suryaprakash81"),
        ("Grid.GitHub",   "github.com/Aries-Surya"),
    ]

    y_start = INFO_Y + 40
    y_gap   = 23
    x_left  = INFO_X + 20
    x_right = INFO_X + INFO_W - 20

    for i, (label, value) in enumerate(rows_data):
        y = y_start + i * y_gap
        lw = len(label + " ") * 8.4
        vw = len(value) * 8.4
        x_line_start = x_left + lw
        x_line_end   = x_right - vw
        lbl_s = label.replace("&", "&amp;").replace("<", "&lt;")
        val_s = value.replace("&", "&amp;").replace("<", "&lt;")
        w(f'<text x="{x_left}" y="{y}" class="lb">{lbl_s} </text>')
        if x_line_end > x_line_start + 5:
            w(f'<line x1="{x_line_start:.1f}" y1="{y-4}" x2="{x_line_end:.1f}" y2="{y-4}" class="dl"/>')
        w(f'<text x="{x_right}" y="{y}" text-anchor="end" class="vl"'
          f' textLength="{vw:.1f}" lengthAdjust="spacingAndGlyphs">{val_s}</text>')

    # Terminal prompt at bottom
    y_prompt = y_start + len(rows_data) * y_gap + 12
    w(f'<text x="{x_left}" y="{y_prompt}" class="lb"'
      f' style="fill:{t["chrome"]};font-weight:bold">'
      f'aries-surya@terminal:~$'
      f' <tspan style="fill:{t["value"]};font-weight:normal">./contact.sh --live</tspan>'
      f'</text>')

    w('</svg>')
    return "\n".join(svg)

if __name__ == "__main__":
    import sys
    for mode in ("dark", "light"):
        print(f"\nGenerating {mode}.svg (Full Clean Portrait Line-by-Line Print Loop) …")
        content = generate(mode)
        out = os.path.join(ROOT, f"{mode}.svg")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        kb = os.path.getsize(out) / 1024
        print(f"  Wrote {out}  ({kb:.0f} KB)")
    print("\nDone. Full clean portrait banner updated successfully.")
