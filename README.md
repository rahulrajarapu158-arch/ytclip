# ytclip — YouTube Clipper

**Free YouTube clipper.** This is open source code — not a hosted service.

Fork it, run it locally, modify it, deploy it yourself. No uptime guarantees.

---

## Quick Start (Local)

```bash
git clone https://github.com/rahulrajarapu158-arch/ytclip.git
cd ytclip
bash setup.sh
# → http://localhost:5000
```

Or manually:

```bash
pip install flask yt-dlp
python3 -m web.app
# → http://localhost:5000
```

---

## How it works

```
Paste URL → Set timestamps → Download clip
```

The Flask app uses yt-dlp + ffmpeg to download and trim YouTube videos.

---

## Project Structure

```
ytclip/
├── web/app.py              # Flask backend
├── cf-worker/worker.js     # Cloudflare Worker (optional)
├── cf-frontend/index.html  # Static UI (optional)
├── .github/workflows/      # GitHub Actions (optional)
├── setup.sh                # One-command local setup
├── README.md
├── LICENSE
└── pyproject.toml
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend |
| POST | `/api/info` | Get video metadata |
| POST | `/api/process` | Download + trim + transcript |
| POST | `/api/multi-process` | Multiple clips at once |
| GET | `/api/file/:filename` | Download a file |

---

## Requirements

- Python 3.9+
- ffmpeg
- yt-dlp
- Flask

---

## Deploy Your Own

### Cloudflare + GitHub Actions (free tier)

1. Fork this repo
2. Create Cloudflare KV namespace: `wrangler kv:namespace create YTCLIP_KV`
3. Add GitHub Actions secrets (see `cf-worker/wrangler.toml`)
4. Deploy Worker: `cd cf-worker && wrangler deploy`
5. Deploy frontend: `cd cf-frontend && wrangler pages deploy .`

### VPS

```bash
# On any VPS with Python + ffmpeg
pip install -r requirements.txt
python3 -m web.app
# Bind to 0.0.0.0 for public access
```

### Hugging Face Spaces

Create a Docker Space with the Flask app. Add yt-dlp + ffmpeg to the Dockerfile.

---

## Limitations

- YouTube may rate-limit or block requests
- Processing time depends on video length and quality
- No background job queue in local mode (request stays open during processing)

---

## Contributing

Issues and PRs welcome. This is a code dump — not a maintained project — but fixes and improvements are fine.

---

## License

MIT — do whatever you want.

---

## Author

Rahul Rajarapu — [rahulrajarapu158-arch](https://github.com/rahulrajarapu158-arch)
