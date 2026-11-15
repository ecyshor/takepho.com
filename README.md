# Takeout Photo Landing Page

This is the static website for Takeout Photo, hosted at [takepho.com](https://takepho.com).

## What is Takeout Photo?

Takeout Photo is a desktop app for Mac (Apple silicon, macOS 12 or later) and Windows (10 or 11, 64-bit) that reads your Google Takeout export and, on a Mac, your Apple Photos library on your own computer: it finds every holiday and day trip in your photos (places named, best shots picked, routes drawn on a map), turns those trips into albums in Apple Photos and Proton Photos while backing your Google photos up there, and matches your photos to your Strava, Komoot and Garmin Connect activities along the GPS track. There is also a Docker image for running it on a NAS. Everything runs on your own computer; your photos are never uploaded to our servers. The app is free to download and explore; the free Lite plan imports your own Takeout for your 5 most recent holidays (photo timeline only, no account needed), and the paid plans — Lifetime one-time or Yearly subscription, bought inside the app (see the Pricing section on the home page) — unlock the whole library and the other apps.

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
- `img/apps/`: eight WebP screenshots of the demo app (1200x780 viewport at device scale factor 2, i.e. 2400 px wide, dark theme, each under 250 KB), captured from the bundled demo with `scripts/screenshots.py` (run inside `nix develop ./nix`; pass view names to re-capture only some, e.g. `python3 scripts/screenshots.py apps photos activities-map`):
  - `timeline.webp` — the Photos "Rows" timeline: year cards (2025: 3 trips · 465 photos; 2024: 2 trips · 166 photos) with trip cards (Paris, Barcelona, Italy, Lisbon) and cover photos joined by the timeline path.
  - `map.webp` — the world map with all 5 trip routes and the "In view" list of trips with cover thumbnails (Paris 100 photos, Barcelona 125, Italy 240, Lisbon 150, Bern 16).
  - `photos.webp` — the Italy trip page (Apr 9–17, 2025, 9 days, 240 photos), captured from the very top of the page (scrollY = 0) so the sticky header clips nothing: title line, stats line, the Activities (1) panel with the "Rome evening ride", and Day 1 with its row of photos.
  - `overview.webp` — the Overview stat tiles (Total Photos 1,006; Holidays 4; Day Trips 1; Countries 6; Flights 10; Km Flown 10,478) and the "Holiday days per year" chart (2024: 7 days, 2025: 20 days).
  - `strava.webp` — the "Rome evening ride" activity page: route map with photo markers plus the "Best photos" strip (8 photos, 46.8 km, 3:55, 1055 m).
  - `activities-map.webp` — the Activities map zoomed to the "Rome evening ride" route (drawn in blue across ~40% of the map width, pixel-verified at capture time), with the "Activities in view" list on the right showing that ride (46.8 km, 8 photos); the Lisbon run and Bern hike routes are out of frame at this zoom.
  - `sync.webp` — the Proton Photos sync albums table: 6 trip albums (Bern, Lisbon, Italy, Barcelona, Paris, Munich) each with its photo count and an "in Proton" check.
  - `takeout.webp` — the Takeout page: the three source options (Local folder, Drive link, Google account) and the Ingestion step checklist, all ticked, "Completed".
- `img/trips/`: fifteen 560x420 WebP crops (4:3, under 60 KB each) of the app's sample photos (Wikimedia Commons, the same files as the demo's sample library: `apps/photos/backend/photos/sample_photos/` in the app repo) used by the home page's hero route, the "Each moment once" figure and the album table: Lisbon (`lisbon-2/4/5`), Italy (`rome-3/4`, `florence-1/4`), Barcelona (`barcelona-2/3/4`), Paris (`paris-1/2/3`), Bern (`bern-2/3`). Every one is credited (title, author, licence) in the home page's "Photo credits" list; add a credit when adding a photo.
- `home.css`: the home page's own styles (see Pages → `index.html`).
- `favicon.svg`: the Takeout Photo logo: a white takeout box with a photo (sun + mountains) on its front, on a rounded indigo→violet gradient tile. It is the same file as the app's `common/frontend/public/favicon.svg` in the app's private repository. The site uses it as the favicon, the header brand icon, and the hero logo on the home page.
- `apple-touch-icon.png`: 180×180 px raster version of the logo, used as the Apple touch icon for iOS home-screen bookmarks.
- `demo/`: the static, read-only demo of the app (takepho.com/demo, linked from the header's "Live demo" nav link, the home page's "Open the live demo" buttons in the hero, mid-page CTA and closing CTA, and every home-page screenshot link and caption): the app's frontend built in demo mode plus a JSON/image snapshot of its API for the made-up sample library (photos from Wikimedia Commons, credited in the app). Generated, do not edit by hand: rebuild it from the app repo with `scripts/run_python.sh scripts/build_demo.py --out ../takepho.com/demo` (it replaces the folder's contents).
- `og-image.png`: 1200×630 social/OG image (logo + "Takeout Photo" + tagline on the indigo→violet gradient), referenced by the `og:image` / `twitter:image` tags on every page.

## Pages

- `index.html`: home, built around one route: photos come in (Google Takeout + Apple Photos), become trips, become albums, get backed up. Its own styles are in `home.css` (loaded after `style.css`, home page only: `<body class="home">`, `h-`-prefixed classes); shared header, buttons, plans, price table, platforms, FAQ and footer stay in `style.css`. Sections: a dusk-indigo hero (headline "Find every trip in your photos, and keep each one as an album.", lead naming Google Takeout + Apple Photos (Mac) + albums in Apple Photos and Proton Photos, the demo as the amber primary button plus "Download for Mac" / "Download for Windows", a note with Lite and the other platforms) and under it the journey graphic: "Google Takeout + Apple Photos library" chips, then an amber dashed route (inline SVG, drawn once on load with the prints landing on it; no motion under `prefers-reduced-motion`) with four trip stops from the sample library (Lisbon, Italy, Barcelona, Paris: three photo prints each from `img/trips/`, dates, photo count, and an "Apple Photos album" / "Proton Photos album" row each; on phones the route scrolls sideways). Then a four-step nav (1 Bring in your photos `#sources`, 2 Explore your trips `#trips`, 3 Turn trips into albums `#albums`, 4 Back them up `#backup`) and the four numbered chapters, joined by the dashed route in the left gutter: `#sources` (Takeout and Apple Photos columns, the "Each moment once" cross-source dedup figure), `#trips` (old anchor `#apps` kept; the timeline screenshot full width, map / trip day-by-day feature rows, the activities row `#activities`, three short facts), `#albums` (the two album layouts "As in your Takeout" / "Trip albums" and a table of the sample trip albums named as the app names them, e.g. "Holiday Lisbon, Portugal – August 2024", ticked for Apple Photos (teal) and Proton Photos (violet)), `#backup` (Apple Photos and Proton Photos `#proton` columns in their app colours, plus shared facts). Then a mid-page CTA band, the `#pricing` section (Lite free card, then Lifetime / Yearly plan cards with bottom-aligned download buttons and "Buy in the app: Settings → Account" notes, regional prices table — the Yearly plan is full price for the first year, then renews automatically at 50% off: USD 25 → USD 12.50/year, EUR 20 → EUR 10, GBP 20 → GBP 10, CHF 20 → CHF 10; buy inside the app; no payment-processor wording; Lite includes one import of the 500 most recent Apple Photos), `#platforms` (Mac — the only one that works with Apple Photos —, Windows with the portable zip and a link to the first-launch-warning FAQ item, NAS linking `/self-host/`) with the `#privacy` mini-grid, "Coming next", FAQ (27 items), a dusk closing CTA band, and a collapsed "Photo credits" list (Wikimedia Commons author + licence for every photo in `img/trips/`). A small inline script at the end of `<body>` adds `os-mac` / `os-win` / `os-mobile` to `<html>` from the user agent and touch points, and CSS then hides the non-matching download button in the hero, mid-page CTA and closing CTA (with an "Also for …" link in the hero note), or on phones hides both downloads and shows a "Send the link to my computer" share button (sharing `https://takepho.com/?from=phone#download`) plus a "desktop app" note. Named click tracking via `data-analiza-click` on nav, hero, steps, screenshots, mid CTA, platforms, plan cards, FAQ links, closing CTA and footer links. The header is sticky with nav links Trips/Albums/Backup/Pricing/FAQ/Live demo/Download (the three section links hide below 900 px, and below 480 px only Live demo + Download stay). JSON-LD `@graph` with Organization/WebSite/SoftwareApplication (macOS + Windows + Docker, `downloadUrl` = the Mac DMG, three `Offer`s: Lite free, Lifetime, Yearly) and a FAQPage mirroring the visible FAQ 1:1.
- `google-photos-takeout/index.html`: guide/landing page for "google photos takeout" (Takeout viewer: what a Takeout contains, JSON sidecars, in-place reading, trips/places/maps/Overview, how to export); hero CTA links the Mac and Windows downloads, the demo deep-linked to `/demo/#/timeline` and `/#pricing`; linked screenshots from `img/apps/` (the Italy trip page and the Overview page).
- `google-photos-strava/index.html`: guide/landing page for "google photos strava" (photos matched to your Strava, Komoot and Garmin Connect activities along the GPS track, the routes map with heatmap and the per-year Stats; the page stays Strava-focused because of the URL, and says Komoot and Garmin Connect work the same way); demo deep-linked to `/demo/#/activities/1`, screenshots of the activity page and the activities map.
- `google-photos-to-proton-photos/index.html`: guide/landing page for "google photos proton import" (moving the Takeout to Proton Photos with albums and metadata; pause/resume, a sync never deletes anything in your Proton account, Revert sync); demo deep-linked to `/demo/#/sync/albums`, with the sync albums screenshot.
- `self-host/index.html`: NAS self-hosting guide (Docker Compose): requirements, compose file, folders, security, updating. Linked from the home hero note, platforms section and footers; listed in `sitemap.xml`. The body between `<!-- self-hosting:begin -->` / `<!-- self-hosting:end -->` is generated from the app repo, do not edit it.
- `privacy.html`, `terms.html`, `404.html`: legal pages (404 is `noindex`). Privacy has an "Account and purchases (account.takepho.com)" section (data stored, purposes/legal bases, retention, processors, rights, account deletion) and a "This website" section describing the cookieless page-view and click counting; terms has the licence terms (personal licence per account, 2 devices (Mac or Windows), Lifetime/Yearly, Link/Stripe as seller of record at checkout).

All pages share the home header nav (Trips `/#trips`, Albums `/#albums`, Backup `/#backup`, Pricing `/#pricing`, FAQ `/#faq`, Live demo, Download; root-relative) and the same footer. Click tracking: the analiza script records outbound links and file downloads automatically, and same-site links/buttons only when they carry `data-analiza-click="name"`; names are `area-action` with the prefixes `nav-`, `hero-`, `steps-`, `shot-`, `mid-`, `plan-`, `platform-`, `final-`, `footer-`, `more-`, `faq-` on the home page and `guide-<slug>-…` (`takeout`, `strava`, `proton`) on the guide pages (e.g. `nav-download`, `nav-pricing`, `hero-send-link`, `shot-trip`, `plan-lifetime-cta`, `faq-demo`, `guide-takeout-shot-trip`, `guide-strava-related`, `footer-guide-proton`); the `*-cta` names and `nav-download` only jump to the download buttons, while real downloads are `*-download-mac`, `*-download-win` and `*-portable-zip`; the app repo's demo banner uses `demo-banner-download`.

## Support issues

The app's in-app **Support** link opens `https://github.com/ecyshor/takepho.com/issues/new`. `.github/ISSUE_TEMPLATE/support.yml` is the only issue form (blank issues are disabled in `config.yml`): it requires where the app runs (Mac app / web demo / other), the app version, the affected area, what happened, steps to reproduce and the expected result, and asks for logs (`~/Library/Logs/TakeoutPhoto/desktop.log`) and screenshots, with a reminder to redact personal data since the repo is public. Issues get the `question` label.

## Crawl / SEO / AI-search files (repo root)

- `robots.txt`: allows all crawlers (including the AI ones: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot/-User/-SearchBot, anthropic-ai, PerplexityBot/-User, Google-Extended, Applebot-Extended, CCBot, Bingbot), disallows only `/demo/data/`, points at the sitemap.
- `sitemap.xml`: all public pages with `<lastmod>`.
- `llms.txt`: llmstxt.org-format summary of the product with the Mac and Windows download links, the NAS option, pricing (plans, regional prices), links to the pages, status, privacy, contact, and the releases repo.
- `llms-full.txt`: plain-markdown content of the home page and the three guide pages, for LLM consumption without HTML.
- `og-image.png`: see above.
- `scripts/screenshots.py`: serves the repo root locally and uses headless Chromium (Playwright, from the nix dev shell) to capture the demo app views into `img/apps/*.webp` (`apps` mode, optionally only named views: `apps photos ...`) or home-page verification screenshots at 1440/375 px, light and dark (`landing --out <dir>` mode). Per-view framing: `photos.webp` from the top of the trip page, `activities-map.webp` with the map zoomed to the Rome evening ride route and pixel-verified.

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
