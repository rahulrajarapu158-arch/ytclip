---
title: ytclip
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
---

# ytclip

Download YouTube clips by timestamps, free and open source.

## Features

- Paste a YouTube URL, set start/end timestamps
- Download just the section you need
- Choose quality: 480p (free) / 720p / 1080p
- Extract transcripts (SRT/VTT/text)
- Batch processing (multiple clips at once)

## Usage

1. Paste a YouTube URL
2. Use the range slider or type timestamps
3. Click "Download Clip"
4. Wait for processing — download starts automatically

## CLI

```bash
pip install ytclip

ytclip cut "https://youtube.com/watch?v=..." --start 1:30 --end 4:20
ytclip process "https://youtube.com/watch?v=..." --start 0:10 --end 2:30 --transcript
```

## License

AGPL-3.0
