# ytclip Deployment Guide

## Architecture

```
CF Pages (static UI)          Replit (API server)        CF R2 (storage)
┌─────────────────┐          ┌──────────────────┐       ┌────────────────┐
│ ytclip.dev      │          │                  │       │                │
│ Paste URL       │────────→│ yt-dlp download  │──────→│ Clip.mp4       │
│ Set timestamps  │  fetch  │ ffmpeg trim      │ upload│ (ytclip.dev/x) │
│ Get clip        │←────────│ Upload to R2     │──────→│                │
└─────────────────┘  URL    └──────────────────┘       └────────────────┘
     free                  free (cold starts)              free
```

---

## Step 1: Cloudflare R2 Setup

1. Go to https://dash.cloudflare.com/
2. Navigate to **R2** (left sidebar)
3. Click **Create bucket** → name it `ytclip-clips`
4. **Public access:** Enable
5. **Custom domain:** Add `cdn.ytclip.dev` (optional but recommended)
6. In bucket settings, note:
   - Account ID
   - Access Key ID
   - Secret Access Key

---

## Step 2: Deploy Replit API

1. Go to https://replit.com/
2. Click **+ Create Repl**
3. Select **Python** template
4. Copy files from `/home/hermes/yt-clipper/replit/`:
   - `app.py`
   - `.replit`
5. Add dependencies via Replit's Packages tab:
   - `flask`
   - `yt-dlp`
   - `boto3` (for R2 upload)
6. Set environment variables (in Replit's Secrets tab):
   ```
   R2_BUCKET=ytclip-clips
   R2_ACCOUNT_ID=<your-account-id>
   R2_ACCESS_KEY_ID=<your-access-key-id>
   R2_SECRET_ACCESS_KEY=<your-secret-access-key>
   R2_PUBLIC_URL=https://cdn.ytclip.dev
   ```
7. Run the Repl — note the URL (e.g., `https://ytclip-api.johnny9615.repl.co`)

---

## Step 3: Deploy CF Pages

1. Go to https://dash.cloudflare.com/
2. Navigate to **Workers & Pages**
3. Click **Create application** → **Pages**
4. Choose **Direct Upload**
5. Upload the static UI from `/home/hermes/yt-clipper/static/`
6. Name: `ytclip`
7. Custom domain: `ytclip.dev` (add in domain settings)

---

## Step 4: Update Static UI

Edit `/home/hermes/yt-clipper/static/index.html`:
```javascript
const API = 'https://YOUR_REPL_NAME.YOUR_USERNAME.repl.co';
```

Replace with your actual Replit URL.

---

## Step 5: Test

1. Visit https://ytclip.dev
2. Paste a YouTube URL
3. Set timestamps (0:10 to 0:30 for a 30s clip)
4. Click "Download Clip"
5. Wait for processing → download starts

---

## Step 6: Configure Custom Domain (Optional)

In R2 bucket settings:
1. Go to **Settings** → **Custom Domains**
2. Add `cdn.ytclip.dev`
3. Add CNAME in your DNS provider:
   - Name: `cdn`
   - Target: `cdn.ytclip.dev.r2.cloudflarestorage.com`

---

## Cost Breakdown

| Service | Free Tier |
|---------|-----------|
| Cloudflare Pages | Unlimited bandwidth, 100k requests/day |
| Cloudflare R2 | 10GB storage, unlimited egress |
| Replit | 500MB disk, 0.5 vCPU, 512MB RAM |
| **Total** | **₹0/month** |

---

## Maintenance

**Update yt-dlp (YouTube breaks it sometimes):**
```bash
# In Replit console:
pip install -U yt-dlp
```

**Replit free tier sleeps after 30min idle.** When you visit the site, the API takes ~10s to wake up. For a paid "Always On" repl, it's $7/month.

---

## Troubleshooting

**API offline on first load:**
- Replit is waking up from sleep. Wait 30s, retry.

**Download fails:**
- Check Replit console for yt-dlp errors
- YouTube may have changed — update yt-dlp

**R2 upload fails:**
- Verify R2 credentials in Replit secrets
- Check bucket is public
