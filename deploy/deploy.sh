#!/bin/bash
# deploy.sh — copy files to VPS and run setup
# Usage: ./deploy.sh root@<VPS_IP>

set -e

VPS_HOST="${1:?Usage: ./deploy.sh root@<VPS_IP>}"
DEPLOY_DIR="/home/hermes/yt-clipper/deploy"

echo "Deploying ytclip to $VPS_HOST..."

# Create remote directory
ssh "$VPS_HOST" "mkdir -p /opt/ytclip"

# Copy deploy files
scp "$DEPLOY_DIR/setup.sh" "$VPS_HOST:/tmp/setup.sh"
scp "$DEPLOY_DIR/requirements.txt" "$VPS_HOST:/opt/ytclip/requirements.txt"
scp "$DEPLOY_DIR/gunicorn.conf.py" "$VPS_HOST:/opt/ytclip/gunicorn.conf.py"
scp "$DEPLOY_DIR/ytclip.service" "$VPS_HOST:/opt/ytclip/ytclip.service"
scp "$DEPLOY_DIR/nginx.conf" "$VPS_HOST:/opt/ytclip/nginx.conf"

# Copy app code
scp -r /home/hermes/yt-clipper/web "$VPS_HOST:/opt/ytclip/"
scp -r /home/hermes/yt-clipper/src/ytclip "$VPS_HOST:/opt/ytclip/"

# Run setup
ssh "$VPS_HOST" "chmod +x /tmp/setup.sh && bash /tmp/setup.sh"

echo ""
echo "Done! ytclip is live on your VPS."
echo "Next: point ytclip.dev DNS to the VPS IP, then run certbot."
