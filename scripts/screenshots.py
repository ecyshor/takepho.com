#!/usr/bin/env python3
"""Capture screenshots for takepho.com.

Modes:
  apps     Serve the repo root locally, open the bundled web demo views and save
           1200x780 dark-theme screenshots (device scale factor 2, i.e. 2400 px
           wide images) as optimized WebP in img/apps/ — timeline.webp, map.webp,
           photos.webp, overview.webp, strava.webp, activities-map.webp,
           activities-stats.webp, sync.webp, sync-run.webp, takeout.webp, each
           under ~250 KB. The trip page behind photos.webp is resolved at run
           time (the Italy link on the trips page); activity pages fall back to
           the first entry of the activities list if the sample id is missing.
  landing  Capture the home page at the given widths, light and dark, into an
           output directory (verification only; not committed).

Usage (from the repo root, inside `nix develop ./nix`):
  python3 scripts/screenshots.py apps
  python3 scripts/screenshots.py landing --out /tmp/vibe-landing-shots
"""

import argparse
import http.server
import io
import os
import shutil
import socketserver
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 250 * 1024
# App screenshots: 1200x780 CSS viewport at 2x device scale (2400x1560 image).
VIEW_W, VIEW_H = 1200, 780
DSF = 2


def launch_browser(p):
    """Prefer a system Chrome (software WebGL works there); fall back to the
    nix-provided Playwright Chromium."""
    clean_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        exe = shutil.which(name)
        if not exe:
            continue
        try:
            return p.chromium.launch(
                executable_path=exe, env=clean_env,
                args=["--no-sandbox", "--enable-unsafe-swiftshader"],
            )
        except Exception:
            continue
    return p.chromium.launch(args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])

# Demo views (hash router inside /demo/). Each entry: output name, route, a JS
# condition that is true once the view's content has rendered, a settle time
# in ms (maps need extra time for tiles/routes to finish drawing), and optional
# scroll-candidate/score JS for views where the best scroll position depends on
# the final layout (empty string = capture from the top).
# photos.webp is captured separately: the Italy trip page is resolved at run
# time by following the "Italy" link on /demo/#/trips (trip ids change on every
# demo rebuild, so they are never hard-coded).
APP_VIEWS = [
    ("timeline", "/demo/#/timeline", """() => {
      const t = document.body.innerText;
      const cards = document.querySelectorAll('a[href*="#/trips/"]').length;
      const imgs = [...document.images].filter(i => i.complete && i.naturalWidth > 0).length;
      return /Rows/.test(t) && cards >= 5 && imgs >= 5;
    }""", 2500, "", ""),
    ("map", "/demo/#/", """() => {
      const c = document.querySelector('canvas.maplibregl-canvas');
      const aside = document.querySelector('aside');
      const items = aside ? aside.querySelectorAll('button').length : 0;
      const imgs = [...document.images].filter(i => i.complete && i.naturalWidth > 0).length;
      return !!c && c.width > 0 && /In view/.test(document.body.innerText) && items >= 4 && imgs >= 5;
    }""", 6000, "", ""),
    ("overview", "/demo/#/overview", """() => {
      const t = document.body.innerText;
      return /Total Photos/.test(t) && /Km Flown/.test(t) && /Holiday days per year/.test(t);
    }""", 2500, "", ""),
    ("strava", "/demo/#/activities/1", """() => {
      const c = document.querySelector('canvas.maplibregl-canvas');
      const imgs = [...document.images].filter(i => i.complete && i.naturalWidth > 0).length;
      return !!c && c.width > 0 && /Best photos/.test(document.body.innerText) && imgs >= 8;
    }""", 6000, "", ""),
    ("activities-map", "/demo/#/activities", """() => {
      const c = document.querySelector('canvas.maplibregl-canvas');
      const aside = document.querySelector('aside');
      const items = aside ? aside.querySelectorAll('button').length : 0;
      return !!c && c.width > 0 && /Activities in view/.test(document.body.innerText) && items >= 3;
    }""", 8000, "", ""),
    ("activities-stats", "/demo/#/activities/stats", """() => {
      const t = document.body.innerText;
      return /Matched photos/.test(t) && /Per year/.test(t) && /Moving time/.test(t);
    }""", 2500, "", ""),
    ("sync", "/demo/#/sync/albums", """() => {
      const t = document.body.innerText;
      return /Albums/.test(t) && (t.match(/in Proton/g) || []).length >= 5;
    }""", 2000, "", ""),
    # sync-run.webp: the three stacked cards do not fit in one viewport, so try
    # a scroll position that shows all three card headers plus the signed-in
    # line and as many sync stats as possible.
    ("sync-run", "/demo/#/sync", """() => {
      const t = document.body.innerText;
      return /Proton connection/.test(t) && /What to sync/.test(t) && /Signed in to Proton/.test(t);
    }""", 2000, """() => {
      const vh = innerHeight, sy = scrollY;
      const heads = [...document.querySelectorAll('h2')]
        .filter(h => ['Proton connection', 'What to sync', 'Sync'].includes((h.textContent || '').trim()));
      const signed = [...document.querySelectorAll('*')]
        .filter(e => /Signed in to Proton/.test(e.textContent || ''))
        .pop();
      const cands = [{name: 'top', y: 0}];
      const syncHead = heads.find(h => (h.textContent || '').trim() === 'Sync');
      if (syncHead) {
        let y = Math.round(syncHead.getBoundingClientRect().bottom + sy - vh + 16);
        if (signed) y = Math.min(y, Math.round(signed.getBoundingClientRect().top + sy));
        cands.push({name: 'all-cards', y: Math.max(0, y)});
      }
      return cands;
    }""", """() => {
      const vh = innerHeight;
      const vis = e => { const b = e.getBoundingClientRect(); return b.bottom > 0 && b.top < vh; };
      const heads = [...document.querySelectorAll('h2')]
        .filter(h => ['Proton connection', 'What to sync', 'Sync'].includes((h.textContent || '').trim()));
      const headsVis = heads.filter(vis).length;
      const signed = [...document.querySelectorAll('*')]
        .some(e => /Signed in to Proton/.test(e.textContent || '') && vis(e));
      const statsVis = ['Uploaded', 'Pending', 'Last sync'].filter(n =>
        [...document.querySelectorAll('*')].some(e => e.children.length === 0
          && (e.textContent || '').includes(n) && vis(e))).length;
      return {headsVis, signedIn: signed, statsVis,
              score: headsVis * 5 + (signed ? 5 : 0) + statsVis};
    }"""),
    ("takeout", "/demo/#/takeout", """() => {
      const t = document.body.innerText;
      return /Local folder/.test(t) && /Drive link/.test(t) && /Google account/.test(t)
          && /Ingestion/.test(t) && /Completed/.test(t);
    }""", 2000, "", ""),
]

# Demo chrome (sample-data banner) and demo-only warning leaf text are hidden
# before capturing, so the shots show app content only, no banners.
HIDE_DEMO_CHROME = """() => {
  document.querySelectorAll('div, aside, header').forEach(el => {
    const t = (el.textContent || '').trim();
    if (t.length < 250 && /demo with sample data|download the app/i.test(t) && el.querySelector('a')) el.remove();
  });
  document.querySelectorAll('*').forEach(el => {
    if (el.children.length === 0) {
      const t = el.textContent || '';
      if (/exiftool/i.test(t) && t.length < 400) el.style.visibility = 'hidden';
    }
  });
}"""

# Wait until every image that intersects the viewport has finished loading
# (thumbnails must not show up as grey boxes).
WAIT_VIEWPORT_IMAGES = """() => [...document.images].filter(i => {
  const b = i.getBoundingClientRect();
  return b.width > 20 && b.bottom > -50 && b.top < innerHeight + 50;
}).every(i => i.complete && i.naturalWidth > 0)"""

# Scroll candidates + scoring for the two views that need a scroll position
# chosen at run time (the layout shifts when the demo banner is hidden).
# strava.webp: route map plus the "Best photos" strip (they do not both fit in
# the viewport, so the candidate that shows the most of both wins).
STRAVA_CANDIDATES = """() => {
  const vh = innerHeight, sy = scrollY;
  const c = document.querySelector('canvas.maplibregl-canvas');
  const bp = [...document.querySelectorAll('h1,h2,h3,h4,div')]
    .filter(e => (e.textContent || '').trim() === 'Best photos').pop();
  const cands = [{name: 'top', y: 0}];
  if (c) {
    const cb = c.getBoundingClientRect().bottom + sy;
    cands.push({name: 'map-full', y: Math.max(0, Math.round(cb - vh + 16))});
  }
  if (bp) {
    const bpBottom = bp.getBoundingClientRect().bottom + sy;
    // only the "Best photos" strip (not the "Photos along the route" strip below it)
    const strip = [...document.images].filter(i => {
      const b = i.getBoundingClientRect();
      return b.width > 100 && b.top + sy >= bpBottom && b.top + sy < bpBottom + 250;
    });
    if (strip.length) {
      const bottom = Math.max(...strip.map(i => i.getBoundingClientRect().bottom + sy));
      cands.push({name: 'map+photos', y: Math.max(0, Math.round(bottom - vh + 16))});
    }
  }
  return cands;
}"""
STRAVA_SCORE = """() => {
  const vh = innerHeight;
  const vis = e => { const b = e.getBoundingClientRect(); return b.bottom > 0 && b.top < vh; };
  const frac = e => { const b = e.getBoundingClientRect();
    return Math.max(0, Math.min(b.bottom, vh) - Math.max(b.top, 0)) / Math.max(1, b.height); };
  const c = document.querySelector('canvas.maplibregl-canvas');
  const h1 = document.querySelector('h1');
  const bp = [...document.querySelectorAll('h1,h2,h3,h4,div')]
    .filter(e => (e.textContent || '').trim() === 'Best photos').pop();
  let full = 0, partial = 0;
  if (bp) {
    const bpBottom = bp.getBoundingClientRect().bottom;
    const strip = [...document.images].filter(i => {
      const b = i.getBoundingClientRect();
      return b.width > 100 && b.top >= bpBottom && b.top < bpBottom + 250;
    });
    full = strip.filter(i => { const b = i.getBoundingClientRect();
      return b.top >= 0 && b.bottom <= vh && i.complete && i.naturalWidth > 0; }).length;
    partial = strip.filter(i => vis(i) && i.complete && i.naturalWidth > 0).length;
  }
  const mapFrac = c ? frac(c) : 0;
  // the route map with its photo markers matters most, the photo strip second
  return {mapFrac: +mapFrac.toFixed(2), bestPhotos: !!(bp && vis(bp)), full, partial,
          score: mapFrac * 30 + (bp && vis(bp) ? 4 : 0) + full + 0.1 * partial + (h1 && vis(h1) ? 2 : 0)};
}"""

# photos.webp: the Italy trip page — prefer the trip title plus the Activities
# panel and a day with a full row of photos; fall back to a day header with
# 4+ photos in view.
PHOTOS_CANDIDATES = """() => {
  const vh = innerHeight, sy = scrollY;
  const h1 = document.querySelector('h1');
  const h1y = h1 ? h1.getBoundingClientRect().top + sy : 0;
  const days = [...document.querySelectorAll('h3')]
    .filter(h => /^Day \\d/.test((h.textContent || '').trim()));
  const cands = [{name: 'top', y: 0}];
  if (days.length) {
    const d0y = days[0].getBoundingClientRect().top + sy;
    const row = [...document.images].filter(i => {
      const b = i.getBoundingClientRect();
      return b.width > 100 && b.top + sy > d0y && b.top + sy < d0y + 600;
    });
    if (row.length) {
      const bottom = Math.max(...row.map(i => i.getBoundingClientRect().bottom + sy));
      // scroll just enough to fit the first photo row at the bottom of the
      // viewport, keeping the trip title visible when possible
      cands.push({name: 'title+day1', y: Math.max(0, Math.min(Math.round(bottom - vh + 16), Math.round(h1y)))});
    }
    for (const d of days.slice(0, 4)) {
      const y = d.getBoundingClientRect().top + sy;
      cands.push({name: 'day-' + (d.textContent || '').trim().slice(0, 24), y: Math.max(0, Math.round(y - 90))});
    }
  }
  return cands;
}"""
PHOTOS_SCORE = """() => {
  const vh = innerHeight;
  const vis = e => { const b = e.getBoundingClientRect(); return b.bottom > 0 && b.top < vh; };
  const h1 = document.querySelector('h1');
  const acts = [...document.querySelectorAll('h2')].find(h => /Activities/.test(h.textContent || ''));
  const day = [...document.querySelectorAll('h3')].find(h => /^Day \\d/.test((h.textContent || '').trim()) && vis(h));
  const full = [...document.images].filter(i => {
    const b = i.getBoundingClientRect();
    return b.width > 100 && b.top >= 0 && b.bottom <= vh && i.complete && i.naturalWidth > 0;
  }).length;
  const partial = [...document.images].filter(i => {
    const b = i.getBoundingClientRect();
    return b.width > 100 && b.bottom > 0 && b.top < vh && i.complete && i.naturalWidth > 0;
  }).length;
  return {h1: !!(h1 && vis(h1)), acts: !!(acts && vis(acts)), day: !!day, full, partial,
          score: (h1 && vis(h1) ? 10 : 0) + (acts && vis(acts) ? 6 : 0) + (day ? 4 : 0)
               + full + 0.25 * partial};
}"""


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve_root(port: int) -> subprocess.Popen:
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=1)
            return proc
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("local server did not start")


def save_webp(page, path: Path, quality: int = 82) -> None:
    """Screenshot the page to WebP, cropping the uniform empty margin at the
    bottom and re-encoding with Pillow if over MAX_BYTES. Only the bottom is
    cropped (sampled from the bottom-right corner) so the image keeps the full
    2400 px width; on a dark app page the side margins are content, not empty."""
    png = page.screenshot(type="png")
    try:
        from PIL import Image, ImageChops
    except ImportError:
        page.screenshot(path=str(path), type="webp", quality=quality)
        return
    img = Image.open(io.BytesIO(png)).convert("RGB")
    # find the lowest row that differs from the background colour
    bg = img.getpixel((img.width - 1, img.height - 1))
    diff = ImageChops.difference(img, Image.new("RGB", img.size, bg)).convert("L")
    bbox = diff.point(lambda p: 255 if p > 12 else 0).getbbox()
    if bbox:
        pad = 16
        bottom = min(img.height, bbox[3] + pad)
        if bottom < img.height:
            img = img.crop((0, 0, img.width, bottom))
    q = quality
    while True:
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=q, method=6)
        if buf.tell() <= MAX_BYTES or q <= 40:
            break
        q -= 10
    path.write_bytes(buf.getvalue())
    print(f"  {path.name}: {img.width}x{img.height}, {path.stat().st_size // 1024} KB (quality {q})")


def wait_viewport_images(page, timeout: int = 30000) -> None:
    """Wait until every image intersecting the viewport is fully loaded."""
    try:
        page.wait_for_function(WAIT_VIEWPORT_IMAGES, timeout=timeout)
    except Exception:
        pass


def pick_best_scroll(page, candidates_js: str, score_js: str, label: str) -> None:
    """Try several scroll positions, score what is visible in the viewport at
    each, and leave the page scrolled to the best one."""
    candidates = page.evaluate(candidates_js)
    print(f"  {label} candidates:", [(c["name"], c["y"]) for c in candidates])
    best = None
    for cand in candidates:
        page.evaluate(f"window.scrollTo(0, {cand['y']})")
        page.wait_for_timeout(700)
        wait_viewport_images(page, timeout=20000)
        page.wait_for_timeout(500)
        s = page.evaluate(score_js)
        print(f"  candidate {cand['name']!r} y={cand['y']}: {s}")
        if best is None or s["score"] > best[0]["score"]:
            best = (s, cand)
    s, cand = best
    print(f"  {label}: keeping candidate {cand['name']!r} (score {s['score']})")
    page.evaluate(f"window.scrollTo(0, {cand['y']})")
    page.wait_for_timeout(700)
    wait_viewport_images(page, timeout=20000)


def finish_view(page, settle_ms: int, scroll_js=None, score_js=None, label: str = "") -> None:
    """Let the page settle, hide the demo banner, then either scroll back to
    the top or pick the best scroll position (when scroll_js is given)."""
    page.wait_for_timeout(settle_ms)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    page.evaluate(HIDE_DEMO_CHROME)
    page.wait_for_timeout(1200)
    wait_viewport_images(page, timeout=15000)
    if scroll_js:
        pick_best_scroll(page, scroll_js, score_js, label)
    else:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)


def open_view(page, base: str, route: str, wait_js: str, settle_ms: int,
              scroll_js=None, score_js=None, label: str = "") -> None:
    """Open a demo route and wait until its content is rendered, then hide the
    demo banner and let the layout settle before capturing."""
    page.goto(base + route, wait_until="domcontentloaded", timeout=60000)
    page.evaluate("window.scrollTo(0, 0)")
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_function(wait_js, timeout=45000)
    wait_viewport_images(page)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    finish_view(page, settle_ms, scroll_js, score_js, label)


def open_activity(page, base: str, wait_js: str, settle_ms: int) -> None:
    """Open the sample activity detail page. Tries /activities/1 first (stable
    sample id) and falls back to the first link on the activities list page,
    then waits like any other view and picks the best scroll position (route
    map plus best-photos strip)."""
    route = "/demo/#/activities/1"
    try:
        page.goto(base + route, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(wait_js, timeout=15000)
    except Exception:
        print("  /activities/1 not available, falling back to the activities list")
        page.goto(base + "/demo/#/activities/list", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(
            """() => [...document.querySelectorAll('a[href^="#/activities/"]')]
                .some(a => /#\\/activities\\/[^/]+$/.test(a.getAttribute('href') || ''))""",
            timeout=30000,
        )
        href = page.evaluate(
            """() => [...document.querySelectorAll('a[href^="#/activities/"]')]
                .map(a => a.getAttribute('href'))
                .find(h => /#\\/activities\\/[^/]+$/.test(h))"""
        )
        page.goto(base + "/demo/" + href, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(wait_js, timeout=45000)
    page.evaluate("window.scrollTo(0, 0)")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    wait_viewport_images(page)
    finish_view(page, settle_ms, STRAVA_CANDIDATES, STRAVA_SCORE, "strava")


def capture_photos(page, base: str, out_dir: Path) -> None:
    """Capture the Italy trip page (link resolved at run time from /trips).

    Several scroll candidates are tried and scored; the best one (trip title
    plus the Activities panel and a day with a full row of photos, or failing
    that a day header with 4+ photos in view) is saved as photos.webp."""
    page.goto(base + "/demo/#/trips", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function(
        """() => document.querySelectorAll('a[href*="#/trips/"]').length >= 3""",
        timeout=30000,
    )
    href = page.evaluate(
        """() => [...document.querySelectorAll('a[href*="#/trips/"]')]
            .find(a => /italy/i.test(a.textContent || ''))?.getAttribute('href') || null"""
    )
    if not href:
        raise RuntimeError("no Italy trip link found on /demo/#/trips")
    print(f"  photos: Italy trip {href}")
    page.goto(base + "/demo/" + href, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function(
        """() => {
          const t = document.body.innerText;
          return document.querySelector('h1') && /Activities/.test(t) && /Day by day/.test(t)
              && [...document.querySelectorAll('h3')].some(h => /^Day \\d/.test((h.textContent || '').trim()));
        }""",
        timeout=45000,
    )
    wait_viewport_images(page)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.evaluate(HIDE_DEMO_CHROME)
    page.wait_for_timeout(1200)
    wait_viewport_images(page, timeout=15000)
    pick_best_scroll(page, PHOTOS_CANDIDATES, PHOTOS_SCORE, "photos")
    save_webp(page, out_dir / "photos.webp")


def capture_apps(out_dir: Path) -> None:
    port = free_port()
    server = serve_root(port)
    base = f"http://127.0.0.1:{port}"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            ctx = browser.new_context(
                viewport={"width": VIEW_W, "height": VIEW_H},
                color_scheme="dark",
                device_scale_factor=DSF,
            )
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for name, route, wait_js, settle_ms, scroll_js, score_js in APP_VIEWS:
                print(f"capturing {name}: {route}")
                if name == "strava":
                    open_activity(page, base, wait_js, settle_ms)
                else:
                    open_view(page, base, route, wait_js, settle_ms,
                              scroll_js or None, score_js or None, name)
                save_webp(page, out_dir / f"{name}.webp")
            print("capturing photos: Italy trip page")
            capture_photos(page, base, out_dir)
            if errors:
                print("console errors:", *errors[:10], sep="\n  ")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


LANDING_PAGES = [
    ("home", "/"),
    ("self-host", "/self-host/"),
]


def capture_landing(out_dir: Path) -> None:
    port = free_port()
    server = serve_root(port)
    base = f"http://127.0.0.1:{port}"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            for width in (1440, 375):
                for scheme in ("light", "dark"):
                    ctx = browser.new_context(
                        viewport={"width": width, "height": 1000},
                        color_scheme=scheme,
                        device_scale_factor=1,
                    )
                    page = ctx.new_page()
                    for slug, path in LANDING_PAGES:
                        page.goto(base + path, wait_until="domcontentloaded", timeout=60000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=30000)
                        except Exception:
                            pass
                        # scroll through the page so lazy images load, then back to top
                        page.evaluate(
                            "async () => {"
                            "  const h = document.body.scrollHeight;"
                            "  for (let y = 0; y <= h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }"
                            "  window.scrollTo(0, 0);"
                            "}"
                        )
                        page.wait_for_timeout(1500)
                        name = f"{slug}-{width}-{scheme}.png"
                        page.screenshot(path=str(out_dir / name), full_page=True)
                        sw = page.evaluate("document.documentElement.scrollWidth")
                        print(f"  {name}: scrollWidth={sw} (viewport {width})")
                        if width <= 375 and sw > width:
                            print(f"  WARNING: horizontal overflow at {width}px: {sw}")
                    ctx.close()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["apps", "landing"])
    ap.add_argument("--out", default=None, help="output dir (landing mode)")
    args = ap.parse_args()
    if args.mode == "apps":
        capture_apps(ROOT / "img" / "apps")
    else:
        capture_landing(Path(args.out or "/tmp/vibe-landing-shots"))


if __name__ == "__main__":
    main()
