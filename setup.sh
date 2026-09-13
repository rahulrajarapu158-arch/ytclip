#!/bin/bash
# ytclip local setup — one command to run
set -e

echo "Setting up ytclip..."

# Check Python
python3 --version || { echo "Python 3 required"; exit 1; }

# Install dependencies if missing
pip3 install --quiet flask yt-dlp 2>/dev/null || pip install --quiet flask yt-dlp

# Check ffmpeg
ffmpeg -version 2>&1 | head -1 || { echo "Install ffmpeg: sudo apt install ffmpeg"; exit 1; }

# Create output dir
mkdir -p /tmp/ytclip_web

echo ""
echo "Starting ytclip..."
echo "→ http://localhost:5000"
echo ""

cd "$(dirname "$0")" && python3 -m web.app
