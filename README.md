# Takeout Photo Landing Page

This is the static website for Takeout Photo, hosted at [takepho.com](https://takepho.com).

## What is Takeout Photo?

Takeout Photo is a desktop app for Mac (Apple silicon, macOS 12 or later) that turns your Google Takeout export into a private, browsable photo timeline of your life. Trips are detected automatically, places are named, the best shots are picked for you, and routes are drawn on a map. Everything runs on your own computer — your photos are never uploaded to our servers. The app is free to download and explore; importing your own Takeout needs a plan (Lifetime one-time or Yearly subscription, sold via Stripe Managed Payments with Link as merchant of record — see the Pricing section on the home page).

## Release assets and appcast (this repo doubles as the app's release host)

The app's release CI (in the private app repo) publishes every `v*` release here, to this public repo's **GitHub Releases**, and commits the update feed:

- `TakeoutPhoto-macos-arm64.dmg` — constant-name DMG, so `https://github.com/ecyshor/takepho.com/releases/latest/download/TakeoutPhoto-macos-arm64.dmg` always points at the latest release (the site's "Download for Mac" button).
- `TakeoutPhoto-<version>-macos-arm64.zip` — the Sparkle update archive (EdDSA-signed).
- `appcast.xml` — at the repo root, served at `https://takepho.com/appcast.xml`; it is the Sparkle `SUFeedURL` baked into the app. **Committed by the app's release CI — do not hand-edit it.**

Release notes are the GitHub release pages (`https://github.com/ecyshor/takepho.com/releases`).

## Site assets

- `favicon.svg` — the Takeout Photo logo: a white takeout box with a photo (sun + mountains) on its front, on a rounded indigo→violet gradient tile. It is the same file as the app's `common/frontend/public/favicon.svg` in [ecyshor/takepho](https://github.com/ecyshor/takepho). The site uses it as the favicon, the header brand icon, and the hero logo on the home page.
- `apple-touch-icon.png` — 180×180 px raster version of the logo, used as the Apple touch icon for iOS home-screen bookmarks.
- `demo/` — the static, read-only demo of the app (takepho.com/demo, linked from the hero's "Try the demo" button): the app's frontend built in demo mode plus a JSON/image snapshot of its API for the made-up sample library (photos from Wikimedia Commons, credited in the app). Generated, do not edit by hand — rebuild it from the app repo with `scripts/run_python.sh scripts/build_demo.py --out ../takepho.com/demo` (it replaces the folder's contents).
- `og-image.png` — 1200×630 social/OG image (logo + "Takeout Photo" + tagline on the indigo→violet gradient), referenced by the `og:image` / `twitter:image` tags on every page.

## Pages

- `index.html` — home: hero with the "Download for Mac" button (stable release link) + "Try the demo", how it works, pricing (Lifetime / Yearly plan cards, regional prices table, how to buy, merchant-of-record note), the three use cases (links to the guides below), features, updates (Developer ID signing, notarization, Sparkle self-update), FAQ. JSON-LD `@graph` with Organization/WebSite/SoftwareApplication (macOS, `downloadUrl`, two `Offer`s) and a FAQPage mirroring the visible FAQ.
- `google-photos-takeout/index.html` — guide/landing page for "google photos takeout" (Takeout viewer: what a Takeout contains, JSON sidecars, in-place reading, trips/places/maps, how to export); hero CTA links the Mac download and the pricing.
- `google-photos-strava/index.html` — guide/landing page for "google photos strava" (photos matched to Strava activities along the GPS track).
- `google-photos-to-proton-photos/index.html` — guide/landing page for "google photos proton import" (moving the Takeout to Proton Photos with albums and metadata).
- `privacy.html`, `terms.html`, `404.html` — legal pages (404 is `noindex`). Privacy has an "Account and purchases (account.takepho.com)" section (data stored, purposes/legal bases, retention, processors, rights, account deletion); terms has the licence terms (personal licence per account, 2 Macs, Lifetime/Yearly, Link/Stripe as seller of record at checkout).

## Crawl / SEO / AI-search files (repo root)

- `robots.txt` — allows all crawlers (including the AI ones: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot/-User/-SearchBot, anthropic-ai, PerplexityBot/-User, Google-Extended, Applebot-Extended, CCBot, Bingbot), disallows only `/demo/data/`, points at the sitemap.
- `sitemap.xml` — all public pages with `<lastmod>`.
- `llms.txt` — llmstxt.org-format summary of the product with the Mac download link, pricing (plans, regional prices, merchant of record), links to the pages, status, privacy, contact, and the releases repo.
- `llms-full.txt` — plain-markdown content of the home page and the three guide pages, for LLM consumption without HTML.
- `og-image.png` — see above.

## SEO / AI search (GEO) checklist for new pages

When adding a page (outside `demo/`), also:

1. Add it to `sitemap.xml`, to `llms.txt` (and regenerate/append its content in `llms-full.txt`), and to the footer links of every page.
2. In `<head>`: canonical URL, `robots` meta, `og:title`/`og:description`/`og:type`/`og:url`/`og:site_name`/`og:image` (+ width/height/alt), `twitter:card` + title/description/image, and a JSON-LD block (`WebPage` + `BreadcrumbList` + `FAQPage` mirroring the visible FAQ; on the home page an `@graph` with `Organization`/`WebSite`/`SoftwareApplication`/`FAQPage`).
3. Add the analiza.dev tracker `<script>` tag (same tenant), the stylesheet and the favicons.
4. Exactly one `<h1>` per page, answer-first summary paragraph under it, FAQ in `<details class="faq-item">`.

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
