#!/bin/bash
# =============================================================================
# PyPAM Deployment Script for Ubuntu 20.04 / 22.04 / 24.04
# Usage: sudo bash deploy.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
section() { echo -e "\n${BLUE}==>${NC} ${YELLOW}$*${NC}"; }

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PYPAM_USER="pypam"
PYPAM_DIR="/opt/pypam"
PYPAM_VENV="${PYPAM_DIR}/venv"
PYPAM_LOG="/var/log/pypam"
PYPAM_DATA="${PYPAM_DIR}/data"
PYPAM_PORT="${PYPAM_PORT:-8080}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# 1. Root check
# ---------------------------------------------------------------------------
section "Checking privileges"
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root.  Use:  sudo bash $0"
    exit 1
fi
info "Running as root — OK"

# ---------------------------------------------------------------------------
# 2. Ubuntu version check
# ---------------------------------------------------------------------------
section "Checking Ubuntu version"
if [[ ! -f /etc/os-release ]]; then
    error "Cannot determine OS version (/etc/os-release not found)."
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    error "This script supports Ubuntu only. Detected: $ID"
    exit 1
fi

SUPPORTED_VERSIONS=("20.04" "22.04" "24.04")
VERSION_OK=false
for v in "${SUPPORTED_VERSIONS[@]}"; do
    if [[ "$VERSION_ID" == "$v" ]]; then
        VERSION_OK=true
        break
    fi
done

if ! $VERSION_OK; then
    warn "Untested Ubuntu version: $VERSION_ID (supported: ${SUPPORTED_VERSIONS[*]})"
    read -rp "Continue anyway? [y/N] " yn
    [[ "$yn" =~ ^[Yy]$ ]] || exit 1
fi
info "Ubuntu $VERSION_ID detected"

# ---------------------------------------------------------------------------
# 3. Update system packages
# ---------------------------------------------------------------------------
section "Updating system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
info "System packages up to date"

# ---------------------------------------------------------------------------
# 4. Install dependencies
# ---------------------------------------------------------------------------
section "Installing dependencies"
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    build-essential libffi-dev libssl-dev \
    nginx \
    git curl wget \
    supervisor \
    2>&1 | tail -1

# Ensure Python >= 3.10
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 10) )); then
    error "Python 3.10+ is required (found $PYTHON_VERSION)."
    error "On Ubuntu 20.04 you may need to install from deadsnakes PPA."
    exit 1
fi
info "Python $PYTHON_VERSION — OK"

# ---------------------------------------------------------------------------
# 5. Create system user
# ---------------------------------------------------------------------------
section "Creating system user '${PYPAM_USER}'"
if id "$PYPAM_USER" &>/dev/null; then
    info "User '$PYPAM_USER' already exists — skipping"
else
    useradd --system --shell /usr/sbin/nologin --home-dir "$PYPAM_DIR" --create-home "$PYPAM_USER"
    info "User '$PYPAM_USER' created"
fi

# ---------------------------------------------------------------------------
# 6. Create directory structure
# ---------------------------------------------------------------------------
section "Creating directory structure"
mkdir -p "$PYPAM_DIR"
mkdir -p "$PYPAM_DATA"
mkdir -p "${PYPAM_DATA}/sessions"
mkdir -p "${PYPAM_DATA}/replays"
mkdir -p "$PYPAM_LOG"
mkdir -p /data/jump-2
chmod 777 /data/jump-2 2>/dev/null || true
info "Directories created:"
info "  Application : $PYPAM_DIR"
info "  Data        : $PYPAM_DATA"
info "  Recordings  : /data/jump-2"
info "  Logs        : $PYPAM_LOG"

# ---------------------------------------------------------------------------
# 7. Copy application files
# ---------------------------------------------------------------------------
section "Copying application files"
# Copy everything except deployment-only files
rsync -a --exclude='deploy.sh' \
         --exclude='Dockerfile' \
         --exclude='docker-compose.yml' \
         --exclude='.env.example' \
         --exclude='venv' \
         --exclude='__pycache__' \
         --exclude='.git' \
         "${SCRIPT_DIR}/" "${PYPAM_DIR}/"
info "Application files copied to $PYPAM_DIR"

# ---------------------------------------------------------------------------
# 8. Create Python virtual environment & install requirements
# ---------------------------------------------------------------------------
section "Setting up Python virtual environment"
python3 -m venv "$PYPAM_VENV"
source "${PYPAM_VENV}/bin/activate"

pip install --upgrade pip setuptools wheel -q
if [[ -f "${PYPAM_DIR}/requirements.txt" ]]; then
    pip install -r "${PYPAM_DIR}/requirements.txt" -q
    info "Python dependencies installed"
else
    error "requirements.txt not found in $PYPAM_DIR"
    exit 1
fi

deactivate

# ---------------------------------------------------------------------------
# 9 & 10. Generate secrets and create .env
# ---------------------------------------------------------------------------
section "Generating secrets & creating .env"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
    || python3 -c "import secrets; print(secrets.token_urlsafe(32))")

if [[ ! -f "${PYPAM_DIR}/.env" ]]; then
    cat > "${PYPAM_DIR}/.env" <<EOF
# PyPAM Environment Configuration — generated by deploy.sh
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
DATABASE_URI=sqlite:///${PYPAM_DATA}/pypam.db
ENCRYPTION_KEY=${ENCRYPTION_KEY}
LOG_LEVEL=INFO
SESSION_RECORDING_PATH=/data/jump-2/recording
ARCHIVE_PATH=/data/jump-2/archive
VIDEO_RETENTION_DAYS=60
AUDIT_RETENTION_DAYS=180
ALLOWED_HOSTS=*
DEBUG=false
EOF
    info ".env created with generated keys"
else
    warn ".env already exists — skipping (remove it to regenerate)"
fi

# ---------------------------------------------------------------------------
# 11. Initialize database
# ---------------------------------------------------------------------------
section "Initializing database"
cd "$PYPAM_DIR"
"${PYPAM_VENV}/bin/python" -c "
from app import create_app, seed_data, db
from models import User
import uuid, os

app = create_app()
with app.app_context():
    db.create_all()
    seed_data(app)
    print('Database initialized with default admin.')
"
info "Database initialized"

# ---------------------------------------------------------------------------
# 12. Set ownership
# ---------------------------------------------------------------------------
section "Setting file ownership"
chown -R "${PYPAM_USER}:${PYPAM_USER}" "$PYPAM_DIR"
chown -R "${PYPAM_USER}:${PYPAM_USER}" "$PYPAM_LOG"
chmod 600 "${PYPAM_DIR}/.env"
info "Ownership set to ${PYPAM_USER}:${PYPAM_USER}"

# ---------------------------------------------------------------------------
# 13. Install systemd service
# ---------------------------------------------------------------------------
section "Installing systemd service"
cp "${SCRIPT_DIR}/pypam.service" /etc/systemd/system/pypam.service
systemctl daemon-reload
info "systemd unit installed"

# ---------------------------------------------------------------------------
# 14. Install nginx configuration
# ---------------------------------------------------------------------------
section "Configuring Nginx"
# Remove default site if present
rm -f /etc/nginx/sites-enabled/default

# Auto-detect if port 80 is busy
if ss -tulpn | grep -q ':80 '; then
    warn "Port 80 is already in use by another application. Configuring PyPAM on port ${PYPAM_PORT}..."
    sed -E "s/listen (80|8080);/listen ${PYPAM_PORT};/g" "${SCRIPT_DIR}/nginx.conf" > /etc/nginx/sites-available/pypam
else
    cp "${SCRIPT_DIR}/nginx.conf" /etc/nginx/sites-available/pypam
fi

ln -sf /etc/nginx/sites-available/pypam /etc/nginx/sites-enabled/pypam

# Validate nginx config
nginx -t 2>&1 || { error "Nginx config test failed"; exit 1; }
info "Nginx configured and validated"

# ---------------------------------------------------------------------------
# 15. Enable and start services
# ---------------------------------------------------------------------------
section "Enabling & starting services"
systemctl daemon-reload
systemctl enable pypam.service
systemctl restart pypam.service
systemctl restart nginx

# Wait a moment and check health
sleep 2
if systemctl is-active --quiet pypam.service; then
    info "PyPAM service is running"
else
    error "PyPAM service failed to start — check: journalctl -u pypam"
    exit 1
fi

if systemctl is-active --quiet nginx.service; then
    info "Nginx service is running"
else
    warn "Nginx is not running — check: journalctl -u nginx"
fi

# ---------------------------------------------------------------------------
# 16. Summary
# ---------------------------------------------------------------------------
PORT_STR=""
if grep -q "listen ${PYPAM_PORT};" /etc/nginx/sites-available/pypam; then
    PORT_STR=":${PYPAM_PORT}"
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  PyPAM has been deployed successfully!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  ${BLUE}Access URL:${NC}       http://$(hostname -I | awk '{print $1}')${PORT_STR}"
echo -e "  ${BLUE}Admin user:${NC}       admin"
echo -e "  ${BLUE}Admin password:${NC}   admin123"
echo ""
echo -e "  ${BLUE}Application dir:${NC}  ${PYPAM_DIR}"
echo -e "  ${BLUE}Data dir:${NC}         ${PYPAM_DATA}"
echo -e "  ${BLUE}Log dir:${NC}          ${PYPAM_LOG}"
echo -e "  ${BLUE}Service name:${NC}     pypam.service"
echo ""
echo -e "${YELLOW}  ⚠  Next Steps:${NC}"
echo -e "   1. Change the default admin password immediately!"
echo -e "   2. Enable MFA for admin accounts"
echo -e "   3. Configure HTTPS (see nginx.conf SSL comments)"
echo -e "   4. Add your first assets via the web UI"
echo ""
echo -e "  ${BLUE}Useful commands:${NC}"
echo -e "   systemctl status pypam          — check service status"
echo -e "   journalctl -u pypam -f          — follow logs"
echo -e "   tail -f ${PYPAM_LOG}/error.log  — application errors"
echo -e "   systemctl restart pypam         — restart the service"
echo ""
