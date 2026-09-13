# ytclip — Free YouTube Clipper

**Clip any YouTube video for free.** No signup, no server, no bills.

## How it works

```
You paste URL → Cloudflare Worker creates job → GitHub Actions processes clip → Download
```

| Layer | Service | Cost |
|-------|---------|------|
| Frontend | Cloudflare Pages | Free |
| API + Job Queue | Cloudflare Worker + KV | Free |
| Processing | GitHub Actions | Free (2000 min/mo) |
| Storage | Catbox.moe | Free (200MB/file) |

## Quick Start (Local)

```bash
# Clone
git clone https://github.com/rahulrajarapu158-arch/ytclip.git
cd ytclip

# Install dependencies
pip install flask yt-dlp

# Run
python3 -m web.app
# → http://localhost:5000
```

## Quick Start (Cloudflare + GitHub Actions)

### 1. Cloudflare Setup

```bash
# Install wrangler
npm install -g wrangler

# Login
wrangler login

# Create KV namespace
wrangler kv:namespace create YTCLIP_KV
```

### 2. GitHub Setup

1. Fork this repo
2. Go to **Settings → Secrets → Actions**
3. Add:
   - `WORKER_URL` — your Worker URL
   - `WEBHOOK_SECRET` — any random string
   - `GITHUB_TOKEN` — your PAT (auto-added if enabled)

### 3. Deploy Worker

```bash
cd cf-worker
wrangler deploy
```

### 4. Deploy Frontend

```bash
cd cf-frontend
wrangler pages deploy .
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/job` | Create clip job |
| GET | `/api/job/:id` | Check status |
| GET | `/api/jobs` | List all jobs |
| POST | `/api/webhook` | GH Actions callback |

## Job Lifecycle

```
pending → processing → done
                    → error
```

## Limitations

- **2-5 min delay** per clip (GitHub Actions cold start)
- **~660 clips/month** (GitHub Actions free tier)
- **200MB max** per clip (Catbox.moe limit)

## Author

**Rahul Rajarapu** — [rahulrajarapu158-arch](https://github.com/rahulrajarapu158-arch)

## License

MIT
