#!/usr/bin/env python3
"""Capture screenshots for takepho.com.

Modes:
  apps     Serve the repo root locally, open the bundled web demo views and save
           1600x1000 light-theme screenshots as optimized WebP in img/apps/
           (photos.webp, strava.webp, sync.webp, each under ~250 KB).
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
VIEW_W, VIEW_H = 1600, 1000


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

# Demo views (hash router inside /demo/): trip detail, Strava activity, sync.
APP_VIEWS = [
    ("photos", "/demo/#/trips/40a69116-e60c-4427-92a1-de16f1b994fa"),
    ("strava", "/demo/#/strava/activities/9000000001"),
    ("sync", "/demo/#/sync"),
]


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
    """Screenshot the page to WebP, re-encoding with Pillow if over MAX_BYTES."""
    png = page.screenshot(type="png")
    try:
        from PIL import Image
    except ImportError:
        page.screenshot(path=str(path), type="webp", quality=quality)
        return
    img = Image.open(io.BytesIO(png)).convert("RGB")
    q = quality
    while True:
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=q, method=6)
        if buf.tell() <= MAX_BYTES or q <= 40:
            break
        q -= 10
    path.write_bytes(buf.getvalue())
    print(f"  {path.name}: {path.stat().st_size // 1024} KB (quality {q})")


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
                color_scheme="light",
                device_scale_factor=1,
            )
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for name, route in APP_VIEWS:
                url = base + route
                print(f"capturing {name}: {route}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_load_state("networkidle", timeout=45000)
                except Exception:
                    pass
                # give maps/tiles and lazy thumbnails time to settle
                page.wait_for_timeout(4000)
                save_webp(page, out_dir / f"{name}.webp")
            if errors:
                print("console errors:", *errors[:10], sep="\n  ")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


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
                    page.goto(base + "/", wait_until="domcontentloaded", timeout=60000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception:
                        pass
                    page.wait_for_timeout(1500)
                    name = f"home-{width}-{scheme}.png"
                    page.screenshot(path=str(out_dir / name), full_page=True)
                    sw = page.evaluate("document.documentElement.scrollWidth")
                    print(f"  {name}: scrollWidth={sw} (viewport {width})")
                    if width == 375 and sw > 375:
                        print(f"  WARNING: horizontal overflow at 375px: {sw}")
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
