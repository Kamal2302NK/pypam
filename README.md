# PyPAM — Open Source Privileged Access Management

<p align="center">
  <strong>A lightweight, self-hosted PAM solution for managing privileged access to servers and databases.</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-usage-guide">Usage</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-troubleshooting">Troubleshooting</a>
</p>

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser / Client                          │
│                   (Web UI + xterm.js SSH Terminal)                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP / WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Nginx (Reverse Proxy)                        │
│                 :80 / :443  →  127.0.0.1:5000                       │
│              WebSocket upgrade for /socket.io                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PyPAM Application (Flask)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Auth     │  │ REST API │  │ Socket.IO│  │ Connection Proxy   │  │
│  │ (JWT +   │  │ (Assets, │  │ (Live    │  │ (Paramiko SSH,     │  │
│  │  MFA)    │  │  Users,  │  │  Terminal │  │  DB drivers)       │  │
│  │          │  │  Perms)  │  │  Relay)  │  │                    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┬───────────┘  │
│                                                      │              │
│  ┌──────────────────────────────────────┐            │              │
│  │ SQLAlchemy ORM (SQLite / PostgreSQL) │            │              │
│  └──────────────────┬───────────────────┘            │              │
└─────────────────────┼────────────────────────────────┼──────────────┘
                      │                                │
                      ▼                                ▼
              ┌───────────────┐          ┌──────────────────────────┐
              │   Database    │          │   Target Assets          │
              │  (pypam.db)   │          │  ┌────────┐ ┌─────────┐ │
              └───────────────┘          │  │Linux VM│ │MySQL    │ │
                                         │  │(SSH)   │ │PostgreSQL│ │
                                         │  │Windows │ │MongoDB  │ │
                                         │  │(RDP)   │ │Redis    │ │
                                         │  └────────┘ └─────────┘ │
                                         └──────────────────────────┘
```

### Component Descriptions

| Component | Technology | Purpose |
|---|---|---|
| **Web Frontend** | HTML/CSS/JS + xterm.js | User interface, web-based SSH terminal |
| **Reverse Proxy** | Nginx | TLS termination, static files, WebSocket upgrade |
| **Application** | Flask + Gunicorn (eventlet) | REST API, authentication, business logic |
| **Real-time** | Flask-SocketIO | Live SSH terminal relay, session monitoring |
| **SSH Proxy** | Paramiko | Connects to target Linux/Unix servers |
| **DB Proxy** | PyMySQL, psycopg2, pymongo, redis-py | Proxied database access with query logging |
| **Database** | SQLite (default) / PostgreSQL | Users, assets, permissions, sessions, audit logs |
| **Credential Vault** | Fernet symmetric encryption | Encrypted storage of system account passwords/keys |

### Tech Stack

- **Language:** Python 3.10+
- **Framework:** Flask, Flask-RESTful, Flask-SocketIO
- **ORM:** SQLAlchemy
- **Auth:** JWT (PyJWT), bcrypt, TOTP (pyotp)
- **SSH:** Paramiko
- **WSGI:** Gunicorn with eventlet workers
- **Proxy:** Nginx
- **Container:** Docker & Docker Compose

---

## ✨ Features

### User Management & RBAC
- **Four roles:** Admin, Operator, Auditor, User — each with fine-grained permissions
- User CRUD, password policies, and account deactivation

### VM Access (SSH)
- Web-based SSH terminal via xterm.js + Socket.IO
- Session recording and replay (asciinema-compatible)
- Command logging with risk-level classification (normal / warning / danger)
- Live session monitoring and administrative termination

### Database Access
- Proxied connections to **MySQL**, **PostgreSQL**, **MongoDB**, and **Redis**
- Query logging with full audit trail
- Users never see actual database credentials

### Multi-Factor Authentication
- TOTP-based MFA (compatible with Google Authenticator, Authy, etc.)
- Enforceable per-role or per-user

### Credential Vaulting
- All system account passwords and SSH keys are encrypted at rest (Fernet)
- Operators manage credentials; end users connect without seeing them

### Permission Management
- Grant users access to specific assets via specific system accounts
- Time-based access windows (start date / expiry date)
- Action controls: connect, upload, download, clipboard

### Audit & Compliance
- Complete login log (IP, user-agent, success/failure)
- Per-session command history with timestamps
- Session replay for SSH connections
- Dashboard with real-time statistics

---

## 📋 Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| **OS** | Ubuntu 20.04 LTS | Ubuntu 22.04 / 24.04 LTS |
| **Python** | 3.10 | 3.11+ |
| **RAM** | 1 GB | 2 GB+ |
| **Disk** | 10 GB | 20 GB+ (depends on session recordings) |
| **Network** | Outbound to target assets | Dedicated management VLAN |

> **Docker path:** If using Docker, you only need Docker Engine 20.10+ and Docker Compose v2.

---

## 🚀 Quick Start

### Method 1: Automated Deploy Script (Recommended)

The fastest path on a fresh Ubuntu server:

```bash
git clone https://github.com/yourorg/pypam.git
cd pypam
sudo bash deploy.sh
```

The script will:
1. Verify Ubuntu version and install system dependencies
2. Create a `pypam` system user and directory structure
3. Set up a Python virtual environment and install packages
4. Generate cryptographic secrets
5. Initialize the database with a default admin account
6. Install and start the systemd service and Nginx

Once complete you'll see the access URL and default credentials.

### Method 2: Docker (Easiest)

```bash
git clone https://github.com/yourorg/pypam.git
cd pypam

# Create your environment file
cp .env.example .env
# Edit .env and set real secrets (or leave defaults for testing)

# Start the full stack
docker-compose up -d

# View logs
docker-compose logs -f pypam
```

PyPAM will be available at **http://localhost**.

### Method 3: Manual Setup

<details>
<summary>Click to expand step-by-step manual installation</summary>

```bash
# 1. Install system packages
sudo apt update && sudo apt install -y python3 python3-pip python3-venv \
    python3-dev build-essential libffi-dev libssl-dev nginx

# 2. Create application user
sudo useradd --system --shell /usr/sbin/nologin --home-dir /opt/pypam --create-home pypam

# 3. Create directories
sudo mkdir -p /opt/pypam/data/{sessions,replays} /var/log/pypam

# 4. Copy application files
sudo cp -r ./* /opt/pypam/

# 5. Create virtual environment
sudo python3 -m venv /opt/pypam/venv
sudo /opt/pypam/venv/bin/pip install -r /opt/pypam/requirements.txt

# 6. Generate secrets and create .env
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sudo tee /opt/pypam/.env > /dev/null <<EOF
SECRET_KEY=$SECRET
JWT_SECRET_KEY=$JWT_SECRET
DATABASE_URI=sqlite:////opt/pypam/data/pypam.db
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
LOG_LEVEL=INFO
SESSION_RECORDING_PATH=/opt/pypam/data/sessions
ALLOWED_HOSTS=*
DEBUG=false
EOF

# 7. Initialize database
cd /opt/pypam
sudo -u pypam /opt/pypam/venv/bin/python -c "
from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash
import uuid
app = create_app()
with app.app_context():
    db.create_all()
    admin = User(id=str(uuid.uuid4()), username='admin',
                 email='admin@pypam.local',
                 password_hash=generate_password_hash('admin123'),
                 role='admin', is_active=True)
    db.session.add(admin)
    db.session.commit()
"

# 8. Set ownership
sudo chown -R pypam:pypam /opt/pypam /var/log/pypam
sudo chmod 600 /opt/pypam/.env

# 9. Install systemd service
sudo cp pypam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pypam

# 10. Configure Nginx
sudo cp nginx.conf /etc/nginx/sites-available/pypam
sudo ln -sf /etc/nginx/sites-available/pypam /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

</details>

---

## 📖 Usage Guide

### First Login

1. Open your browser and navigate to `http://<server-ip>`
2. Log in with the default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. **Change your password immediately** via *Profile → Change Password*

### Adding VM Assets (SSH Servers)

1. Navigate to **Assets → Asset List**
2. Click **Add Asset**
3. Fill in:
   - **Name:** descriptive name (e.g., "Production Web Server 1")
   - **Hostname / IP:** the target server's address
   - **Port:** SSH port (default 22)
   - **Asset Type:** Linux
   - **Protocol:** SSH
4. Click **Save**

### Adding Database Assets

1. Navigate to **Assets → Asset List**
2. Click **Add Asset**
3. Fill in:
   - **Name:** e.g., "Production MySQL"
   - **Hostname / IP:** database host
   - **Port:** database port (3306, 5432, 27017, 6379)
   - **Asset Type:** Database
   - **Protocol:** MySQL / PostgreSQL / MongoDB / Redis
   - **Database Name:** target database (if applicable)
4. Click **Save**

### Creating System Accounts

System accounts are the **actual credentials** on the target machine or database. Users never see these directly.

1. Navigate to **Assets → Asset List** and click on an asset
2. Go to the **Accounts** tab
3. Click **Add Account**
4. Enter:
   - **Username:** the login on the target (e.g., `root`, `deploy`, `dbadmin`)
   - **Password** or **SSH Private Key**
   - **Account Type:** Common / Admin / Privileged
5. Click **Save** — the credential is encrypted and stored in the vault

### Setting Up Permissions

1. Navigate to **Permissions → Permission List**
2. Click **Add Permission**
3. Select:
   - **User:** the PyPAM user
   - **Asset:** the target asset
   - **System Account:** which credential to use
   - **Actions:** Connect, Upload, Download, Clipboard
   - **Valid From / Expires:** optional time window
4. Click **Save**

### Connecting to Assets

1. Navigate to **My Assets** (or **Assets → Asset List**)
2. Click the **Connect** button next to an asset
3. For **SSH assets:** a web terminal opens in a new tab
4. For **Database assets:** a query interface opens

### Monitoring Sessions

Admins and Auditors can:

1. Navigate to **Sessions → Active Sessions** to see live connections
2. Click **Monitor** to watch a session in real-time
3. Click **Terminate** to force-disconnect a session
4. Navigate to **Sessions → Session History** and click **Replay** to play back a recorded SSH session

### Reviewing Audit Logs

1. **Sessions → Command Logs:** every command executed through PyPAM, with risk levels
2. **Sessions → Login Logs:** all authentication events with IP addresses
3. **Dashboard:** real-time counts of users, assets, sessions, and recent activity

---

## 🔒 Security Considerations

> [!CAUTION]
> **Change the default admin password (`admin123`) immediately after deployment!**

### Authentication Hardening
- Enable MFA for **all** admin and operator accounts
- Set strong `SECRET_KEY` and `JWT_SECRET_KEY` values (the deploy script does this automatically)
- JWT tokens expire after 24 hours by default

### HTTPS in Production
The included Nginx config has a commented-out HTTPS server block. To enable:

```bash
# Obtain a certificate (e.g., Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Or manually place your certificates and uncomment the SSL block in nginx.conf
```

### Credential Encryption
- All system account passwords and SSH private keys are encrypted at rest using **Fernet symmetric encryption** (AES-128-CBC + HMAC-SHA256)
- The encryption key is stored in `.env` — protect this file (`chmod 600`)

### Network Security
- PyPAM listens on `127.0.0.1:5000` (localhost only); Nginx handles external access
- Use firewall rules to restrict which IPs can reach the Nginx port
- Place PyPAM on a dedicated management network / VLAN
- Target assets should ideally be reachable only from the PyPAM server

### Best Practices
- Run regular backups of `/opt/pypam/data/`
- Rotate the `ENCRYPTION_KEY` periodically (re-encrypt credentials)
- Review audit logs weekly
- Use the Auditor role for compliance personnel (read-only access to sessions and logs)

---

## 🛠️ Configuration Reference

All configuration is via environment variables in `/opt/pypam/.env`:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | Flask secret key for session signing |
| `JWT_SECRET_KEY` | *(required)* | Secret for JWT token signing |
| `DATABASE_URI` | `sqlite:////opt/pypam/data/pypam.db` | SQLAlchemy database connection string |
| `ENCRYPTION_KEY` | *(required)* | Fernet key for encrypting stored credentials |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `SESSION_RECORDING_PATH` | `/opt/pypam/data/sessions` | Directory for SSH session recordings |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hostnames |
| `DEBUG` | `false` | Enable Flask debug mode (**never in production**) |
| `SMTP_SERVER` | *(optional)* | SMTP server for email alerts |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(optional)* | SMTP username |
| `SMTP_PASSWORD` | *(optional)* | SMTP password |
| `ALERT_EMAIL` | *(optional)* | Email address for security alerts |

---

## 📊 API Reference

All API endpoints are prefixed with `/api`. Authentication is via JWT Bearer token (obtained from `/api/auth/login`).

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/auth/login` | Login, returns JWT token | No |
| `POST` | `/api/auth/logout` | Invalidate token | Yes |
| `GET` | `/api/auth/profile` | Current user profile | Yes |
| `POST` | `/api/auth/mfa/enable` | Enable MFA, returns QR secret | Yes |
| `POST` | `/api/auth/mfa/verify` | Verify MFA TOTP code | Yes |

### Users (Admin only)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users` | List all users |
| `POST` | `/api/users` | Create a new user |
| `GET` | `/api/users/<id>` | Get user details |
| `PUT` | `/api/users/<id>` | Update user |
| `DELETE` | `/api/users/<id>` | Delete user |
| `POST` | `/api/users/<id>/reset-password` | Reset user password |

### Assets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/assets` | List all assets |
| `POST` | `/api/assets` | Create asset |
| `GET` | `/api/assets/<id>` | Get asset details |
| `PUT` | `/api/assets/<id>` | Update asset |
| `DELETE` | `/api/assets/<id>` | Delete asset |
| `GET` | `/api/assets/types` | List supported asset types |
| `POST` | `/api/assets/<id>/test-connection` | Test connectivity to asset |

### System Accounts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/assets/<id>/accounts` | List accounts for asset |
| `POST` | `/api/assets/<id>/accounts` | Create account for asset |
| `GET` | `/api/accounts/<id>` | Get account details |
| `PUT` | `/api/accounts/<id>` | Update account |
| `DELETE` | `/api/accounts/<id>` | Delete account |

### Permissions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/permissions` | List all permissions |
| `POST` | `/api/permissions` | Create permission |
| `GET` | `/api/permissions/<id>` | Get permission details |
| `PUT` | `/api/permissions/<id>` | Update permission |
| `DELETE` | `/api/permissions/<id>` | Delete permission |
| `GET` | `/api/users/<id>/permissions` | Permissions for a user |
| `GET` | `/api/users/<id>/assets` | Assets accessible by user |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/sessions` | List sessions (admin: all, user: own) |
| `GET` | `/api/sessions/<id>` | Session details |
| `DELETE` | `/api/sessions/<id>/terminate` | Force-terminate active session |
| `GET` | `/api/sessions/<id>/commands` | Command log for session |
| `GET` | `/api/sessions/<id>/replay` | Session replay data |

### Connect (PAM Proxy)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/connect/ssh` | Initiate SSH session (returns WebSocket URL) |
| `POST` | `/api/connect/db` | Initiate DB session (returns session token) |
| `POST` | `/api/connect/db/query` | Execute query through PAM proxy |
| `GET` | `/api/connect/sessions` | User's active connections |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard/stats` | Counts: users, assets, sessions |
| `GET` | `/api/dashboard/recent-sessions` | Last 10 sessions |
| `GET` | `/api/dashboard/login-logs` | Recent login events |

### Health

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Application health check | No |

---

## 🔧 Troubleshooting

### Service won't start

```bash
# Check service status and logs
sudo systemctl status pypam
sudo journalctl -u pypam -n 50 --no-pager

# Check application error log
sudo tail -50 /var/log/pypam/error.log
```

**Common causes:**
- `.env` file missing or has wrong permissions → `sudo chmod 600 /opt/pypam/.env`
- Python dependency missing → re-run `pip install -r requirements.txt` in the venv
- Port 5000 already in use → `sudo ss -tlnp | grep 5000`

### Nginx returns 502 Bad Gateway

The PyPAM application is not running or not listening on port 5000.

```bash
# Verify PyPAM is running
sudo systemctl status pypam

# Verify it's listening
sudo ss -tlnp | grep 5000

# Restart
sudo systemctl restart pypam
```

### Cannot connect to an SSH asset

1. **Check connectivity** from the PyPAM server:
   ```bash
   ssh -p <port> <username>@<hostname>
   ```
2. **Verify system account credentials** in the PyPAM UI (Assets → Account → Test)
3. **Check firewall rules** between PyPAM server and target
4. **Review session logs:** Sessions → Command Logs

### Database file is locked (SQLite)

This happens when multiple processes try to write simultaneously.

```bash
# Use only 1 Gunicorn worker with SQLite (this is the default)
# If you need concurrency, switch to PostgreSQL:
DATABASE_URI=postgresql://pypam:password@localhost:5432/pypam
```

### MFA not working

- Ensure the server clock is accurate (TOTP is time-sensitive):
  ```bash
  sudo timedatectl set-ntp true
  ```
- Re-scan the QR code in your authenticator app
- Check that `pyotp` is installed: `/opt/pypam/venv/bin/pip show pyotp`

### Docker: container exits immediately

```bash
# Check logs
docker-compose logs pypam

# Common fix: ensure .env exists
cp .env.example .env
# Edit .env with real secrets, then restart
docker-compose up -d
```

### Permission denied errors

```bash
# Fix ownership
sudo chown -R pypam:pypam /opt/pypam /var/log/pypam

# Fix .env permissions
sudo chmod 600 /opt/pypam/.env
```

### High memory usage

- Session recordings accumulate over time. Archive old recordings:
  ```bash
  # Move recordings older than 90 days
  find /opt/pypam/data/sessions -mtime +90 -exec mv {} /archive/pypam/ \;
  ```
- Consider switching to PostgreSQL for large deployments

---

## 🗂️ Project Structure

```
pypam/
├── app.py                 # Flask application & API routes
├── models.py              # SQLAlchemy database models
├── auth.py                # JWT authentication & RBAC decorators
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
├── deploy.sh              # Automated Ubuntu deployment script
├── pypam.service          # systemd service unit
├── nginx.conf             # Nginx reverse proxy configuration
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Full-stack Docker Compose
├── .env.example           # Environment variable template
├── README.md              # This documentation
├── static/                # Frontend static assets
│   ├── css/
│   ├── js/
│   └── img/
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── assets.html
│   ├── sessions.html
│   ├── terminal.html
│   └── ...
└── data/                  # Runtime data (created by deploy)
    ├── pypam.db           # SQLite database
    ├── sessions/          # SSH session recordings
    └── replays/           # Session replay files
```

---

## 📜 License

MIT License

Copyright (c) 2024 PyPAM Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
