# Takeout Photo Landing Page

This is the static website for Takeout Photo, hosted at [takepho.com](https://takepho.com).

## What is Takeout Photo?

Takeout Photo is a desktop app for Mac (Apple silicon, macOS 12 or later) and Windows (10 or 11, 64-bit) that turns your Google Takeout export into built-in apps you can use on your own computer: a private, browsable photo timeline of your life (holidays and day trips are detected automatically, places are named, the best shots are picked for you, and routes are drawn on a map), your photos matched to your Strava, Komoot and Garmin Connect activities along the GPS track, and a move to Proton Photos. There is also a Docker image for running it on a NAS. Everything runs on your own computer; your photos are never uploaded to our servers. The app is free to download and explore; the free Lite plan imports your own Takeout for your 5 most recent holidays (photo timeline only, no account needed), and the paid plans — Lifetime one-time or Yearly subscription, bought inside the app (see the Pricing section on the home page) — unlock the whole library and the other apps.

## Release assets and appcast (this repo doubles as the app's release host)

The app's release CI (in the private app repo) publishes every `v*` release here, to this public repo's **GitHub Releases**, and commits the update feed:

- `TakeoutPhoto-macos-arm64.dmg`: constant-name DMG, so `https://github.com/ecyshor/takepho.com/releases/latest/download/TakeoutPhoto-macos-arm64.dmg` always points at the latest release (the site's "Download for Mac" button).
- `TakeoutPhoto-windows-x64-setup.exe`: constant-name Windows installer, so `https://github.com/ecyshor/takepho.com/releases/latest/download/TakeoutPhoto-windows-x64-setup.exe` always points at the latest release (the site's primary "Download for Windows" button). Windows 10 or 11, 64-bit. **The release CI must publish an asset with exactly this name on every `v*` release.**
- `TakeoutPhoto-windows-x64.zip`: constant-name portable Windows archive, so `https://github.com/ecyshor/takepho.com/releases/latest/download/TakeoutPhoto-windows-x64.zip` always points at the latest release (the site's "Windows portable zip" link in the home hero note and the "download the portable zip" note on the Windows platform card; it does not update itself). **The release CI must publish an asset with exactly this name on every `v*` release.**
- `TakeoutPhoto-<version>-macos-arm64.zip`: the Sparkle update archive (EdDSA-signed).
- `appcast.xml`: at the repo root, served at `https://takepho.com/appcast.xml`; it is the Sparkle `SUFeedURL` baked into the Mac app. **Committed by the app's release CI: do not hand-edit it.**
- `appcast-windows.xml`: at the repo root, served at `https://takepho.com/appcast-windows.xml`; it is the WinSparkle feed of the Windows app (daily update checks, EdDSA-signed items). **Committed by the app's release CI: do not hand-edit it.**

Release notes are the GitHub release pages (`https://github.com/ecyshor/takepho.com/releases`).

## Site assets

- `fonts/`: self-hosted woff2 files (Bricolage Grotesque 600-800 and Atkinson Hyperlegible Next 400-700, latin subset), fetched once from the Google Fonts CSS2 API and served from `/fonts/` by `style.css`, so no font CDN is contacted at runtime.
- `img/apps/`: ten WebP screenshots of the demo app (1200x780 viewport at device scale factor 2, i.e. 2400 px wide, dark theme, each under 250 KB), captured from the bundled demo with `scripts/screenshots.py` (run inside `nix develop ./nix`):
  - `timeline.webp` — the Photos "Rows" timeline: year cards (2025: 3 trips · 465 photos; 2024: 2 trips · 166 photos) with trip cards (Paris, Barcelona, Italy, Lisbon) and cover photos joined by the timeline path.
  - `map.webp` — the world map with all 5 trip routes and the "In view" list of trips with cover thumbnails (Paris 100 photos, Barcelona 125, Italy 240, Lisbon 150, Bern 16).
  - `photos.webp` — the Italy trip page (Apr 9–17, 2025, 9 days, 240 photos): title line, the Activities (1) panel with the "Rome evening ride", and Day 1 with its row of photos.
  - `overview.webp` — the Overview stat tiles (Total Photos 1,006; Holidays 4; Day Trips 1; Countries 6; Flights 10; Km Flown 10,478) and the "Holiday days per year" chart (2024: 7 days, 2025: 20 days).
  - `strava.webp` — the "Rome evening ride" activity page: route map with photo markers plus the "Best photos" strip (8 photos, 46.8 km, 3:55, 1055 m).
  - `activities-map.webp` — the Activities map with all 3 routes drawn and the "Activities in view" list (Rome evening ride 46.8 km, Lisbon riverside run 10.1 km, Bern day trip hike 76.2 km).
  - `activities-stats.webp` — the Activities stats: totals tiles (3 activities, 133.1 km, 12:45 moving, 3069 m elevation, 3/3 with photos, 22 matched photos) and the per-year distance chart (2024: 86.3 km, 2025: 46.8 km).
  - `sync.webp` — the Proton Photos sync albums table: 6 trip albums (Bern, Lisbon, Italy, Barcelona, Paris, Munich) each with its photo count and an "in Proton" check.
  - `sync-run.webp` — the Sync page in the signed-in, synced state, scrolled to show all three cards: the Proton connection card with "Signed in to Proton", the What to sync card, and the Sync card with its asset stats (1006 assets, Uploaded 1006).
  - `takeout.webp` — the Takeout page: the three source options (Local folder, Drive link, Google account) and the Ingestion step checklist, all ticked, "Completed".
- `favicon.svg`: the Takeout Photo logo: a white takeout box with a photo (sun + mountains) on its front, on a rounded indigo→violet gradient tile. It is the same file as the app's `common/frontend/public/favicon.svg` in the app's private repository. The site uses it as the favicon, the header brand icon, and the hero logo on the home page.
- `apple-touch-icon.png`: 180×180 px raster version of the logo, used as the Apple touch icon for iOS home-screen bookmarks.
- `demo/`: the static, read-only demo of the app (takepho.com/demo, linked from the header's "Live demo" nav link and the home page's primary "Open the live demo" button in the hero and the closing CTA, plus the hero screenshot's caption): the app's frontend built in demo mode plus a JSON/image snapshot of its API for the made-up sample library (photos from Wikimedia Commons, credited in the app). Generated, do not edit by hand: rebuild it from the app repo with `scripts/run_python.sh scripts/build_demo.py --out ../takepho.com/demo` (it replaces the folder's contents).
- `og-image.png`: 1200×630 social/OG image (logo + "Takeout Photo" + tagline on the indigo→violet gradient), referenced by the `og:image` / `twitter:image` tags on every page.

## Pages

- `index.html`: home: a split hero (two columns on desktop, copy left and the Photos timeline screenshot from `img/apps/` right) with the outcome headline "Turn your Google Takeout into a timeline of every trip you've taken" and a lead paragraph, the demo as the solid primary "Open the live demo" button followed by "Download for Mac" / "Download for Windows" secondary buttons, a short demo line, a hero note (free/Lite, Mac Apple silicon macOS 12+, Windows 10/11, NAS Docker, Windows portable zip) and the collapsed Windows first-launch note; a small inline script at the end of `<body>` adds `os-mac` / `os-win` / `os-mobile` to `<html>` from the user agent and touch points, and CSS then hides the non-matching download button in the hero (with an "Also for …" line), or on phones hides both downloads and shows a "Send the link to my computer" share button plus a "desktop app" note. Then a trust strip (runs on your computer / free Lite plan / Mac app signed and notarized by Apple / pay once), the archive → processing → built-in apps flow figure, the built-in apps showcase (one panel per built-in app with a demo screenshot from `img/apps/`, plus a lighter "Coming next" block listing more sync destinations beyond Proton Photos and Google Drive / Google Docs support from your Takeout), platforms (Mac: Apple silicon M1+ with macOS 12+, signed and notarized; Windows 10/11 64-bit with a link to the first-launch-warning FAQ item; NAS with Docker, linking `/self-host/`), pricing (Lite free card, then Lifetime / Yearly plan cards with bottom-aligned download buttons and "Buy in the app: Settings → Account" notes, regional prices table — the Yearly plan is full price for the first year, then renews automatically at 50% off: USD 25 → USD 12.50/year, EUR 20 → EUR 10, GBP 20 → GBP 10, CHF 20 → CHF 10; buy inside the app; no payment-processor wording), privacy, FAQ (19 items, including "What happens if an import is interrupted?" and "How does the app update?", which replaced the old Updates section), and a closing CTA card repeating the demo + download buttons; the header is sticky (with `scroll-margin-top` on anchored sections). JSON-LD `@graph` with Organization/WebSite/SoftwareApplication (macOS + Windows + Docker, `downloadUrl` = the Mac DMG, three `Offer`s: Lite free, Lifetime, Yearly) and a FAQPage mirroring the visible FAQ.
- `google-photos-takeout/index.html`: guide/landing page for "google photos takeout" (Takeout viewer: what a Takeout contains, JSON sidecars, in-place reading, trips/places/maps, how to export); hero CTA links the Mac and Windows downloads and the pricing.
- `google-photos-strava/index.html`: guide/landing page for "google photos strava" (photos matched to your Strava, Komoot and Garmin Connect activities along the GPS track; the page stays Strava-focused because of the URL, and says Komoot and Garmin Connect work the same way).
- `google-photos-to-proton-photos/index.html`: guide/landing page for "google photos proton import" (moving the Takeout to Proton Photos with albums and metadata).
- `self-host/index.html`: NAS self-hosting guide (Docker Compose): requirements, compose file, folders, security, updating. Linked from the header, hero note, platforms section and footers; listed in `sitemap.xml`.
- `privacy.html`, `terms.html`, `404.html`: legal pages (404 is `noindex`). Privacy has an "Account and purchases (account.takepho.com)" section (data stored, purposes/legal bases, retention, processors, rights, account deletion); terms has the licence terms (personal licence per account, 2 devices (Mac or Windows), Lifetime/Yearly, Link/Stripe as seller of record at checkout).

## Support issues

The app's in-app **Support** link opens `https://github.com/ecyshor/takepho.com/issues/new`. `.github/ISSUE_TEMPLATE/support.yml` is the only issue form (blank issues are disabled in `config.yml`): it requires where the app runs (Mac app / web demo / other), the app version, the affected area, what happened, steps to reproduce and the expected result, and asks for logs (`~/Library/Logs/TakeoutPhoto/desktop.log`) and screenshots, with a reminder to redact personal data since the repo is public. Issues get the `question` label.

## Crawl / SEO / AI-search files (repo root)

- `robots.txt`: allows all crawlers (including the AI ones: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot/-User/-SearchBot, anthropic-ai, PerplexityBot/-User, Google-Extended, Applebot-Extended, CCBot, Bingbot), disallows only `/demo/data/`, points at the sitemap.
- `sitemap.xml`: all public pages with `<lastmod>`.
- `llms.txt`: llmstxt.org-format summary of the product with the Mac and Windows download links, the NAS option, pricing (plans, regional prices), links to the pages, status, privacy, contact, and the releases repo.
- `llms-full.txt`: plain-markdown content of the home page and the three guide pages, for LLM consumption without HTML.
- `og-image.png`: see above.
- `scripts/screenshots.py`: serves the repo root locally and uses headless Chromium (Playwright, from the nix dev shell) to capture the demo app views into `img/apps/*.webp` (`apps` mode) or home-page verification screenshots at 1440/375 px, light and dark (`landing --out <dir>` mode).

## SEO / AI search (GEO) checklist for new pages

When adding a page (outside `demo/`), also:

1. Add it to `sitemap.xml`, to `llms.txt` (and regenerate/append its content in `llms-full.txt`), and to the footer links of every page.
2. In `<head>`: canonical URL, `robots` meta, `og:title`/`og:description`/`og:type`/`og:url`/`og:site_name`/`og:image` (+ width/height/alt), `twitter:card` + title/description/image, and a JSON-LD block (`WebPage` + `BreadcrumbList` + `FAQPage` mirroring the visible FAQ; on the home page an `@graph` with `Organization`/`WebSite`/`SoftwareApplication`/`FAQPage`).
3. Add the analiza.dev tracker `<script>` tag (same tenant), the stylesheet and the favicons.
4. Exactly one `<h1>` per page, answer-first summary paragraph under it, FAQ in `<details class="faq-item">`.

## Analytics

Every page loads the [analiza.dev](https://analiza.dev) tracker (`<script defer src="https://cdn.analiza.dev/analiza.js" tenant="…">` in `<head>`) with the same tenant as nicu.dev; `takepho.com` must be registered as a domain of that tenant in the analiza admin, otherwise the API rejects the events. It sets no cookies; what it records is described in `privacy.html` → "This website". Add the same tag to any new page.

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
