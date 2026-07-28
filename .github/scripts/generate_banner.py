#!/usr/bin/env python3
"""
GitHub Profile Banner Generator — implements the Phase 1 spec exactly.

Design (per GitHub-Profile-Master-Prompt.MD):
  - Left panel (380×485): Floyd-Steinberg dithered portrait, ~17k dots
      Dark:  background segmented out → dots draw lit subject on dark bg
      Light: background kept          → dots draw dark parts on light bg
  - Two-layer animation:
      Layer 1 (intro, once, ~3.2s): ~60 interleaved random groups shimmer in
      Layer 2 (loop, 14.2s): ~94 drift bands dissolve → 900 traveller dots
        morph Python → Docker → Git via optimal transport (Hungarian algorithm)
  - Right panel (680×485): SYSTEM.INFO rows with dotted leaders + textLength lock
  - Terminal chrome: title bar, window buttons, handle pill, LIVE badge

Usage:
    python .github/scripts/generate_banner.py

Outputs: dark.svg and light.svg in the repository root (~900KB–1MB each).
"""

import os, math, random
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from scipy.cluster.vq import kmeans
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment

random.seed(42)
np.random.seed(42)

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
        "traveller":    "#10B981",
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
        "traveller":    "#0891B2",
        "pill_text":    "#FFFFFF",
    },
}

# ── Layout constants ───────────────────────────────────────────────────────────
SVG_W, SVG_H  = 1180, 610
LEFT_X, LEFT_Y, LEFT_W, LEFT_H = 40, 85, 380, 485
INFO_X, INFO_Y, INFO_W, INFO_H = 460, 85, 680, 485
PORTRAIT_CX, PORTRAIT_CY       = 230, 305   # center of left panel

NUM_INTRO_GROUPS  = 60
NUM_DRIFT_BANDS   = 94
NUM_TRAVELLERS    = 900

# Animation timing (seconds)
INTRO_DUR   = 3.2   # intro plays once then stops
LOOP_DUR    = 14.2  # total loop
# Keyframe fractions within the 14.2s loop:
# portrait visible:  0.00 → 0.01 (fade in) → 0.2113 (start drift) → 0.3028 (gone)
# logos visible:     0.3028 → 0.9085
# return:            0.9085 → 1.00
KF = {
    "p_fadein":  0.01,
    "p_start":   round(3.0  / LOOP_DUR, 4),   # 0.2113
    "p_gone":    round(4.3  / LOOP_DUR, 4),   # 0.3028
    "l12_start": round(6.3  / LOOP_DUR, 4),   # 0.4437
    "l12_end":   round(7.6  / LOOP_DUR, 4),   # 0.5352
    "l23_start": round(9.6  / LOOP_DUR, 4),   # 0.6761
    "l23_end":   round(10.9 / LOOP_DUR, 4),   # 0.7676
    "t_return":  round(12.9 / LOOP_DUR, 4),   # 0.9085
}

# ── Floyd-Steinberg dithering (serpentine) ─────────────────────────────────────
def dither_fs(arr_float: np.ndarray) -> np.ndarray:
    """In-place Floyd-Steinberg with serpentine scan. Returns binary uint8."""
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

# ── Background segmentation (dark mode) ───────────────────────────────────────
def segment_subject_dark(img_rgb: np.ndarray) -> np.ndarray:
    """
    Threshold on colour distance to the reddish studio background,
    then binary-close + fill holes + keep largest component.
    Returns a boolean mask: True = subject pixel.
    """
    from scipy.ndimage import binary_closing, binary_fill_holes, label
    bg_col = np.array([238, 36, 42], dtype=float)
    dist   = np.linalg.norm(img_rgb.astype(float) - bg_col, axis=2)
    mask   = dist > 55
    mask   = binary_closing(mask, iterations=4)
    mask   = binary_fill_holes(mask)
    lbl, n = label(mask)
    if n == 0:
        return mask
    sizes  = [(lbl == i).sum() for i in range(1, n+1)]
    return lbl == (np.argmax(sizes) + 1)

# ── Logo point extraction via K-means ─────────────────────────────────────────
def logo_points(path: str, n: int = NUM_TRAVELLERS) -> np.ndarray:
    """
    Load logo, extract foreground pixels, scale to [-110,110] box,
    K-means to exactly n centroids, centred at (0,0).
    """
    img  = Image.open(path).convert("RGBA")
    arr  = np.array(img)
    alpha = arr[:, :, 3]
    pts  = np.argwhere(alpha > 50)[:, [1, 0]].astype(float)  # (x, y)
    if len(pts) < 10:
        # fallback: use dark pixels from grayscale
        gray = np.array(img.convert("L"))
        pts  = np.argwhere(gray < 200)[:, [1, 0]].astype(float)
    xmin, ymin = pts.min(0);  xmax, ymax = pts.max(0)
    scale = 220.0 / max(xmax-xmin, ymax-ymin, 1)
    pts   = (pts - [(xmin+xmax)/2, (ymin+ymax)/2]) * scale
    if len(pts) > 4000:
        idx  = np.random.choice(len(pts), 4000, replace=False)
        pts  = pts[idx]
    centroids, _ = kmeans(pts, n)
    # pad / trim to exactly n
    if len(centroids) < n:
        diff = n - len(centroids)
        idx  = np.random.choice(len(centroids), diff)
        centroids = np.vstack([centroids, centroids[idx] + np.random.normal(0, 0.5, (diff, 2))])
    return centroids[:n]

# ── Optimal transport matching ─────────────────────────────────────────────────
def match(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Return dst reordered so that src[i] ↔ dst[return[i]] minimises total distance."""
    _, col = linear_sum_assignment(cdist(src, dst))
    return dst[col]

# ── SVG helpers ────────────────────────────────────────────────────────────────
def path_from_dots(dots: np.ndarray) -> str:
    return "".join(f"M{int(x)} {int(y)}h1v1h-1z" for x, y in dots)

def kt(frac: float) -> str:
    return f"{frac:.4f}"

# ── Main generator ─────────────────────────────────────────────────────────────
def generate(mode: str) -> str:
    t    = THEMES[mode]
    dark = (mode == "dark")
    svg  = []
    w    = svg.append

    # ── Portrait processing ────────────────────────────────────────────────────
    print(f"  [{mode}] processing portrait …")
    img_pil = Image.open(os.path.join(ASSETS, "image.png"))
    iw, ih  = img_pil.size
    
    # If input is a 5x5 AI contact sheet (e.g. 1536x1536), extract single portrait tile (row 1, col 2)
    if iw >= 1000 and ih >= 1000:
        tw, th = iw // 5, ih // 5
        img_pil = img_pil.crop((2*tw, 1*th, 3*tw, 2*th))
        iw, ih  = img_pil.size

    # Head + shoulders crop & resize to 150x170
    box     = (int(iw*0.05), int(ih*0.02), int(iw*0.95), int(ih*0.95))
    img_rgb = img_pil.crop(box).resize((150, 170), Image.LANCZOS).convert("RGB")
    img_rgb = ImageOps.autocontrast(img_rgb, cutoff=1)
    img_rgb = ImageEnhance.Contrast(img_rgb).enhance(1.4)
    img_rgb = img_rgb.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    arr_rgb = np.array(img_rgb)
    gray    = np.array(img_rgb.convert("L"), dtype=float)

    if dark:
        mask       = segment_subject_dark(arr_rgb)
        gray_final = np.where(mask, gray, 0.0)
    else:
        gray_final = 255.0 - gray   # light bg: draw dark parts

    dithered = dither_fs(gray_final)
    rows, cols = np.where(dithered == 255)
    # Map to SVG space (portrait centred at PORTRAIT_CX, PORTRAIT_CY)
    dot_x   = PORTRAIT_CX - 150 + cols * 2
    dot_y   = PORTRAIT_CY - 170 + rows * 2
    all_dots = np.column_stack((dot_x, dot_y))
    print(f"  [{mode}] portrait dots: {len(all_dots)}")

    # ── Logo traveller points ──────────────────────────────────────────────────
    print(f"  [{mode}] extracting logo points …")
    p1 = logo_points(os.path.join(ASSETS, "logo_python.png"))
    p2 = logo_points(os.path.join(ASSETS, "logo_docker.png"))
    p3 = logo_points(os.path.join(ASSETS, "logo_git.png"))
    p2 = match(p1, p2)
    p3 = match(p2, p3)
    # Translate to SVG space (centred at PORTRAIT_CX, PORTRAIT_CY)
    t1 = p1 + [PORTRAIT_CX, PORTRAIT_CY]
    t2 = p2 + [PORTRAIT_CX, PORTRAIT_CY]
    t3 = p3 + [PORTRAIT_CX, PORTRAIT_CY]

    # ── Intro groups: interleaved indexing for uniform spatial scatter ──────
    # Instead of np.array_split (sequential = spatchy regions),
    # assign dot i to group (i % NUM_INTRO_GROUPS) so every group
    # contains dots evenly distributed across the whole portrait.
    np.random.shuffle(all_dots)          # randomise order first
    intro_groups = [all_dots[i::NUM_INTRO_GROUPS] for i in range(NUM_INTRO_GROUPS)]

    # Evenness metric: std of per-cell dot counts / mean (lower = more uniform)
    grid = np.zeros((6, 10), dtype=int)
    for d in all_dots:
        gx = min(int((d[0] - LEFT_X) / LEFT_W * 10), 9)
        gy = min(int((d[1] - LEFT_Y) / LEFT_H * 6), 5)
        if 0 <= gx < 10 and 0 <= gy < 6:
            grid[gy, gx] += 1
    counts = grid.flatten(); mean = counts.mean() or 1
    evenness = counts.std() / mean
    print(f"  [{mode}] intro evenness metric: {evenness:.3f} (good < 0.10)")
    if evenness > 0.15:
        print(f"  [{mode}] WARNING: evenness {evenness:.3f} > 0.15 — dots may appear patchy")

    # ── Drift bands: per-dot noise BEFORE sort (spec: sigma ~4) ─────────────
    # Per-dot noise before sorting ensures the sort key is organic,
    # preventing the mathematical recreation of a square grid (the grid trap).
    noise_keys  = all_dots[:, 1] + np.random.normal(0, 4.0, len(all_dots))
    sort_idx    = np.argsort(noise_keys)
    sorted_dots = all_dots[sort_idx]

    # Straight-boundary metric: measure y-homogeneity within each band.
    # A grid would have bands with very small y-spread (all same row).
    # Organic bands have large y-spread. We want mean_y_std / overall_y_std > 0.8.
    band_arr   = np.array_split(sorted_dots, NUM_DRIFT_BANDS)
    y_stds     = [b[:, 1].std() for b in band_arr if len(b) > 1]
    overall_y  = sorted_dots[:, 1].std() or 1
    straight_m = 1.0 - (np.mean(y_stds) / overall_y)
    print(f"  [{mode}] straight-boundary metric: {straight_m:.3f} (organic < 0.10)")
    if straight_m > 0.15:
        print(f"  [{mode}] WARNING: metric {straight_m:.3f} > 0.15 — bands may look blocky")

    target_c = np.array([float(PORTRAIT_CX), float(PORTRAIT_CY)])
    bands    = []
    for band in band_arr:
        centroid = band.mean(axis=0)
        dx = 0.42 * (target_c[0] - centroid[0])
        dy = 0.42 * (target_c[1] - centroid[1])
        bands.append((path_from_dots(band), dx, dy))

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

    # ── Layer 1: Intro portrait (60 groups, shimmer in once over 3.2s) ─────────
    w('<g id="intro">')
    for i, grp in enumerate(intro_groups):
        d    = path_from_dots(grp)
        t_in = (i / NUM_INTRO_GROUPS) * 2.0   # staggered 0→2s
        # values: invisible → invisible → solid → solid → gone
        # keyTimes mapped to 3.2s total
        kt0  = 0
        kt1  = f"{t_in / INTRO_DUR:.4f}"
        kt2  = f"{min((t_in + 0.6) / INTRO_DUR, 0.999):.4f}"
        kt3  = "0.9375"  # 3.0/3.2
        kt4  = "1"
        w(f'<path d="{d}" fill="{t["portrait_col"]}" shape-rendering="crispEdges" opacity="0">')
        w(f'<animate attributeName="opacity" values="0;0;1;1;0"'
          f' keyTimes="{kt0};{kt1};{kt2};{kt3};{kt4}"'
          f' dur="{INTRO_DUR}s" fill="freeze"/>')
        w('</path>')
    w('</g>')

    # ── Layer 2: Loop portrait (94 drift bands, loop 14.2s, begins after intro) ─
    w('<g id="loop-portrait">')
    for d_str, dx, dy in bands:
        w(f'<path d="{d_str}" fill="{t["portrait_col"]}" shape-rendering="crispEdges" opacity="0">')
        w(f'<animate attributeName="opacity"'
          f' values="0;1;1;0;0;0;1"'
          f' keyTimes="0;{kt(KF["p_fadein"])};{kt(KF["p_start"])};{kt(KF["p_gone"])};{kt(KF["t_return"])};0.91;1"'
          f' dur="{LOOP_DUR}s" begin="{INTRO_DUR}s" repeatCount="indefinite"/>')
        w(f'<animateTransform attributeName="transform" type="translate"'
          f' values="0,0;0,0;0,0;{dx:.1f},{dy:.1f};{dx:.1f},{dy:.1f};0,0"'
          f' keyTimes="0;{kt(KF["p_fadein"])};{kt(KF["p_start"])};{kt(KF["p_gone"])};{kt(KF["t_return"])};1"'
          f' dur="{LOOP_DUR}s" begin="{INTRO_DUR}s" repeatCount="indefinite"/>')
        w('</path>')
    w('</g>')

    # ── Travellers (900 dots morphing between logos) ───────────────────────────
    w('<g id="travellers">')
    for i in range(NUM_TRAVELLERS):
        x1, y1 = t1[i];  x2, y2 = t2[i];  x3, y3 = t3[i]
        # opacity: hidden during portrait phase, visible during logo phases
        op_vals  = "0;0;0;1;1;1;1;1;0"
        op_kt    = f"0;{kt(KF['p_fadein'])};{kt(KF['p_start'])};{kt(KF['p_gone'])};{kt(KF['l12_start'])};{kt(KF['l12_end'])};{kt(KF['l23_start'])};{kt(KF['t_return'])};1"
        cx_vals  = f"{x1:.1f};{x1:.1f};{x1:.1f};{x1:.1f};{x2:.1f};{x2:.1f};{x3:.1f};{x3:.1f};{x1:.1f}"
        cy_vals  = f"{y1:.1f};{y1:.1f};{y1:.1f};{y1:.1f};{y2:.1f};{y2:.1f};{y3:.1f};{y3:.1f};{y1:.1f}"
        w(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="1.3" fill="{t["traveller"]}" opacity="0">')
        w(f'<animate attributeName="opacity" values="{op_vals}" keyTimes="{op_kt}"'
          f' dur="{LOOP_DUR}s" begin="{INTRO_DUR}s" repeatCount="indefinite"/>')
        w(f'<animate attributeName="cx" values="{cx_vals}" keyTimes="{op_kt}"'
          f' dur="{LOOP_DUR}s" begin="{INTRO_DUR}s" repeatCount="indefinite"/>')
        w(f'<animate attributeName="cy" values="{cy_vals}" keyTimes="{op_kt}"'
          f' dur="{LOOP_DUR}s" begin="{INTRO_DUR}s" repeatCount="indefinite"/>')
        w('</circle>')
    w('</g>')

    # ── SYSTEM.INFO frame ───────────────────────────────────────────────────────
    w(f'<rect x="{INFO_X}" y="{INFO_Y}" width="{INFO_W}" height="{INFO_H}" class="frm" rx="6"/>')
    w(f'<rect x="{INFO_X+20}" y="{INFO_Y-8}" width="90" height="15" class="bg"/>')
    w(f'<text x="{INFO_X+25}" y="{INFO_Y+4}" class="fl">SYSTEM.INFO</text>')

    # Info rows — exact spec rows
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
        # HTML-escape special chars
        lbl_s = label.replace("&", "&amp;").replace("<", "&lt;")
        val_s = value.replace("&", "&amp;").replace("<", "&lt;")
        w(f'<text x="{x_left}" y="{y}" class="lb">{lbl_s} </text>')
        if x_line_end > x_line_start + 5:
            w(f'<line x1="{x_line_start:.1f}" y1="{y-4}" x2="{x_line_end:.1f}" y2="{y-4}" class="dl"/>')
        # textLength locks right-alignment in any browser
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


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    for mode in ("dark", "light"):
        print(f"\nGenerating {mode}.svg …")
        try:
            content = generate(mode)
            out = os.path.join(ROOT, f"{mode}.svg")
            with open(out, "w", encoding="utf-8") as f:
                f.write(content)
            kb = os.path.getsize(out) / 1024
            print(f"  Wrote {out}  ({kb:.0f} KB)")
            if kb < 100:
                print(f"  WARNING: {kb:.0f} KB seems small — check portrait dot count")
            if kb > 1500:
                print(f"  WARNING: {kb:.0f} KB is very large — may exceed GitHub render limit")
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            raise
    print("\nDone. Open dark.svg and light.svg in a browser to verify animations.")
