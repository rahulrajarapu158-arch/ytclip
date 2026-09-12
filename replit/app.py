#!/usr/bin/env python3
"""ytclip API - Runs on Replit, uploads clips to CF R2"""
import os
import subprocess
import tempfile
import uuid
import re
from flask import Flask, request, jsonify
from urllib.parse import urlparse

# Try boto3 (for R2 upload), optional if not installed
try:
    import boto3
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

app = Flask(__name__)

# R2 config from environment
R2_BUCKET = os.environ.get('R2_BUCKET', 'ytclip-clips')
R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', 'https://cdn.ytclip.dev')

VALID_QUALITIES = ['480', '720', '1080']

def validate_youtube_url(url):
    """Check if valid YouTube URL"""
    patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
    ]
    return any(re.match(p, url) for p in patterns)

def get_video_id(url):
    match = re.search(r'(?:v=|shorts/|youtu\.be/)([\w-]+)', url)
    return match.group(1) if match else None

def parse_timestamp(ts):
    parts = str(ts).split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return 0

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'version': '0.1.0'})

@app.route('/api/info', methods=['POST'])
def api_info():
    data = request.json
    url = data.get('url')
    if not validate_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'video_id': get_video_id(url),
                'duration': info.get('duration', 0),
                'title': info.get('title', ''),
                'thumbnail': info.get('thumbnail', ''),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def api_process():
    """Download section, trim, upload to R2, return download URL"""
    data = request.json
    url = data.get('url')
    start = data.get('start', '0:00')
    end = data.get('end')
    quality = data.get('quality', '480')
    
    if not validate_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    if not end:
        return jsonify({'error': 'End timestamp required'}), 400
    if quality not in VALID_QUALITIES:
        return jsonify({'error': f'Quality must be one of {VALID_QUALITIES}'}), 400
    
    start_secs = parse_timestamp(start)
    end_secs = parse_timestamp(end)
    duration = end_secs - start_secs
    
    if duration <= 0:
        return jsonify({'error': 'End time must be after start time'}), 400
    if duration > 600:
        return jsonify({'error': 'Max clip length is 10 minutes'}), 400
    
    video_id = get_video_id(url)
    clip_id = str(uuid.uuid4())[:8]
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Download full video (yt-dlp doesn't support section downloads on YouTube)
            temp_video = os.path.join(tmpdir, 'video.%(ext)s')
            
            quality_map = {
                '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
                '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            }
            
            import yt_dlp
            ydl_opts = {
                'format': quality_map[quality],
                'outtmpl': temp_video,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find downloaded file
            downloaded = None
            for f in os.listdir(tmpdir):
                if f.startswith('video.'):
                    downloaded = os.path.join(tmpdir, f)
                    break
            
            if not downloaded:
                return jsonify({'error': 'Download failed'}), 500
            
            # Trim with ffmpeg
            output_filename = f"{video_id}_{clip_id}_{quality}.mp4"
            output_path = os.path.join(tmpdir, output_filename)
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_secs),
                '-i', downloaded,
                '-t', str(duration),
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                '-c:a', 'aac', '-b:a', '96k',
                '-avoid_negative_ts', 'make_zero',
                '-movflags', '+faststart',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return jsonify({'error': f'FFmpeg error: {result.stderr[-200:]}'}), 500
            
            # Upload to R2
            if HAS_BOTO and R2_ACCOUNT_ID:
                r2 = boto3.client(
                    's3',
                    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                )
                
                extra_args = {
                    'ContentType': 'video/mp4',
                    'ACL': 'public-read',
                }
                
                r2.upload_file(
                    output_path,
                    R2_BUCKET,
                    output_filename,
                    ExtraArgs=extra_args,
                )
                
                download_url = f"{R2_PUBLIC_URL}/{output_filename}"
            else:
                # Fallback: serve directly (for testing)
                # Save to /tmp for Flask to serve
                fallback_path = f"/tmp/{output_filename}"
                import shutil
                shutil.copy(output_path, fallback_path)
                download_url = f"/tmp/{output_filename}"
            
            file_size = os.path.getsize(output_path)
            size_str = f"{file_size / 1024 / 1024:.1f} MB"
            
            return jsonify({
                'status': 'done',
                'download_url': download_url,
                'quality': quality,
                'duration': f"{int(duration)}s",
                'size': size_str,
                'title': video_id,
            })
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Processing timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tmp/<filename>')
def serve_fallback(filename):
    """For testing without R2"""
    return app.send_from_directory('/tmp', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
