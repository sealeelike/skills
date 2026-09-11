#!/usr/bin/env python3
"""Convert a handwriting screen-recording video into a causally-exact, zero-aliasing vector SVG animation.

Supports outputting both a standalone preview HTML and a production-ready asynchronous bundle (.js) for zero-blocking web integration.

Usage:
    python3 video_to_svg_anim.py <input_video.mp4> [output.html] [--bundle output-bundle.js] [--fps 24] [--speed 1.8]
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.measure import find_contours

PAD = 24


def rdp(P, eps):
    """Ramer-Douglas-Peucker polygon simplification."""
    keep = [False] * len(P)
    keep[0] = keep[-1] = True
    st = [(0, len(P) - 1)]
    A = np.asarray(P, float)
    while st:
        a, b = st.pop()
        if b <= a + 1:
            continue
        ab = A[b] - A[a]
        L = float(np.hypot(*ab))
        seg = A[a : b + 1] - A[a]
        d = (
            np.abs(seg[:, 0] * ab[1] - seg[:, 1] * ab[0]) / L
            if L
            else np.hypot(seg[:, 0], seg[:, 1])
        )
        i = int(d.argmax())
        if d[i] > eps:
            keep[a + i] = True
            st.append((a, a + i))
            st.append((a + i, b))
    return [p for p, k in zip(P, keep) if k]


def trace(region, eps=0.4):
    """Trace a boolean region into a simplified SVG path."""
    if not region.any():
        return None
    R = np.pad(region.astype(float), 1)
    subs = []
    for c in find_contours(R, 0.5):
        if len(c) < 6:
            continue
        pts = rdp([(float(x) - 1, float(y) - 1) for y, x in c], eps)
        if len(pts) >= 3:
            subs.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
    return " ".join(subs) if subs else None


def extract_ink_mask(img_arr):
    """Extract ink mask using robust chromatic difference (Blue - Red difference for blue ink, or luminance for dark ink)."""
    diff = img_arr[:, :, 2].astype(float) - img_arr[:, :, 0].astype(float)
    if np.max(diff) > 40:
        return diff > 35
    gray = np.dot(img_arr[:, :, :3], [0.299, 0.587, 0.114])
    return gray < 128


def main():
    parser = argparse.ArgumentParser(description="Convert handwriting video to causal animated SVG & web bundle.")
    parser.add_argument("video", help="Path to input video (.mp4/.mov)")
    parser.add_argument("output", nargs="?", default=None, help="Output HTML file path (default: <stem>_anim.html)")
    parser.add_argument("--bundle", default=None, help="Optional output path for production-ready .js bundle")
    parser.add_argument("--fps", type=float, default=24.0, help="Sampling frame rate (default: 24)")
    parser.add_argument("--speed", type=float, default=1.8, help="Default playback speed multiplier (default: 1.8)")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    out_path = (
        Path(args.output).resolve()
        if args.output
        else video_path.with_name(f"{video_path.stem}_anim.html")
    )

    print(f"[*] Processing {video_path.name}...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(video_path),
                "-r",
                str(args.fps),
                str(tmp / "f%04d.png"),
                "-y",
            ],
            check=True,
        )
        files = sorted(tmp.glob("f*.png"))
        T = len(files)
        fps = args.fps

        frames_ink = []
        for p in files:
            arr = np.array(Image.open(p).convert("RGB"))
            frames_ink.append(extract_ink_mask(arr))

    counts = [np.sum(m) for m in frames_ink]
    max_ink = max(counts)
    if max_ink == 0:
        print("Error: No ink detected in video.", file=sys.stderr)
        sys.exit(1)

    start_idx = next(i for i, c in enumerate(counts) if c > max_ink * 0.01)
    end_idx = next(i for i, c in enumerate(reversed(counts)) if c >= max_ink * 0.99)
    end_idx = T - 1 - end_idx

    frames_ink = frames_ink[start_idx : end_idx + 1]
    T = len(frames_ink)

    final = frames_ink[-1]
    first = np.full(final.shape, T, dtype=np.int16)
    for i, ink in enumerate(frames_ink):
        first[ink & (first == T)] = i

    ys, xs = np.nonzero(final)
    y0, y1 = max(0, ys.min() - PAD), min(final.shape[0], ys.max() + PAD)
    x0, x1 = max(0, xs.min() - PAD), min(final.shape[1], xs.max() + PAD)

    mask = final[y0:y1, x0:x1]
    tmap = first[y0:y1, x0:x1]
    Hh, Ww = mask.shape
    print(f"[*] Canvas: {Ww}x{Hh}, {T} frames active ({T/fps:.2f}s)")

    # Potrace ultra-smooth cubic Bézier finish
    with tempfile.TemporaryDirectory() as pbm_tmp:
        pbm_path = Path(pbm_tmp) / "final.pbm"
        svg_path = Path(pbm_tmp) / "final.svg"
        pbm_data = np.ones((Hh, Ww), dtype=np.uint8) * 255
        pbm_data[mask] = 0
        Image.fromarray(pbm_data, mode="L").convert("1").save(pbm_path)
        subprocess.run(
            [
                "potrace",
                "-s",
                "-o",
                str(svg_path),
                "-a",
                "1.3",
                "-t",
                "1",
                "-O",
                "0.2",
                str(pbm_path),
            ],
            check=True,
        )
        svg_txt = svg_path.read_text()

    match = re.search(
        r'<g transform="translate\(0\.000000,(\d+)\.000000\) scale\(0\.100000,-0\.100000\)"[^>]*>(.*?)</g>',
        svg_txt,
        re.DOTALL,
    )
    Hh_val = int(match.group(1))
    full_bezier_paths = match.group(2)

    regions = []
    for k in range(T):
        d = trace(tmap == k, 0.4)
        if d:
            regions.append({"t": round(k / fps, 3), "d": d})

    print(f"[*] Generated {len(regions)} causal reveal regions")

    reveal_tags = "\n        ".join(
        f'<path id="f{i}" d="{r["d"]}"/>' for i, r in enumerate(regions)
    )
    timestamps = [r["t"] for r in regions]
    DUR = T / fps
    title = video_path.stem

    # Pure SVG component markup
    svg_markup = f"""<svg viewBox="0 0 {Ww} {Hh}" role="img" aria-label="{title} Signature">
  <defs>
    <mask id="penMask" maskUnits="userSpaceOnUse" x="0" y="0" width="{Ww}" height="{Hh}">
      <g id="reveal">
        {reveal_tags}
      </g>
    </mask>
  </defs>
  <g mask="url(#penMask)">
    <g transform="translate(0,{Hh_val}) scale(0.1,-0.1)" class="ink-bezier">
      {full_bezier_paths}
    </g>
  </g>
</svg>"""

    # 1. Output standalone preview HTML
    html = f"""<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>{title} — Causal Vector Signature</title>
  <style>
    body {{
      background: #2e3d49;
      color: #edf0ed;
      font-family: system-ui, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 2rem;
      box-sizing: border-box;
    }}
    .card {{
      background: rgba(53, 74, 85, 0.4);
      border: 1px solid #495b64;
      border-radius: 12px;
      padding: 2.5rem 3rem;
      max-width: 960px;
      width: 100%;
      text-align: center;
    }}
    .stage {{
      width: 100%;
      max-width: 820px;
      margin: 2rem auto;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
      shape-rendering: geometricPrecision;
      text-rendering: geometricPrecision;
    }}
    .ink-bezier {{
      fill: #edf0ed;
      shape-rendering: geometricPrecision;
    }}
    #reveal path {{
      fill: #fff;
      stroke: #fff;
      stroke-width: 2.5px;
      stroke-linejoin: round;
      stroke-linecap: round;
      shape-rendering: geometricPrecision;
    }}
    .controls {{
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin-top: 1.5rem;
    }}
    button {{
      background: #354a55;
      border: 1px solid #495b64;
      color: #edf0ed;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 150ms ease;
    }}
    button:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: #c7ddd6;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size: 0.85rem; color: #b7c0c3; margin-bottom: 0.5rem; letter-spacing: 0.05em; text-transform: uppercase;">
      Causal Vector Signature ({title})
    </div>

    <div class="stage">
      {svg_markup}
    </div>

    <div style="font-size: 0.9rem; color: #b7c0c3;" id="timerLab">0.00s</div>

    <div class="controls">
      <button id="btn1" onclick="play(1.0)">原速播放 (1.0x)</button>
      <button id="btn2" onclick="play({args.speed})">利落速度 ({args.speed}x)</button>
      <button id="btn3" onclick="showAll()">显示最终真迹</button>
    </div>
  </div>

  <script>
    const TS = {json.dumps(timestamps)};
    const N = TS.length;
    const DUR = {DUR:.3f} * 1000;
    const els = TS.map((_, i) => document.getElementById('f' + i));
    let speed = {args.speed};
    let playing = false;
    let raf = 0;
    let shown = -1;
    const lab = document.getElementById('timerLab');

    function at(ms) {{
      const t = ms / 1000;
      let k = -1;
      while (k + 1 < N && TS[k + 1] <= t) k++;
      if (k !== shown) {{
        const lo = Math.min(shown, k) + 1;
        const hi = Math.max(shown, k);
        for (let i = lo; i <= hi; i++) els[i].style.display = i <= k ? '' : 'none';
        shown = k;
      }}
      lab.textContent = Math.max(0, Math.min(t, DUR / 1000)).toFixed(2) + 's';
    }}

    function reset() {{
      for (let i = 0; i < N; i++) els[i].style.display = 'none';
      shown = -1;
    }}

    function play(s = {args.speed}) {{
      cancelAnimationFrame(raf);
      reset();
      speed = s;
      playing = true;
      const t0 = performance.now();
      (function step(now) {{
        if (!playing) return;
        const ms = (now - t0) * speed;
        at(ms);
        if (ms < DUR) {{
          raf = requestAnimationFrame(step);
        }} else {{
          playing = false;
          at(DUR);
          lab.textContent = '书写完毕，终态完美定格！';
        }}
      }})(performance.now());
    }}

    function showAll() {{
      cancelAnimationFrame(raf);
      playing = false;
      for (let i = 0; i < N; i++) els[i].style.display = '';
      shown = N - 1;
      lab.textContent = '已显示最终真迹';
    }}

    setTimeout(() => play({args.speed}), 300);
  </script>
</body>
</html>"""

    out_path.write_text(html)
    print(f"[✓] Generated preview HTML: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")

    # 2. Output production .js bundle if requested
    bundle_target = Path(args.bundle) if args.bundle else video_path.with_name(f"{video_path.stem}-signature-bundle.js")
    bundle_js = f"""// Independent Signature Animation Component (Lazy-loadable & Auto-hydrating)
(function() {{
  const svgMarkup = {json.dumps(svg_markup)};
  const timestamps = {json.dumps(timestamps)};

  window.initSignatureHero = function(targetSelector, options = {{}}) {{
    const container = document.querySelector(targetSelector || '#signature-hero');
    if (!container) return;

    container.innerHTML = svgMarkup;
    const N = timestamps.length;
    const dur = (timestamps[N - 1] || 10) * 1000;
    const speed = options.speed || {args.speed};
    const els = timestamps.map((_, i) => document.getElementById('f' + i));

    els.forEach(el => {{ if (el) el.style.display = 'none'; }});

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {{
      els.forEach(el => {{ if (el) el.style.display = ''; }});
      return;
    }}

    let shown = -1;
    function at(ms) {{
      const t = ms / 1000;
      let k = -1;
      while (k + 1 < N && timestamps[k + 1] <= t) k++;
      if (k !== shown) {{
        const lo = Math.min(shown, k) + 1;
        const hi = Math.max(shown, k);
        for (let i = lo; i <= hi; i++) {{
          if (els[i]) els[i].style.display = i <= k ? '' : 'none';
        }}
        shown = k;
      }}
    }}

    setTimeout(() => {{
      const t0 = performance.now();
      function step(now) {{
        const ms = (now - t0) * speed;
        at(ms);
        if (ms < dur) {{
          requestAnimationFrame(step);
        }} else {{
          els.forEach(el => {{ if (el) el.style.display = ''; }});
        }}
      }}
      requestAnimationFrame(step);
    }}, options.delay || 120);
  }};

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => window.initSignatureHero());
  }} else {{
    window.initSignatureHero();
  }}
}})();
"""
    bundle_target.write_text(bundle_js)
    print(f"[✓] Generated production bundle: {bundle_target} ({bundle_target.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
