#!/usr/bin/env python3
"""Capture screenshots for takepho.com.

Modes:
  apps     Serve the repo root locally, open the bundled web demo views and save
           1200x780 dark-theme screenshots (device scale factor 2, i.e. 2400 px
           wide images) as optimized WebP in img/apps/ — timeline.webp, map.webp,
           overview.webp, strava.webp, activities-map.webp, activities-stats.webp,
           sync.webp, takeout.webp, each under ~250 KB, plus photos.webp (the
           Italy trip page). The trip page behind photos.webp is resolved at run
           time (the Italy link on the trips page); activity pages fall back to
           the first entry of the activities list if the sample id is missing.
           Optional view names re-capture only those images (e.g.
           `apps photos activities-map`), leaving the rest untouched.
           Per-view framing: photos.webp is captured from the very top of the
           trip page (scrollY = 0) so the sticky header cannot clip the title
           or stats line (fallback: scroll so the "Activities (n)" card sits
           24 CSS px under the header); activities-map.webp is captured after
           zooming the MapLibre map to the "Rome evening ride" route and waiting
           for all tiles, with the route pixels verified by pixel analysis
           before saving.
  landing  Capture the home page at the given widths, light and dark, into an
           output directory (verification only; not committed).

Usage (from the repo root, inside `nix develop ./nix`):
  python3 scripts/screenshots.py apps
  python3 scripts/screenshots.py apps photos activities-map
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

# photos.webp: captured from the very top of the trip page (scrollY = 0), so the
# sticky app header cannot cut the trip title or the stats line and the shot
# shows the title, the stats line, the Activities panel and the start of
# "Day by day" with the first photo row. If the top of the page is occupied by
# something else (e.g. a big map) so that no photos are visible at scrollY = 0,
# fall back to scrolling so that the top edge of the "Activities (n)" card sits
# about 24 CSS px under the sticky header (no text line may be cut by it).
PHOTOS_TOP_OK = """() => {
  const vh = innerHeight;
  const nav = document.querySelector('nav.sticky') || document.querySelector('nav');
  const navBottom = nav ? nav.getBoundingClientRect().bottom : 0;
  const h1 = document.querySelector('h1');
  const hb = h1 ? h1.getBoundingClientRect() : null;
  const vis = e => { const b = e.getBoundingClientRect(); return b.bottom > 0 && b.top < vh; };
  const belowNav = e => { const b = e.getBoundingClientRect(); return b.top >= navBottom && b.bottom <= vh; };
  const photos = [...document.images].filter(i => {
    const b = i.getBoundingClientRect();
    return b.width > 100 && b.bottom > 0 && b.top < vh && i.complete && i.naturalWidth > 0;
  }).length;
  const acts = [...document.querySelectorAll('h2')]
    .some(h => /Activities \\(\\d+\\)/.test((h.textContent || '').trim()) && vis(h) && belowNav(h));
  const day = [...document.querySelectorAll('h3')]
    .some(h => /^Day \\d/.test((h.textContent || '').trim()) && vis(h) && belowNav(h));
  const bigCanvas = [...document.querySelectorAll('canvas')].some(c => {
    const b = c.getBoundingClientRect();
    return b.width > innerWidth * 0.5 && b.height > vh * 0.5;
  });
  const ok = !!(h1 && hb && belowNav(h1) && photos >= 1 && acts && day && !bigCanvas);
  return {ok, h1Top: hb ? Math.round(hb.top) : null, navBottom: Math.round(navBottom),
          photos, acts, day, bigCanvas};
}"""
PHOTOS_FALLBACK_SCROLL = """() => {
  const nav = document.querySelector('nav.sticky') || document.querySelector('nav');
  const navH = nav ? nav.getBoundingClientRect().height : 0;
  const acts = [...document.querySelectorAll('h2')]
    .find(h => /Activities \\(\\d+\\)/.test((h.textContent || '').trim()));
  if (!acts) return 0;
  const card = acts.closest('div.card') || acts.parentElement;
  const top = card.getBoundingClientRect().top + scrollY;
  return Math.max(0, Math.round(top - navH - 24));
}"""

# activities-map.webp: the initial fitBounds spans all three routes (Rome,
# Lisbon, Bern), leaving them a few pixels long on the western-Europe view.
# Zoom the MapLibre map to the "Rome evening ride" route instead: find the map
# instance through the React fiber of the map container, fit the route's bounds
# and wait until the map is idle (all tiles drawn) before capturing.
FIND_MAPLIBRE_MAP = """() => {
  function findMap(root) {
    const seen = new Set(); const stack = [root];
    while (stack.length) {
      const f = stack.pop();
      if (!f || seen.has(f)) continue; seen.add(f);
      let h = f.memoizedState;
      while (h) {
        const m = h.memoizedState;
        if (m && typeof m === 'object' && typeof m.current === 'object' && m.current
            && typeof m.current.getSource === 'function' && typeof m.current.fitBounds === 'function')
          return m.current;
        h = h.next;
      }
      if (f.child) stack.push(f.child);
      if (f.sibling) stack.push(f.sibling);
      if (f.return) stack.push(f.return);
    }
    return null;
  }
  const canvas = document.querySelector('canvas.maplibregl-canvas');
  const cont = canvas ? (canvas.closest('.maplibregl-map') || canvas.parentElement) : null;
  if (!cont) return null;
  for (const k of Object.keys(cont)) {
    if (k.startsWith('__reactFiber')) {
      const m = findMap(cont[k]);
      if (m) return m;
    }
  }
  return null;
}"""
ZOOM_ACTIVITIES_MAP = """async () => {
  const map = (%s)();
  if (!map) return {error: 'MapLibre map instance not found'};
  const src = map.getSource('activity-routes');
  const feats = (src && src._data && src._data.features) || [];
  const f = feats.find(x => /Rome evening ride/i.test((x.properties || {}).name || '')) || feats[0];
  if (!f) return {error: 'no activity routes loaded'};
  const coords = f.geometry.coordinates;
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity;
  for (const c of coords) {
    minLng = Math.min(minLng, c[0]); maxLng = Math.max(maxLng, c[0]);
    minLat = Math.min(minLat, c[1]); maxLat = Math.max(maxLat, c[1]);
  }
  const bounds = [[minLng, minLat], [maxLng, maxLat]];
  map.fitBounds(bounds, {padding: 48, maxZoom: 15, duration: 0});
  await new Promise(res => {
    const t = setTimeout(res, 20000);
    map.once('idle', () => { clearTimeout(t); res(); });
  });
  return {name: f.properties.name, category: f.properties.category, bounds,
          zoom: +map.getZoom().toFixed(2), center: map.getCenter()};
}""" % FIND_MAPLIBRE_MAP
MAP_CANVAS_RECT = """() => {
  const c = document.querySelector('canvas.maplibregl-canvas');
  const b = c.getBoundingClientRect();
  return {left: b.left, top: b.top + scrollY, w: b.width, h: b.height};
}"""

# Route line colours of the activities map (by category), for the pixel check.
ROUTE_COLORS = {
    "ride-blue": (0x3B, 0x82, 0xF6),
    "run-orange": (0xF9, 0x73, 0x16),
    "hike-green": (0x22, 0xC5, 0x5E),
}


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


def save_webp(page, path: Path, quality: int = 82, png: bytes = None) -> None:
    """Screenshot the page to WebP, cropping the uniform empty margin at the
    bottom and re-encoding with Pillow if over MAX_BYTES. Only the bottom is
    cropped (sampled from the bottom-right corner) so the image keeps the full
    2400 px width; on a dark app page the side margins are content, not empty.
    A pre-taken PNG screenshot can be passed via `png` (used when the pixels
    must be analysed before saving)."""
    if png is None:
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

    Captured from the very top of the page (scrollY = 0) so the sticky header
    cannot clip the trip title or stats line. If the top is occupied by
    something else (e.g. a big map) so that no photos are visible at scrollY =
    0, falls back to scrolling so the "Activities (n)" card top sits 24 CSS px
    under the sticky header. Saved as photos.webp."""
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
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    wait_viewport_images(page, timeout=15000)
    top = page.evaluate(PHOTOS_TOP_OK)
    print(f"  photos: scrollY=0 check: {top}")
    if top["ok"]:
        scroll_y = 0
    else:
        scroll_y = page.evaluate(PHOTOS_FALLBACK_SCROLL)
        print(f"  photos: top of page not usable, scrolling to y={scroll_y} "
              "(Activities card 24 px under the sticky header)")
        page.evaluate(f"window.scrollTo(0, {scroll_y})")
        page.wait_for_timeout(700)
        wait_viewport_images(page, timeout=15000)
    print(f"  photos: scrollY={page.evaluate('scrollY')} (requested {scroll_y})")
    save_webp(page, out_dir / "photos.webp")


def route_pixel_stats(png: bytes, rect: dict, dsf: int = DSF) -> dict:
    """Pixel analysis of a device-scale screenshot: for each route colour, the
    bounding box (CSS px, relative to the top-left of the map canvas) of the
    pixels whose hue matches it, plus the horizontal span of those pixels."""
    import colorsys

    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("RGB")
    x0, y0 = max(0, int(rect["left"] * dsf)), max(0, int(rect["top"] * dsf))
    x1 = min(img.width, int((rect["left"] + rect["w"]) * dsf))
    y1 = min(img.height, int((rect["top"] + rect["h"]) * dsf))
    px = img.load()
    stats = {}
    for name, (r, g, b) in ROUTE_COLORS.items():
        th, _, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        xs, ys = [], []
        for y in range(y0, y1, 2):
            for x in range(x0, x1, 2):
                p = px[x, y]
                h, s, v = colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)
                dh = abs(h - th)
                dh = min(dh, 1 - dh)
                if dh < 0.06 and s > 0.35 and v > 0.25:
                    xs.append(x)
                    ys.append(y)
        if xs:
            stats[name] = {
                "pixels_sampled": len(xs),
                "bbox_css": [round(min(xs) / dsf - rect["left"], 1),
                             round(min(ys) / dsf - rect["top"], 1),
                             round(max(xs) / dsf - rect["left"], 1),
                             round(max(ys) / dsf - rect["top"], 1)],
                "span_w_css": round((max(xs) - min(xs)) / dsf, 1),
            }
        else:
            stats[name] = {"pixels_sampled": 0, "span_w_css": 0}
    return stats


def capture_apps(out_dir: Path, views=None) -> None:
    port = free_port()
    server = serve_root(port)
    base = f"http://127.0.0.1:{port}"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_names = [name for name, *_ in APP_VIEWS] + ["photos"]
    wanted = list(views) if views else all_names
    unknown = [v for v in wanted if v not in all_names]
    if unknown:
        raise SystemExit(f"unknown view(s) {unknown}; known views: {all_names}")
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
                if name not in wanted:
                    continue
                print(f"capturing {name}: {route}")
                if name == "strava":
                    open_activity(page, base, wait_js, settle_ms)
                else:
                    open_view(page, base, route, wait_js, settle_ms,
                              scroll_js or None, score_js or None, name)
                if name == "activities-map":
                    r = page.evaluate(ZOOM_ACTIVITIES_MAP)
                    print(f"  activities-map post-js: {r}")
                print(f"  {name}: scrollY={page.evaluate('scrollY')}")
                if name == "activities-map":
                    # tiles done (map went idle in the post-js); verify by pixel
                    # analysis that a route is clearly drawn before saving
                    page.wait_for_timeout(800)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    png = page.screenshot(type="png")
                    rect = page.evaluate(MAP_CANVAS_RECT)
                    stats = route_pixel_stats(png, rect)
                    print(f"  activities-map: map {rect['w']:.0f}x{rect['h']:.0f} CSS px, "
                          f"route pixels (bbox in CSS px, rel. to map): {stats}")
                    best = max(s["span_w_css"] for s in stats.values())
                    if best < rect["w"] / 3:
                        raise RuntimeError(
                            f"no route spans a third of the map width (best span "
                            f"{best} CSS px < {rect['w'] / 3:.0f}); not saving")
                    save_webp(page, out_dir / f"{name}.webp", png=png)
                else:
                    save_webp(page, out_dir / f"{name}.webp")
            if "photos" in wanted:
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
    ap.add_argument("views", nargs="*",
                    help="apps mode only: capture only these view names "
                         "(default: all nine, e.g. 'apps photos activities-map')")
    ap.add_argument("--out", default=None, help="output dir (landing mode)")
    args = ap.parse_args()
    if args.mode == "apps":
        capture_apps(ROOT / "img" / "apps", views=args.views or None)
    else:
        capture_landing(Path(args.out or "/tmp/vibe-landing-shots"))


if __name__ == "__main__":
    main()
