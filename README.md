# ytclip

**ytclip** is a free and open-source CLI tool for downloading, trimming, and extracting transcripts from YouTube videos.

## Features

- Download any YouTube video at configurable quality (480p default, up to 4K)
- Trim videos by timestamps (`--start 1:30 --end 4:20`)
- Extract auto-generated or manual transcripts (SRT/VTT/text)
- Batch processing from a list of URLs
- Clean, colorful CLI output

## Install

```bash
pip install ytclip
```

Or from source:

```bash
git clone https://github.com/rahulrajarapu158-arch/ytclip.git
cd ytclip
pip install -e .
```

## Quick Start

```bash
# Download a video (480p by default)
ytclip download "https://youtube.com/watch?v=..."

# Download and trim
ytclip cut "https://youtube.com/watch?v=..." --start 1:30 --end 4:20

# Get transcript
ytclip transcript "https://youtube.com/watch?v=..."

# All in one
ytclip process "https://youtube.com/watch?v=..." --start 0:10 --end 2:30 --transmit
```

## Pricing

| Tier | Quality | Transcript | Cost |
|------|---------|------------|------|
| Free | 480p | Yes | Free |
| Pro | 1080p, 4K | Yes + translation | API key required |

The CLI tool is free and open source forever. High-resolution downloads require a paid API key to cover bandwidth costs.

## API Keys

For Pro tier:

```bash
ytclip config --api-key YOUR_KEY
```

Get your key at https://ytclip.dev/pricing

## License

AGPL-3.0 — free for personal and non-commercial use. Commercial use requires a license.
