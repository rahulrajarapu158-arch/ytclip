# ytclip — Cloudflare + GitHub Actions Hybrid

**Free YouTube clipper.** No server to manage. No bills.

## Architecture

```
Browser → Cloudflare Pages (static UI)
              ↓
         Cloudflare Worker (API + KV job queue)
              ↓
         GitHub Actions (yt-dlp + ffmpeg + R2 upload)
              ↓
         Cloudflare R2 (clip storage)
              ↓
         User downloads from R2
```

## What's free

| Service | Free tier |
|---------|-----------|
| Cloudflare Pages | Unlimited bandwidth, 500 builds/mo |
| Cloudflare Worker | 100K requests/day |
| Cloudflare KV | 100K reads/day, 1K writes/day |
| Cloudflare R2 | 10GB storage, zero egress |
| GitHub Actions | 2000 min/month |

## Setup

### 1. Cloudflare

1. Sign up at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Create a KV namespace:
   ```bash
   wrangler kv:namespace create YTCLIP_KV
   wrangler kv:namespace create YTCLIP_KV --preview
   ```
3. Create an R2 bucket:
   ```bash
   wrangler r2 bucket create ytclip-clips
   wrangler r2 bucket create ytclip-clips-preview
   ```
4. Get R2 credentials (Access Key + Secret Key) from R2 dashboard
5. Enable public access on the bucket (for clip downloads)

### 2. GitHub

1. Fork this repo: `rahulrajarapu158-arch/ytclip`
2. Add these **Repository Secrets** (Settings → Secrets → Actions):
   - `R2_BUCKET` — bucket name (e.g., `ytclip-clips`)
   - `R2_ACCESS_KEY` — from R2 dashboard
   - `R2_SECRET_KEY` — from R2 dashboard
   - `R2_ENDPOINT` — `https://<account_id>.r2.cloudflarestorage.com`
   - `R2_PUBLIC_URL` — `https://pub-<bucket_id>.r2.dev`
   - `WORKER_URL` — `https://ytclip-worker.<subdomain>.workers.dev`
   - `WEBHOOK_SECRET` — any random string

### 3. Deploy Worker

```bash
cd cf-worker
wrangler deploy
```

### 4. Deploy Frontend

```bash
cd cf-frontend
wrangler pages deploy .
# Or connect to GitHub for auto-deploy on push
```

### 5. Test

1. Open your Pages URL
2. Paste a YouTube URL
3. Set timestamps
4. Click "Process Clip"
5. Wait 2-5 minutes
6. Download the clip

## How it works

1. **User submits** → Worker creates job in KV, returns `job_id`
2. **Worker triggers** GitHub Actions via `workflow_dispatch` API
3. **GitHub Actions** runs yt-dlp + ffmpeg on a real runner
4. **Finished clip** uploaded to R2
5. **Webhook** sent back to Worker with clip URL
6. **User polls** Worker for status, gets download URL

## Limitations

- **2-5 min delay** per clip (GitHub Actions cold start + processing)
- **~660 clips/month** max (GitHub Actions free tier)
- **10GB storage** on R2 free tier (~200 clips at 50MB each)
- **Queue limit** — 1 job per workflow_dispatch trigger

## Local daemon (optional)

For instant processing, run the local daemon:

```bash
cd yt-clipper
python3 -m web.app
# → http://localhost:5000
```

The local daemon uses your own hardware — no queue, no delay.

## License

MIT
