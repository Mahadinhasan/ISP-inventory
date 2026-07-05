#!/bin/bash
##############################################################
# ISP Inventory Management System
# Hostinger VPS Deployment Script
# VPS IP: 72.61.148.231  |  Port: 8080
# Run this script on your VPS as root user
##############################################################

set -e  # Exit immediately on any error

PROJECT_DIR="/var/www/isp-inventory"
REPO_URL="YOUR_GIT_REPO_URL_HERE"   # <-- Replace with your git repo URL
VENV_DIR="$PROJECT_DIR/venv"
APP_DIR="$PROJECT_DIR/ibccl"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ISP Inventory - VPS Deployment Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: System packages ──────────────────────
echo "[1/8] Installing system packages..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx redis-server git

# ── Step 2: Clone project ────────────────────────
echo "[2/8] Setting up project directory..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

if [ -d "$APP_DIR" ]; then
    echo "  Project found. Pulling latest changes..."
    cd $APP_DIR && git pull
else
    echo "  Cloning project..."
    git clone $REPO_URL $PROJECT_DIR
fi

# ── Step 3: Python virtual environment ──────────
echo "[3/8] Setting up Python virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

cd $APP_DIR
pip install --upgrade pip
pip install -r requirements.txt
pip install channels_redis    # Redis channel layer for WebSocket support

# ── Step 4: Django production setup ─────────────
echo "[4/8] Running Django setup..."
python manage.py migrate
python manage.py collectstatic --noinput

# ── Step 5: Open firewall port 8080 ─────────────
echo "[5/8] Opening firewall port 8080..."
ufw allow 8080/tcp
ufw reload

# ── Step 6: Install Daphne service ──────────────
echo "[6/8] Installing Daphne systemd service..."
cp $PROJECT_DIR/ibccl/deploy/daphne.service /etc/systemd/system/daphne.service
systemctl daemon-reload
systemctl enable daphne
systemctl restart daphne
echo "  Daphne status:"
systemctl status daphne --no-pager

# ── Step 7: Install Nginx config ────────────────
echo "[7/8] Setting up Nginx configuration..."
cp $PROJECT_DIR/ibccl/deploy/nginx_isp_inventory.conf /etc/nginx/sites-available/isp_inventory
ln -sf /etc/nginx/sites-available/isp_inventory /etc/nginx/sites-enabled/
# Remove default Nginx site if present
rm -f /etc/nginx/sites-enabled/default
nginx -t  # Test configuration
systemctl restart nginx
systemctl enable nginx

# ── Step 8: Enable Redis ─────────────────────────
echo "[8/8] Enabling Redis service..."
systemctl enable redis-server
systemctl restart redis-server

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deployment Complete!"
echo "  Access your app at: http://72.61.148.231:8080"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
