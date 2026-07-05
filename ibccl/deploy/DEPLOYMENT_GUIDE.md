# 🚀 Production Deployment Guide
## Hostinger VPS — `72.61.148.231:8080`

---

## Architecture Overview

```
Browser (Port 8080)
       │
       ▼
   Nginx (Port 8080)  ◄─── serves /static/ and /media/ directly
       │
       ├── HTTP Requests ───────► Daphne (127.0.0.1:8001)
       │                               │
       └── WebSocket (/ws/) ──────►   Django Channels
                                       │
                                   Redis (6379)
```

---

## Files Created

| File | Description |
|------|-------------|
| `deploy/daphne.service` | Systemd service — runs Daphne as background process |
| `deploy/nginx_isp_inventory.conf` | Nginx config — port 8080, WebSocket support |
| `deploy/deploy.sh` | Automated deployment script |

---

## Step-by-Step Manual Deployment

### Step 1: Connect to Your VPS
```bash
ssh root@72.61.148.231
```

### Step 2: Upload Your Project
```bash
# Option A: Via Git (Recommended)
git clone <your-repo-url> /var/www/isp-inventory

# Option B: Via SCP from your Windows machine (run in PowerShell)
scp -r C:\Users\Mehedi\ISP-inventory\ibccl root@72.61.148.231:/var/www/isp-inventory/
```

### Step 3: Install System Dependencies (on VPS)
```bash
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    postgresql postgresql-contrib \
    nginx redis-server git
```

### Step 4: Set Up Virtual Environment & Install Packages
```bash
cd /var/www/isp-inventory
python3 -m venv venv
source venv/bin/activate

pip install -r ibccl/requirements.txt
pip install channels_redis   # Required for Redis WebSocket support
```

### Step 5: Configure Production Settings
Edit `settings.py` on VPS:
```bash
nano /var/www/isp-inventory/ibccl/ibccl/settings.py
```
Make these changes:
```python
DEBUG = False                              # ← Must be False in production!
SECRET_KEY = 'your-new-secret-key-here'   # ← Generate a new, strong key
```

### Step 6: Run Django Migrations & Collect Static Files
```bash
cd /var/www/isp-inventory/ibccl
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 7: Set Up Daphne Service
```bash
cp /var/www/isp-inventory/ibccl/deploy/daphne.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable daphne
systemctl start daphne

# Verify it is running:
systemctl status daphne
```

### Step 8: Set Up Nginx
```bash
cp /var/www/isp-inventory/ibccl/deploy/nginx_isp_inventory.conf \
   /etc/nginx/sites-available/isp_inventory

ln -s /etc/nginx/sites-available/isp_inventory \
      /etc/nginx/sites-enabled/

rm -f /etc/nginx/sites-enabled/default  # Remove default site

nginx -t          # Test the config
systemctl restart nginx
systemctl enable nginx
```

### Step 9: Open Firewall Port
```bash
ufw allow 8080/tcp
ufw reload
```

### Step 10: Start Redis
```bash
systemctl enable redis-server
systemctl start redis-server
```

---

## ✅ Access Your App

Open in browser: **`http://72.61.148.231:8080`**

---

## 🔧 Useful Commands (on VPS)

```bash
# View app logs in real-time
journalctl -u daphne -f

# Restart app after code changes
systemctl restart daphne

# Restart nginx
systemctl restart nginx

# Check Redis
redis-cli ping  # Should return: PONG

# Redeploy (git pull + restart)
cd /var/www/isp-inventory && git pull
source venv/bin/activate
cd ibccl && python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart daphne
```

---

## ⚠️ Important Security Notes

> **Before going fully live:**
> 1. Change `DEBUG = False` in `settings.py`
> 2. Set a new strong `SECRET_KEY` (never commit it to Git)
> 3. Use PostgreSQL database credentials different from default
> 4. Ensure `ufw` firewall is active: `ufw enable`
