#!/usr/bin/env python3
"""ytclip - YouTube video downloader, trimmer, and transcript extractor"""

import argparse
import sys
import os
import re
import subprocess
import tempfile
import json
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp not installed. Run: pip install yt-dlp")
    sys.exit(1)

__version__ = "0.1.0"

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    print(f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════╗
║     ytclip v{__version__} - YouTube CLI      ║
║   Download · Trim · Transcript      ║
╚══════════════════════════════════════╝{Colors.END}""")

def validate_url(url):
    """Validate YouTube URL"""
    patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(www\.)?youtube\.com/embed/[\w-]+',
    ]
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

def get_video_id(url):
    """Extract video ID from URL"""
    patterns = [
        r'(?:v=|shorts/|embed/|youtu\.be/)([\w-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def parse_timestamp(ts):
    """Parse timestamp like 1:30 or 01:30:45 to seconds"""
    parts = ts.split(':')
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    else:
        raise ValueError(f"Invalid timestamp format: {ts}")

def download_video(url, output_path, quality="480", api_key=None, fmt="mp4", start=None, end=None):
    """Download video using yt-dlp, with optional section download via ffmpeg"""
    print(f"{Colors.BLUE}📥 Downloading video...{Colors.END}")
    
    quality_map = {
        "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "best": "bestvideo+bestaudio/best",
    }
    
    # For MP3, extract audio
    if fmt == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        if start and end:
            start_secs = parse_timestamp(start)
            end_secs = parse_timestamp(end)
            ydl_opts['postprocessors'][0]['preferredquality'] = '192'
            # For MP3 with section, we need to download full then extract section
            # yt-dlp doesn't support section download for audio extraction well
    else:
        ydl_opts = {
            'format': quality_map.get(quality, quality_map["480"]),
            'outtmpl': output_path,
            'merge_output_format': fmt,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['web', 'ios', 'android']}},
            'remote_components': {'ejs': 'github'},
        }
    
    # Pro tier check for high quality
    if quality in ["1080", "2160", "best"] and not api_key:
        print(f"{Colors.YELLOW}⚠️  {quality}p requires Pro tier API key{Colors.END}")
        print(f"{Colors.YELLOW}   Get key at: https://ytclip.dev/pricing{Colors.END}")
        print(f"{Colors.YELLOW}   Falling back to 480p (free tier){Colors.END}")
        ydl_opts['format'] = quality_map["480"]
    
    # YouTube DASH doesn't support --download-sections reliably, so for
    # section downloads we still pull the full stream then extract with ffmpeg.
    # For non-YouTube sites with direct video URLs, use _download_section_ffmpeg
    # which can do HTTP range requests for true partial downloads.
    if start and end and fmt != 'mp3':
        start_secs = parse_timestamp(start)
        end_secs = parse_timestamp(end)
        duration = end_secs - start_secs
        if duration <= 0:
            print(f"{Colors.RED}❌ Invalid section: {start} to {end}{Colors.END}")
            return False
        print(f"{Colors.CYAN}   Downloading section {start} to {end} ({duration:.1f}s)...{Colors.END}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_full = os.path.join(tmpdir, "full.%(ext)s")
            full_opts = dict(ydl_opts)
            full_opts['outtmpl'] = temp_full
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                ydl.download([url])
            
            downloaded = None
            for f in os.listdir(tmpdir):
                if f.startswith("full."):
                    downloaded = os.path.join(tmpdir, f)
                    break
            
            if not downloaded:
                print(f"{Colors.RED}❌ Download failed{Colors.END}")
                return False
            
            cmd = [
                'ffmpeg', '-y', '-ss', str(start_secs),
                '-i', downloaded, '-t', str(duration),
                '-c:v', 'copy', '-c:a', 'copy',
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"{Colors.GREEN}✅ Downloaded section: {duration:.1f}s{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}❌ Section extraction failed{Colors.END}")
                return False
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            duration = info.get('duration', 0)
            print(f"{Colors.GREEN}✅ Downloaded: {title} ({duration}s){Colors.END}")
            return True
    except Exception as e:
        print(f"{Colors.RED}❌ Download failed: {e}{Colors.END}")
        return False


def _download_section_ffmpeg(url, output_path, quality, start, end, fmt="mp4"):
    """Download only a specific section using ffmpeg with direct URLs"""
    import subprocess
    
    start_secs = parse_timestamp(start)
    end_secs = parse_timestamp(end)
    duration = end_secs - start_secs
    
    if duration <= 0:
        print(f"{Colors.RED}❌ Invalid section: {start} to {end}{Colors.END}")
        return False
    
    print(f"{Colors.CYAN}   Downloading section {start} to {end} ({duration:.1f}s)...{Colors.END}")
    
    quality_map = {
        "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "best": "bestvideo+bestaudio/best",
    }
    
    try:
        # Get direct download URLs
        ydl_opts = {
            'format': quality_map.get(quality, quality_map["480"]),
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Find video and audio URLs
            video_url = None
            audio_url = None
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    if quality in ["480", "720", "1080", "2160"]:
                        if f.get('height', 0) <= int(quality):
                            video_url = f.get('url')
                    else:
                        video_url = f.get('url')
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    audio_url = f.get('url')
            
            if not video_url:
                video_url = info.get('url')
            if not audio_url:
                audio_url = video_url
        
        # Use ffmpeg to download only the section
        # -ss BEFORE -i uses HTTP Range request to skip directly to position
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_secs),
            '-i', video_url,
        ]
        if audio_url and audio_url != video_url:
            cmd.extend(['-ss', str(start_secs), '-i', audio_url])
        
        cmd.extend([
            '-t', str(duration),
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart',
            output_path
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(30, int(duration * 3)))
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Downloaded section: {duration:.1f}s{Colors.END}")
            return True
        else:
            print(f"{Colors.YELLOW}⚠️  Section download failed, falling back to full download{Colors.END}")
            return download_video(url, output_path, quality=quality, fmt=fmt)
            
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Download timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Section download error: {e}{Colors.END}")
        return False

def trim_video(input_path, output_path, start_time, end_time):
    """Trim video using ffmpeg"""
    print(f"{Colors.BLUE}✂️  Trimming {start_time} to {end_time}...{Colors.END}")
    
    start_secs = parse_timestamp(start_time)
    end_secs = parse_timestamp(end_time)
    duration = end_secs - start_secs
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_secs),
        "-i", input_path,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Trimmed to {duration:.1f}s{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ Trim failed{Colors.END}")
            return False
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def get_transcript(url, output_format="text", lang="en"):
    """Extract transcript from video"""
    print(f"{Colors.BLUE}📝 Extracting transcript...{Colors.END}")
    
    ydl_opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'subtitleslangs': [lang],
        'subtitlesformat': 'srt/vtt/best',
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['web', 'ios', 'android']}},
        'remote_components': {'ejs': 'github'},
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get subtitles from info
            subtitles = info.get('subtitles', {})
            auto_captions = info.get('automatic_captions', {})
            
            # Try manual subs first, then auto
            subs_data = subtitles.get(lang) or auto_captions.get(lang)
            
            if not subs_data:
                print(f"{Colors.YELLOW}⚠️  No transcript found in '{lang}'{Colors.END}")
                return None
            
            # Find SRT or VTT format, skip JSON3
            sub_entry = None
            for sub in subs_data:
                if sub.get('ext') in ('srt', 'vtt'):
                    sub_entry = sub
                    break
            
            if not sub_entry:
                # Fall back to first available
                sub_entry = subs_data[0]
            
            # Download subtitle file
            sub_url = sub_entry['url']
            
            import urllib.request
            response = urllib.request.urlopen(sub_url)
            content = response.read().decode('utf-8')
            
            if output_format == "srt":
                return content  # Already SRT/VTT format
            elif output_format == "text":
                # Strip timestamps and return plain text
                lines = []
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line[0].isdigit() or '-->' in line:
                        continue
                    lines.append(line)
                return ' '.join(lines)
            else:
                return content
                
    except Exception as e:
        print(f"{Colors.RED}❌ Transcript error: {e}{Colors.END}")
        return None

def cmd_download(args):
    """Handle download command"""
    url = args.url
    if not validate_url(url):
        print(f"{Colors.RED}❌ Invalid YouTube URL{Colors.END}")
        return
    
    output = args.output or f"%(title)s_%(id)s.%(ext)s"
    
    download_video(url, output, quality=args.quality, api_key=args.api_key, fmt=args.format, start=getattr(args, 'start', None), end=getattr(args, 'end', None))

def cmd_cut(args):
    """Handle cut command"""
    url = args.url
    if not validate_url(url):
        print(f"{Colors.RED}❌ Invalid YouTube URL{Colors.END}")
        return
    
    fmt = getattr(args, 'format', 'mp4')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download only the section
        temp_video = os.path.join(tmpdir, "video.mp4")
        if not download_video(url, temp_video, quality=args.quality, api_key=args.api_key, fmt=fmt, start=args.start, end=args.end):
            return
        
        # No trim needed - already downloaded only the section
        output = args.output or f"clip_{get_video_id(url) or 'clip'}.{fmt}"
        import shutil
        shutil.copy2(temp_video, output)
        print(f"{Colors.GREEN}✅ Clip: {output}{Colors.END}")

def cmd_transcript(args):
    """Handle transcript command"""
    url = args.url
    if not validate_url(url):
        print(f"{Colors.RED}❌ Invalid YouTube URL{Colors.END}")
        return
    
    transcript = get_transcript(url, args.format, args.lang)
    if transcript:
        if args.output:
            with open(args.output, 'w') as f:
                f.write(transcript)
            print(f"{Colors.GREEN}✅ Saved to {args.output}{Colors.END}")
        else:
            print(f"\n{Colors.BOLD}Transcript:{Colors.END}")
            print(transcript[:500] + "..." if len(transcript) > 500 else transcript)

def cmd_process(args):
    """Handle full process: download + transcript"""
    url = args.url
    if not validate_url(url):
        print(f"{Colors.RED}❌ Invalid YouTube URL{Colors.END}")
        return
    
    video_id = get_video_id(url)
    base_name = f"ytclip_{video_id}"
    fmt = getattr(args, 'format', 'mp4')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download only the section (or full video if no timestamps)
        temp_video = os.path.join(tmpdir, "video.mp4")
        if not download_video(url, temp_video, quality=args.quality, api_key=args.api_key, fmt=fmt, start=args.start, end=args.end):
            return
        
        # No trim needed - download_video already handles sections
        final_video = args.output or f"{base_name}.{fmt}"
        import shutil
        shutil.copy2(temp_video, final_video)
        print(f"{Colors.GREEN}✅ Video: {final_video}{Colors.END}")
        
        # Get transcript if requested
        if getattr(args, 'transcript', False):
            trans = get_transcript(url, args.format, args.lang)
            if trans:
                trans_file = f"{base_name}.{args.format}"
                with open(trans_file, 'w') as f:
                    f.write(trans)
                print(f"{Colors.GREEN}✅ Transcript: {trans_file}{Colors.END}")

def cmd_batch(args):
    """Process multiple URLs from a file"""
    with open(args.file) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"{Colors.BOLD}Processing {len(urls)} videos...{Colors.END}")
    for i, url in enumerate(urls, 1):
        print(f"\n{Colors.CYAN}[{i}/{len(urls)}] {url}{Colors.END}")
        # Parse timestamps from URL if present (URL|start|end format)
        parts = url.split('|')
        if len(parts) == 3:
            url, start, end = parts
        else:
            start = end = None
        
        # Process
        args.url = url
        args.start = start or args.start
        args.end = end or args.end
        args.output = f"batch_{i:03d}.mp4"
        # Set defaults for transcript/format/lang if not already set
        if not hasattr(args, 'transcript'):
            args.transcript = False
        if not hasattr(args, 'format'):
            args.format = 'mp4'
        if not hasattr(args, 'lang'):
            args.lang = 'en'
        cmd_process(args)

def cmd_config(args):
    """Set configuration"""
    config_dir = os.path.expanduser("~/.ytclip")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config.json")
    
    config = {}
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
    
    if args.api_key:
        config['api_key'] = args.api_key
        print(f"{Colors.GREEN}✅ API key saved{Colors.END}")
    
    if args.quality:
        config['default_quality'] = args.quality
        print(f"{Colors.GREEN}✅ Default quality: {args.quality}{Colors.END}")
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

def main():
    parser = argparse.ArgumentParser(
        prog='ytclip',
        description='ytclip - YouTube video downloader, trimmer, and transcript extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ytclip download "https://youtube.com/watch?v=..."
  ytclip cut "https://youtube.com/watch?v=..." --start 1:30 --end 4:20
  ytclip transcript "https://youtube.com/watch?v=..."
  ytclip process "https://youtube.com/watch?v=..." --start 0:10 --end 2:30 --transcript
  ytclip batch urls.txt
        """
    )
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--api-key', help='Pro tier API key (for 1080p/4K)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Download
    dl_parser = subparsers.add_parser('download', help='Download video')
    dl_parser.add_argument('url', help='YouTube URL')
    dl_parser.add_argument('-o', '--output', help='Output filename (supports %%(title)s, %%(id)s)')
    dl_parser.add_argument('-q', '--quality', default='480', choices=['480', '720', '1080', '2160', 'best'])
    dl_parser.add_argument('-f', '--format', default='mp4', choices=['mp4', 'webm', 'mkv', 'mp3'], help='Output format')
    dl_parser.add_argument('--start', help='Start timestamp for partial download')
    dl_parser.add_argument('--end', help='End timestamp for partial download')
    
    # Cut
    cut_parser = subparsers.add_parser('cut', help='Download and trim video')
    cut_parser.add_argument('url', help='YouTube URL')
    cut_parser.add_argument('--start', required=True, help='Start timestamp (e.g., 1:30)')
    cut_parser.add_argument('--end', required=True, help='End timestamp (e.g., 4:20)')
    cut_parser.add_argument('-o', '--output', help='Output filename')
    cut_parser.add_argument('-q', '--quality', default='480', choices=['480', '720', '1080', '2160', 'best'])
    cut_parser.add_argument('-f', '--format', default='mp4', choices=['mp4', 'webm', 'mkv', 'mp3'], help='Output format')
    cut_parser.set_defaults(func=cmd_cut)
    
    # Transcript
    trans_parser = subparsers.add_parser('transcript', help='Extract transcript')
    trans_parser.add_argument('url', help='YouTube URL')
    trans_parser.add_argument('-o', '--output', help='Output file')
    trans_parser.add_argument('-f', '--format', default='text', choices=['text', 'srt', 'vtt'])
    trans_parser.add_argument('-l', '--lang', default='en', help='Language code')
    
    # Process (all-in-one)
    proc_parser = subparsers.add_parser('process', help='Download, trim, and get transcript')
    proc_parser.add_argument('url', help='YouTube URL')
    proc_parser.add_argument('--start', help='Start timestamp')
    proc_parser.add_argument('--end', help='End timestamp')
    proc_parser.add_argument('-o', '--output', help='Output filename')
    proc_parser.add_argument('-q', '--quality', default='480', choices=['480', '720', '1080', '2160', 'best'])
    proc_parser.add_argument('--transcript', action='store_true', help='Include transcript')
    proc_parser.add_argument('-f', '--format', default='mp4', choices=['mp4', 'webm', 'mkv', 'mp3'], help='Output format')
    proc_parser.add_argument('-l', '--lang', default='en')
    
    # Batch
    batch_parser = subparsers.add_parser('batch', help='Process multiple URLs')
    batch_parser.add_argument('file', help='File with URLs (one per line, format: URL|start|end)')
    batch_parser.add_argument('--start', help='Default start timestamp')
    batch_parser.add_argument('--end', help='Default end timestamp')
    batch_parser.add_argument('-q', '--quality', default='480', choices=['480', '720', '1080', '2160', 'best'])
    batch_parser.add_argument('-f', '--format', default='mp4', choices=['mp4', 'webm', 'mkv', 'mp3'], help='Output format')
    batch_parser.add_argument('--transmit', action='store_true')
    
    # Config
    cfg_parser = subparsers.add_parser('config', help='Set configuration')
    cfg_parser.add_argument('--api-key', help='Pro tier API key')
    cfg_parser.add_argument('--quality', help='Default quality')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load config
    config_file = os.path.expanduser("~/.ytclip/config.json")
    config = {}
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
    
    if not args.api_key and 'api_key' in config:
        args.api_key = config['api_key']
    if hasattr(args, 'quality') and args.quality == '480' and 'default_quality' in config:
        args.quality = config['default_quality']
    
    # Route command
    if args.command == 'download':
        cmd_download(args)
    elif args.command == 'cut':
        cmd_cut(args)
    elif args.command == 'transcript':
        cmd_transcript(args)
    elif args.command == 'process':
        cmd_process(args)
    elif args.command == 'batch':
        cmd_batch(args)
    elif args.command == 'config':
        cmd_config(args)

if __name__ == '__main__':
    main()
