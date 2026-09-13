# ytclip — YouTube Clipper

**Free YouTube clipper.** Open source code — not a hosted service.

Fork it, run it locally, modify it. No accounts, no API keys, no server.

---

## Quick Start

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

## Requirements

- Python 3.9+
- ffmpeg
- yt-dlp
- Flask

---

## Project Structure

```
ytclip/
├── web/app.py              # Flask backend
├── src/ytclip/             # Core library
├── setup.sh                # One-command setup
├── requirements.txt        # Python deps
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

## How it works

```
Paste URL → Set timestamps → Download clip
```

yt-dlp downloads the video section. ffmpeg is available if needed for transcoding.

---

## Limitations

- YouTube may rate-limit or block requests
- Processing time depends on video length and quality
- No background job queue (request stays open during processing)

---

## Contributing

Issues and PRs welcome. This is a code dump — not a maintained project — but fixes and improvements are fine.

---

## License

MIT — do whatever you want.

---

## Author

Rahul Rajarapu — [rahulrajarapu158-arch](https://github.com/rahulrajarapu158-arch)
