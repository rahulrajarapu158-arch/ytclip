#!/bin/bash
set -e

echo "=== Setting up ytclip auto-start on WSL boot ==="

# ── 1. Install dependencies ──────────────────────────────────────────────
echo "[1/4] Checking dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip ffmpeg nginx

# ── 2. Create app directory ──────────────────────────────────────────────
echo "[2/4] Setting up app directory..."
sudo mkdir -p /opt/ytclip
sudo cp -r web src requirements.txt deploy/gunicorn.conf.py /opt/ytclip/
sudo chown -R $(whoami):$(whoami) /opt/ytclip

# ── 3. Create virtual env and install ────────────────────────────────────
echo "[3/4] Installing Python dependencies..."
python3 -m venv /opt/ytclip/venv
/opt/ytclip/venv/bin/pip install --upgrade pip -q
/opt/ytclip/venv/bin/pip install -r /opt/ytclip/requirements.txt gunicorn -q
/opt/ytclip/venv/bin/pip install -e /opt/ytclip 2>/dev/null || true

# Create output directory
mkdir -p /tmp/ytclip_web

# ── 4. Create systemd service ────────────────────────────────────────────
echo "[4/4] Creating systemd service..."

# Create log directory
sudo mkdir -p /var/log/ytclip

# Write service file
sudo tee /etc/systemd/system/ytclip.service > /dev/null << 'EOF'
[Unit]
Description=ytclip Flask App
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=hermes
Group=hermes
WorkingDirectory=/opt/ytclip
ExecStart=/opt/ytclip/venv/bin/gunicorn --config /opt/ytclip/gunicorn.conf.py 'web.app:app'
Restart=always
RestartSec=5
Environment=PATH=/opt/ytclip/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/ytclip
Environment=OUTPUT_DIR=/tmp/ytclip_web

# Hardening
NoNewPrivileges=yes
PrivateTmp=yes

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ytclip

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable ytclip.service
sudo systemctl start ytclip.service

echo ""
echo "═══════════════════════════════════════════"
echo "  ytclip service installed!"
echo "═══════════════════════════════════════════"
echo ""
echo "Commands:"
echo "  sudo systemctl status ytclip      # check status"
echo "  sudo systemctl restart ytclip     # restart"
echo "  sudo journalctl -u ytclip -f     # live logs"
echo ""
echo "Server should be running at http://localhost:5000"
echo ""
