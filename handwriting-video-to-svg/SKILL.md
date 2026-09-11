---
name: handwriting-video-to-svg
description: Convert iPad/tablet handwriting screen recordings (GoodNotes, Notability, Procreate, Apple Notes) into causally-exact, zero-aliasing, infinite-resolution vector SVG handwriting animations. Use whenever the user provides a handwriting screen recording video and wants to turn it into an authentic stroke-by-stroke website signature, title, or lettering animation.
---

# Handwriting Video to Causal Vector SVG Skill

Transform digital handwriting screen recordings into lightweight, frame-exact, infinitely sharp vector animations that reveal strokes according to true temporal physics—guaranteeing **zero premature ink spillover, zero broken slices, and zero anti-aliasing pixelation**.

## 1. Core Principles & The "Fat Stroke" Fallacy

Standard tutorials simulate handwriting by drawing a center-path skeleton and masking it with a thick `stroke-dashoffset` line. **This always fails on cursive and crossing script**:
- A thick stroke travelling along stroke A inevitably bleeds sideways into intersecting stroke B before the pen arrives, causing "shattered/sliced" artifacts.
- Hard thresholding produces ugly raster pixel staircases ("jaggies").

### The Causal Region Reveal Architecture
This skill uses **Physical Causality Extraction + Potrace Cubic Bézier Finish**:
1. **First Arrival Timestamps**: Records the exact frame $t$ each pixel turns into ink.
2. **Per-Frame Region Reveal**: The mask reveals only ink that physically existed at timestamp $t$. Premature ink is mathematically impossible (0.0% error).
3. **Cubic Bézier Finish**: Vectorizes the final lettering using `potrace` high-order Bézier fitting (`-a 1.3 -O 0.2`) with `shape-rendering: geometricPrecision`.

## 2. Dependencies & Toolchain

Ensure the following tools are installed on the host:
- System: `ffmpeg`, `potrace`
- Python: `numpy`, `pillow`, `scikit-image`

```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg potrace
pip install numpy pillow scikit-image
```

## 3. Automation Script Execution

The complete end-to-end converter script is stored at:
`<skill_dir>/scripts/video_to_svg_anim.py`

### Basic Usage
```bash
python3 <skill_dir>/scripts/video_to_svg_anim.py <input_video.mp4> [output.html] [--bundle output-bundle.js] [--fps 24] [--speed 1.8]
```

### Generated Artifacts
1. **`[output.html]`**: A self-contained preview page with interactive controls (speed switches, final state preview).
2. **`[output-bundle.js]`** (via `--bundle`): A production-ready, zero-dependency, asynchronous web bundle that auto-hydrates into `#signature-hero`.

## 4. How to Embed into Web Frontends (Zero-Blocking CDN / Asset Pattern)

To keep the web page lightweight and avoid polluting the main bundle, follow this 3-step embedding architecture:

### Step 1: HTML Placeholder Container
Place a semantic heading with a fixed aspect-ratio container in your HTML:
```html
<h1 class="home-name" aria-label="Author Signature">
  <div class="home-signature-wrap" id="signature-hero"></div>
</h1>
```

### Step 2: Minimal Layout CSS
Ensure layout stability (prevent Layout Shift / CLS) by setting the natural aspect ratio matching the canvas bounding box:
```css
.home-signature-wrap {
  width: 100%;
  max-width: 20rem; /* Adjust width to balance layout */
  aspect-ratio: 1313 / 647; /* Set to the generated Ww / Hh */
  display: block;
}

.home-signature-wrap svg {
  width: 100%;
  height: 100%;
  display: block;
  shape-rendering: geometricPrecision;
  text-rendering: geometricPrecision;
}

/* Inherits the website theme color */
.home-signature-wrap .ink-bezier {
  fill: var(--fg);
}
```

### Step 3: Asynchronous Defer Script
Load the generated bundle via `<script defer>` before `</body>`:
```html
<script src="/assets/signature-bundle.js" defer></script>
```
- **Zero Blocking**: The initial HTML and CSS paint instantly (0ms TTFB).
- **Auto-Hydration**: As soon as the bundle finishes downloading, it injects into `#signature-hero` and starts the smooth writing reveal, automatically falling back to static final state if `prefers-reduced-motion` is enabled.
