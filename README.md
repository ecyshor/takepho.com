# Takeout Photo Landing Page

This is the static website for Takeout Photo, hosted at [takepho.com](https://takepho.com).

## What is Takeout Photo?

Takeout Photo is a desktop app that turns your Google Takeout export into a private, browsable photo timeline of your life. Trips are detected automatically, places are named, the best shots are picked for you, and routes are drawn on a map. Everything runs on your own computer — your photos are never uploaded to our servers.

## Site assets

- `favicon.svg` — the Takeout Photo logo: a white takeout box with a photo (sun + mountains) on its front, on a rounded indigo→violet gradient tile. It is the same file as the app's `common/frontend/public/favicon.svg` in [ecyshor/takepho](https://github.com/ecyshor/takepho). The site uses it as the favicon, the header brand icon, and the hero logo on the home page.
- `apple-touch-icon.png` — 180×180 px raster version of the logo, used as the Apple touch icon for iOS home-screen bookmarks.
- `demo/` — the static, read-only demo of the app (takepho.com/demo, linked from the hero's "Try the demo" button): the app's frontend built in demo mode plus a JSON/image snapshot of its API for the made-up sample library (photos from Wikimedia Commons, credited in the app). Generated, do not edit by hand — rebuild it from the app repo with `scripts/run_python.sh scripts/build_demo.py --out ../takepho.com/demo` (it replaces the folder's contents).

## Analytics

Every page loads the [analiza.dev](https://analiza.dev) tracker (`<script defer src="https://cdn.jsdelivr.net/gh/ecyshor/analiza@main/tracker/analiza.min.js" tenant="…">` in `<head>`) with the same tenant as nicu.dev; `takepho.com` must be registered as a domain of that tenant in the analiza admin, otherwise the API rejects the events. It sets no cookies; what it records is described in `privacy.html` → "This website". Add the same tag to any new page.

## Preview locally

From the repository root:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Deployment

The site is deployed via GitHub Pages:
- **Branch:** `main`
- **Folder:** root (`/`) 
- **Custom domain:** `takepho.com`
- **Enforce HTTPS:** enabled

## DNS configuration (Squarespace)

To set up the custom domain at Squarespace:

1. **Remove Squarespace's default records** for `@` and `www` first.

2. **Add A records for `@` (root domain):**
   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```

3. **Add AAAA records for `@` (IPv6):**
   ```
   2606:50c0:8000::153
   2606:50c0:8001::153
   2606:50c0:8002::153
   2606:50c0:8003::153
   ```

4. **Add CNAME for `www`:**
   ```
   www -> ecyshor.github.io
   ```

After adding these records, GitHub Pages will automatically provision an SSL certificate for the domain.
