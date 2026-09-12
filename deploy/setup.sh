#!/bin/bash
# ytclip VPS deployment script for Oracle Cloud Ampere A1 (ARM64)
# Run as root on a fresh Ubuntu 24.04 instance

set -e

echo "╔══════════════════════════════════════╗"
║   ytclip VPS Deployment Script       ║
║   Ubuntu 24.04 ARM64 (Oracle A1)     ║
╚══════════════════════════════════════╝

# ── 1. System dependencies ───────────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -y
apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    htop \
    curl \
    git

# ── 2. Create app user ──────────────────────────────────────────────────
echo "[2/6] Creating ytclip user..."
id -u ytclip &>/dev/null || useradd -m -s /bin/bash ytclip
mkdir -p /opt/ytclip
chown ytclip:ytclip /opt/ytclip

# ── 3. App setup ────────────────────────────────────────────────────────
echo "[3/6] Setting up ytclip application..."
cd /opt/ytclip

# Copy application code (we'll upload this)
# Expected structure:
#   /opt/ytclip/
#   ├── app.py
#   ├── ytclip/
#   │   ├── __init__.py
#   │   ├── __main__.py
#   │   └── cli.py
#   ├── web/
#   │   ├── templates/
#   │   │   └── index.html
#   │   └── app.py
#   ├── requirements.txt
#   ├── gunicorn.conf.py
#   └── ytclip.service

sudo -u ytclip python3 -m venv /opt/ytclip/venv
sudo -u ytclip /opt/ytclip/venv/bin/pip install --upgrade pip
sudo -u ytclip /opt/ytclip/venv/bin/pip install -r /opt/ytclip/requirements.txt
sudo -u ytclip /opt/ytclip/venv/bin/pip install gunicorn

# Create output directory for clips
mkdir -p /tmp/ytclip_web
chown ytclip:ytclip /tmp/ytclip_web

# ── 4. systemd service ──────────────────────────────────────────────────
echo "[4/6] Configuring systemd service..."
cp /opt/ytclip/ytclip.service /etc/systemd/system/ytclip.service
systemctl daemon-reload
systemctl enable ytclip
systemctl start ytclip
sleep 2
systemctl status ytclip --no-pager

# ── 5. Nginx reverse proxy ──────────────────────────────────────────────
echo "[5/6] Configuring Nginx..."
cp /opt/ytclip/nginx.conf /etc/nginx/sites-available/ytclip
ln -sf /etc/nginx/sites-available/ytclip /etc/nginx/sites-enabled/ytclip
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# ── 6. Firewall ─────────────────────────────────────────────────────────
echo "[6/6] Configuring firewall..."
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw --force enable

echo ""
echo "═══════════════════════════════════════"
echo "  Deploy complete!"
echo "  Flask running on port 5000"
echo "  Nginx proxying 80/443 → 5000"
echo "═══════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Point ytclip.dev DNS to this server's IP"
echo "  2. Run: certbot --nginx -d ytclip.dev"
echo "  3. Visit https://ytclip.dev"
echo ""
echo "Useful commands:"
echo "  systemctl status ytclip    # check service"
echo "  journalctl -u ytclip -f    # live logs"
echo "  systemctl restart ytclip   # restart"
