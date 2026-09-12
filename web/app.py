"""ytclip web app - Flask backend"""
import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file, render_template
from ytclip import download_video, trim_video, get_transcript, get_video_id

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

OUTPUT_DIR = os.path.join(tempfile.gettempdir(), 'ytclip_web')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_video_duration(url):
    """Get video duration in seconds using yt-dlp"""
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration', 0)
    except Exception:
        return 0


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def api_info():
    """Get video metadata"""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    # Fetch duration using yt-dlp
    duration = get_video_duration(url)
    
    return jsonify({
        'video_id': video_id,
        'embed_url': f'https://www.youtube.com/embed/{video_id}',
        'watch_url': f'https://www.youtube.com/watch?v={video_id}',
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
        'duration': duration
    })


@app.route('/api/download', methods=['POST'])
def api_download():
    """Download video"""
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '480')
    api_key = data.get('api_key')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    output = os.path.join(OUTPUT_DIR, f"{video_id}_{quality}.mp4")
    
    if os.path.exists(output):
        return jsonify({'video_id': video_id, 'status': 'cached', 'file': os.path.basename(output)})
    
    success = download_video(url, output, quality=quality, api_key=api_key)
    if success:
        return jsonify({'video_id': video_id, 'status': 'downloaded', 'file': os.path.basename(output)})
    return jsonify({'error': 'Download failed'}), 500


@app.route('/api/trim', methods=['POST'])
def api_trim():
    """Trim video"""
    data = request.json
    url = data.get('url')
    start = data.get('start')
    end = data.get('end')
    quality = data.get('quality', '480')
    api_key = data.get('api_key')
    
    if not all([url, start, end]):
        return jsonify({'error': 'URL, start, and end required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    base_name = f"{video_id}_{quality}_{start.replace(':', '-')}_{end.replace(':', '-')}"
    output = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")
    
    if os.path.exists(output):
        return jsonify({'status': 'cached', 'file': os.path.basename(output), 'video_id': video_id})
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_video = os.path.join(tmpdir, "video.mp4")
        if not download_video(url, temp_video, quality=quality, api_key=api_key):
            return jsonify({'error': 'Download failed'}), 500
        
        success = trim_video(temp_video, output, start, end)
        if success:
            return jsonify({'status': 'trimmed', 'file': os.path.basename(output), 'video_id': video_id})
    
    return jsonify({'error': 'Trim failed'}), 500


@app.route('/api/cut', methods=['POST'])
def api_cut():
    """Cut video (alias for trim)"""
    return api_trim()


@app.route('/api/transcript', methods=['POST'])
def api_transcript():
    """Get transcript"""
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'text')
    lang = data.get('lang', 'en')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    transcript = get_transcript(url, fmt, lang)
    if transcript:
        return jsonify({'transcript': transcript, 'format': fmt})
    return jsonify({'error': 'No transcript found'}), 404


@app.route('/api/process', methods=['POST'])
def api_process():
    """Full process: download + trim + transcript"""
    data = request.json
    url = data.get('url')
    start = data.get('start')
    end = data.get('end')
    quality = data.get('quality', '480')
    fmt = data.get('format', 'text')
    lang = data.get('lang', 'en')
    api_key = data.get('api_key')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    base_name = f"{video_id}_{quality}_{start.replace(':', '-')}_{end.replace(':', '-')}"
    output = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")
    transcript_file = os.path.join(OUTPUT_DIR, f"{base_name}.{fmt}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_video = os.path.join(tmpdir, "video.mp4")
        if not download_video(url, temp_video, quality=quality, api_key=api_key):
            return jsonify({'error': 'Download failed'}), 500
        
        if start and end:
            if not trim_video(temp_video, output, start, end):
                return jsonify({'error': 'Trim failed'}), 500
        else:
            import shutil
            shutil.copy2(temp_video, output)
    
    transcript = get_transcript(url, fmt, lang)
    if transcript:
        with open(transcript_file, 'w') as f:
            f.write(transcript)
    
    # Get file size
    file_size_bytes = os.path.getsize(output)
    file_size = f"{file_size_bytes / 1024 / 1024:.1f} MB" if file_size_bytes > 1024*1024 else f"{file_size_bytes / 1024:.0f} KB"

    return jsonify({
        'status': 'done',
        'file': os.path.basename(output),
        'transcript_file': os.path.basename(transcript_file) if transcript_file else None,
        'video_id': video_id,
        'transcript': transcript,
        'file_size': file_size
    })


@app.route('/api/file/<path:filename>')
def serve_file(filename):
    """Serve any file"""
    if not os.path.isabs(filename):
        filepath = os.path.join(OUTPUT_DIR, filename)
    else:
        filepath = filename
    return send_file(filepath)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
