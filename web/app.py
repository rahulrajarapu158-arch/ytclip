"""ytclip web app - Flask backend"""
import os
import tempfile
from flask import Flask, request, jsonify, send_file, render_template
from ytclip import download_video, trim_video, get_transcript, get_video_id, parse_timestamp

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Use /data for persistent storage on HF Spaces, else temp
if os.path.exists('/data'):
    OUTPUT_DIR = '/data/ytclip_web'
else:
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
    fmt = data.get('format', 'mp4')
    api_key = data.get('api_key')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    output = os.path.join(OUTPUT_DIR, f"{video_id}_{quality}.{fmt}")
    
    if os.path.exists(output):
        return jsonify({'video_id': video_id, 'status': 'cached', 'file': os.path.basename(output), 'format': fmt})
    
    success = download_video(url, output, quality=quality, api_key=api_key, fmt=fmt)
    if success:
        return jsonify({'video_id': video_id, 'status': 'downloaded', 'file': os.path.basename(output), 'format': fmt})
    return jsonify({'error': 'Download failed'}), 500


@app.route('/api/trim', methods=['POST'])
def api_trim():
    """Trim video by downloading only the section"""
    data = request.json
    url = data.get('url')
    start = data.get('start')
    end = data.get('end')
    quality = data.get('quality', '480')
    fmt = data.get('format', 'mp4')
    api_key = data.get('api_key')
    
    if not all([url, start, end]):
        return jsonify({'error': 'URL, start, and end required'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    base_name = f"{video_id}_{quality}_{start.replace(':', '-')}_{end.replace(':', '-')}"
    output = os.path.join(OUTPUT_DIR, f"{base_name}.{fmt}")
    
    if os.path.exists(output):
        return jsonify({'status': 'cached', 'file': os.path.basename(output), 'video_id': video_id, 'format': fmt})
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_video = os.path.join(tmpdir, "video.mp4")
        # Download only the section
        if not download_video(url, temp_video, quality=quality, api_key=api_key, fmt=fmt, start=start, end=end):
            return jsonify({'error': 'Download failed'}), 500
        
        import shutil
        shutil.copy2(temp_video, output)
    
    return jsonify({'status': 'trimmed', 'file': os.path.basename(output), 'video_id': video_id, 'format': fmt})


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
    try:
        data = request.json
        url = data.get('url')
        start = data.get('start')
        end = data.get('end')
        quality = data.get('quality', '480')
        fmt = data.get('format', 'mp4')
        transcript_fmt = data.get('transcript_format', 'text')
        lang = data.get('lang', 'en')
        api_key = data.get('api_key')
        
        if not url:
            return jsonify({'error': 'URL required'}), 400
        
        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Get video duration and clamp timestamps
        duration = get_video_duration(url)
        start_secs = parse_timestamp(start) if start else 0
        end_secs = parse_timestamp(end) if end else duration
        
        # Clamp to video duration
        if start_secs >= duration:
            mins = int(duration) // 60
            secs = int(duration) % 60
            return jsonify({'error': f'Start time {start} exceeds video duration {mins}:{secs:02d}'}), 400
        if end_secs > duration:
            end_secs = duration
            end = f"{int(duration)//60}:{int(duration)%60:02d}"
        if start_secs >= end_secs:
            return jsonify({'error': f'Start time {start} must be before end time {end}'}), 400
        
        base_name = f"{video_id}_{quality}_{start.replace(':', '-')}_{end.replace(':', '-')}"
        output = os.path.join(OUTPUT_DIR, f"{base_name}.{fmt}")
        transcript_file = os.path.join(OUTPUT_DIR, f"{base_name}.{transcript_fmt}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_video = os.path.join(tmpdir, "video.mp4")
            # Download only the section we need
            if not download_video(url, temp_video, quality=quality, api_key=api_key, fmt=fmt, start=start, end=end):
                return jsonify({'error': 'Download failed'}), 500
            
            # No trim needed - already downloaded only the section
            import shutil
            shutil.copy2(temp_video, output)
        
        transcript = get_transcript(url, transcript_fmt, lang)
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
            'file_size': file_size,
            'format': fmt
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/multi-process', methods=['POST'])
def api_multi_process():
    """Download each clip's section separately, no full download needed"""
    try:
        data = request.json
        url = data.get('url')
        clips = data.get('clips', [])
        quality = data.get('quality', '480')
        fmt = data.get('format', 'mp4')
        transcript_fmt = data.get('transcript_format', 'text')
        lang = data.get('lang', 'en')
        api_key = data.get('api_key')
        
        if not url:
            return jsonify({'error': 'URL required'}), 400
        if not clips:
            return jsonify({'error': 'No clips provided'}), 400
        
        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        results = []
        
        for i, clip in enumerate(clips):
            start = clip.get('start', '0:00')
            end = clip.get('end', '0:00')
            
            base_name = f"{video_id}_{quality}_{start.replace(':', '-')}_{end.replace(':', '-')}"
            output = os.path.join(OUTPUT_DIR, f"{base_name}.{fmt}")
            
            # Download only this clip's section
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_video = os.path.join(tmpdir, "video.mp4")
                if not download_video(url, temp_video, quality=quality, api_key=api_key, fmt=fmt, start=start, end=end):
                    results.append({'index': i + 1, 'error': 'Download failed'})
                    continue
                
                import shutil
                shutil.copy2(temp_video, output)
            
            # Get file size
            file_size_bytes = os.path.getsize(output)
            file_size = f"{file_size_bytes / 1024 / 1024:.1f} MB" if file_size_bytes > 1024*1024 else f"{file_size_bytes / 1024:.0f} KB"
            
            results.append({
                'index': i + 1,
                'status': 'done',
                'file': os.path.basename(output),
                'file_size': file_size,
                'format': fmt,
                'start': start,
                'end': end
            })
        
        # Get transcript once
        transcript = None
        if transcript_fmt != 'none':
            transcript = get_transcript(url, transcript_fmt, lang)
            if transcript:
                transcript_file = os.path.join(OUTPUT_DIR, f"{video_id}_{quality}_transcript.{transcript_fmt}")
                with open(transcript_file, 'w') as f:
                    f.write(transcript)
        
        return jsonify({
            'status': 'done',
            'video_id': video_id,
            'results': results,
            'transcript': transcript
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/<path:filename>')
def serve_file(filename):
    """Serve any file"""
    if not os.path.isabs(filename):
        filepath = os.path.join(OUTPUT_DIR, filename)
    else:
        filepath = filename
    return send_file(filepath)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
