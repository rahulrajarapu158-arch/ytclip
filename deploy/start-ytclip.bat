@echo off
REM Auto-start ytclip when Windows boots
REM Place this file in: shell:startup (Win+R → "shell:startup")
REM Or: C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup

echo Starting ytclip...
wsl -d Ubuntu -u root -e bash -c "systemctl start ytclip 2>/dev/null || (cd /home/hermes/yt-clipper && /home/hermes/.local/bin/uvicorn --host 127.0.0.1 --port 5000 --interface wsgi web.app:app &)"
echo ytclip started at http://localhost:5000
