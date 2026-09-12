#!/bin/bash
# pre_build.sh - runs before pip install on HF Spaces
# Downloads yt-dlp standalone binary and ffmpeg static build

set -e

echo "Downloading yt-dlp..."
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod a+rx /usr/local/bin/yt-dlp

echo "Downloading ffmpeg static build..."
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz
cd /tmp
tar -xf ffmpeg.tar.xz
cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/
cp ffmpeg-*-amd64-static/ffprobe /usr/local/bin/
chmod a+rx /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
rm -rf ffmpeg.tar.xz ffmpeg-*-amd64-static

echo "Done! yt-dlp and ffmpeg installed."
