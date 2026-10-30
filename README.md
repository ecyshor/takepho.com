# Takeout Photo Landing Page

This is the static website for Takeout Photo, hosted at [takepho.com](https://takepho.com).

## What is Takeout Photo?

Takeout Photo is a desktop app that turns your Google Takeout export into a private, browsable photo timeline of your life. Trips are detected automatically, places are named, the best shots are picked for you, and routes are drawn on a map. Everything runs on your own computer — your photos are never uploaded to our servers.

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
