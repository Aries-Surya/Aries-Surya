---
name: github-profile-generator
description: Comprehensive skill for creating, generating, and maintaining theme-aware animated dithered banners, line-by-line matrix scanline SVG animations, grid-free image processing, multi-branch GitHub Actions workflows, and profile README assets.
---

# GitHub Profile Generator & Banner Automation Skill

This skill documents the end-to-end architecture, image processing algorithms, SVG SMIL animation pipelines, GitHub Actions workflows, and maintenance procedures for the **Surya Prakash** (`@Aries-Surya`) GitHub Profile README repository.

---

## 🏗️ Architecture Overview

```
Aries-Surya/
├── .github/
│   ├── scripts/
│   │   ├── generate_banner.py    # Python: Full clean Floyd-Steinberg dithered line-by-line banner generator
│   │   ├── generate.mjs          # Node.js: 3D Contribution Jet Heatmap SVG generator
│   │   ├── fetch_data.py         # Python: GitHub API live repo/star stats retriever
│   │   └── generate_projects.py  # Python: Dynamic projects panel SVG generator
│   └── workflows/
│       ├── banner.yml            # Actions: Regenerates dark.svg/light.svg weekly
│       ├── jet-heatmap.yml       # Actions: Updates dist/github-jet.svg daily
│       ├── projects.yml          # Actions: Updates projects branch projects.svg every 6h
│       └── snake.yml             # Actions: Updates output branch contribution snake every 12h
├── assets/
│   └── image.png                 # Source portrait photo
├── dark.svg                      # Dark mode theme-aware animated banner (<300 KB)
├── light.svg                     # Light mode theme-aware animated banner (<300 KB)
└── README.md                     # Profile README featuring all animated components
```

---

## 🎨 Component 1: Dithered Banner Generator (`generate_banner.py`)

### 1. Image Pre-processing & Morphological Grid Filtering
Raw input images or contact sheets may contain baked-in grid lines or lattice artifacts. To produce a seamless portrait:
- **`grey_closing(gray, size=(3, 3))`**: Morphological closing (dilation followed by erosion) eliminates fine dark grid/graph-paper lines.
- **`median_filter(closed_gray, size=3)`**: Smooths out high-frequency noise while preserving sharp facial edges.
- **`ImageOps.autocontrast` & `UnsharpMask`**: Sharpens subject boundaries before dithering.

### 2. Floyd-Steinberg Dithering (Serpentine Scan)
Converts grayscale pixel arrays to binary dot matrices (`0` or `255`) using error diffusion in alternating scan directions:
$$\text{err} = \text{old\_val} - \text{new\_val}$$
Error is distributed to right ($\frac{7}{16}$), bottom-left ($\frac{3}{16}$), bottom ($\frac{5}{16}$), and bottom-right ($\frac{1}{16}$).

### 3. Matrix Line-by-Line Scanline Print Animation (Pure SVG SMIL)
- **Laser Beam**: A glowing line (`stroke-width="2"`) slides down from `min_y` to `max_y` over 3.5 seconds.
- **Line-by-Line Printing**: Dots are grouped by unique `y` coordinate (scanlines). Each scanline reveals opacity `0 → 1` as the laser passes it, holds full opacity for 1.5s, then smoothly resets in a continuous 6.0s loop.
- **Zero Third-Party Logos**: Clean focus on the candidate's portrait and `SYSTEM.INFO` terminal stats.

---

## ⚙️ Component 2: GitHub Actions Workflows

All automated workflows run headless on GitHub's `ubuntu-latest` runners:

### 1. Banner Generation (`.github/workflows/banner.yml`)
- **Triggers**: Schedule (Weekly Sunday), manual `workflow_dispatch`, or push to `generate_banner.py`.
- **Dependencies**: `pip install pillow numpy scipy`.
- **Action**: Runs `python .github/scripts/generate_banner.py` and auto-commits updated `dark.svg`/`light.svg`.

### 2. Jet Heatmap (`.github/workflows/jet-heatmap.yml`)
- **Triggers**: Daily cron at 05:30 UTC or manual run.
- **Action**: Runs `node .github/scripts/generate.mjs`, producing `dist/github-jet.svg`.

### 3. Contribution Snake (`.github/workflows/snake.yml`)
- **Action**: Uses `Platane/snk/svg-only@v3` and pushes to `output` branch as `snake-dark.svg` and `snake-light.svg`.

### 4. Projects Panel (`.github/workflows/projects.yml`)
- **Action**: Runs `fetch_data.py` & `generate_projects.py`, pushing output to `projects` branch as `projects.svg`.

---

## 📊 Component 3: Live Stats & Badges Standards

### High-Availability Stats Server
Default public instances (`github-readme-stats.vercel.app`) frequently hit rate limits (HTTP 503). This setup uses the high-availability dedicated endpoint:
- **Stats Card**: `https://github-readme-stats-sigma-rosy-28.vercel.app/api?username=Aries-Surya&...`
- **Top Languages**: `https://github-readme-stats-sigma-rosy-28.vercel.app/api/top-langs/?username=Aries-Surya&...`

### Horizontal Single-Line Social Badges
To prevent GitHub's markdown parser from wrapping badges onto vertical single lines, all badge links are placed on a single continuous HTML line inside `<p align="center">`:
```html
<p align="center">
  <a href="https://www.linkedin.com/in/suryaprakash81/"><img src="https://img.shields.io/badge/LinkedIn-0A101F?style=for-the-badge&logoColor=white&labelColor=0A101F&logo=linkedin" alt="LinkedIn" /></a>&nbsp;
  <a href="https://suryaprakash-portfolio.vercel.app/"><img src="https://img.shields.io/badge/Portfolio-0A101F?style=for-the-badge&logo=About.me&logoColor=22D3EE&labelColor=0A101F" alt="Portfolio" /></a>&nbsp;
  <a href="mailto:suryaprakash.g.official@gmail.com"><img src="https://img.shields.io/badge/Email-0A101F?style=for-the-badge&logo=gmail&logoColor=EF4444&labelColor=0A101F" alt="Email" /></a>&nbsp;
  <a href="https://x.com/aries_surya_"><img src="https://img.shields.io/badge/X-0A101F?style=for-the-badge&logo=x&logoColor=F8FAFC&labelColor=0A101F" alt="X" /></a>&nbsp;
  <a href="https://instagram.com/aries_surya_"><img src="https://img.shields.io/badge/Instagram-0A101F?style=for-the-badge&logo=instagram&logoColor=A78BFA&labelColor=0A101F" alt="Instagram" /></a>&nbsp;
  <a href="https://www.youtube.com/@SuryaInformative"><img src="https://img.shields.io/badge/YouTube-0A101F?style=for-the-badge&logo=youtube&logoColor=22D3EE&labelColor=0A101F" alt="YouTube" /></a>&nbsp;
  <a href="https://medium.com/@ariessurya8124"><img src="https://img.shields.io/badge/Medium-0A101F?style=for-the-badge&logo=medium&logoColor=F8FAFC&labelColor=0A101F" alt="Medium" /></a>&nbsp;
  <a href="https://discord.gg/RnxVTPs2"><img src="https://img.shields.io/badge/Discord-0A101F?style=for-the-badge&logo=discord&logoColor=5865F2&labelColor=0A101F" alt="Discord" /></a>
</p>
```

---

## 🔧 Maintenance & Execution Commands

### Regenerate Banners Locally:
```bash
python .github/scripts/generate_banner.py
```

### Manually Trigger Workflow via Git:
```bash
git add .
git commit -m "chore: trigger asset refresh"
git push origin main
```
