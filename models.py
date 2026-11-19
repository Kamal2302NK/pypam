"""
PyPAM Database Models
"""

import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _uuid():
    return str(uuid.uuid4())


def _iso(dt):
    """Serialize a stored (naive UTC) datetime with an explicit Z so browsers convert to local time."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20),
        nullable=False,
        default="user",
    )  # admin / operator / auditor / user
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    # "local" = PyPAM password, "ad" = Active Directory identity (username is user@domain)
    auth_source = db.Column(db.String(10), nullable=False, default="local")
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships (passive_deletes: let the DB / delete_user handle child rows)
    sessions = db.relationship("Session", backref="user", lazy="dynamic", passive_deletes=True)
    permissions = db.relationship("Permission", backref="user", lazy="dynamic", passive_deletes=True)
    login_logs = db.relationship("LoginLog", backref="user", lazy="dynamic", passive_deletes=True)

    VALID_ROLES = ("admin", "operator", "auditor", "user")

    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "mfa_enabled": self.mfa_enabled,
            "auth_source": self.auth_source or "local",
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
        if include_sensitive:
            data["mfa_secret"] = self.mfa_secret
        return data


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------

class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(128), nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 ready
    port = db.Column(db.Integer, nullable=False, default=22)
    asset_type = db.Column(
        db.String(20), nullable=False
    )  # linux / windows / database
    protocol = db.Column(
        db.String(20), nullable=False
    )  # ssh / rdp / mysql / postgresql / redis / mongodb
    os_info = db.Column(db.String(255), nullable=True)
    db_name = db.Column(db.String(128), nullable=True)  # For DB assets
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    # Grouping (environment / team) and free tags (comma-separated)
    group_name = db.Column(db.String(64), nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    # Health check (written by the background checker; not touching updated_at)
    health_status = db.Column(db.String(10), nullable=True)   # up / down / None = not checked
    health_detail = db.Column(db.String(255), nullable=True)
    health_checked_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    system_accounts = db.relationship("SystemAccount", backref="asset", lazy="dynamic")
    sessions = db.relationship("Session", backref="asset", lazy="dynamic")
    permissions = db.relationship("Permission", backref="asset", lazy="dynamic")

    VALID_TYPES = ("linux", "windows", "database")
    VALID_PROTOCOLS = ("ssh", "rdp", "mysql", "postgresql", "redis", "mongodb")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "port": self.port,
            "asset_type": self.asset_type,
            "protocol": self.protocol,
            "os_info": self.os_info,
            "db_name": self.db_name,
            "is_active": self.is_active,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "group_name": self.group_name or "",
            "tags": [t for t in (self.tags or "").split(",") if t],
            "health_status": self.health_status,
            "health_detail": self.health_detail,
            "health_checked_at": _iso(self.health_checked_at) if self.health_checked_at else None,
        }


# ---------------------------------------------------------------------------
# SystemAccount — credentials stored ON the target machine / DB
# ---------------------------------------------------------------------------

class SystemAccount(db.Model):
    __tablename__ = "system_accounts"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    asset_id = db.Column(
        db.String(36), db.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    username = db.Column(db.String(128), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=True)
    private_key_encrypted = db.Column(db.Text, nullable=True)
    account_type = db.Column(
        db.String(20), nullable=False, default="common"
    )  # common / admin / privileged
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    # Relationships
    permissions = db.relationship("Permission", backref="system_account", lazy="dynamic")
    sessions = db.relationship("Session", backref="system_account", lazy="dynamic")

    VALID_ACCOUNT_TYPES = ("common", "admin", "privileged")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "username": self.username,
            "account_type": self.account_type,
            "is_active": self.is_active,
            "created_at": _iso(self.created_at),
            # Never expose password_encrypted / private_key_encrypted
        }


# ---------------------------------------------------------------------------
# Permission — links PAM user → asset via system account
# ---------------------------------------------------------------------------

class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    system_account_id = db.Column(
        db.String(36),
        db.ForeignKey("system_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    actions = db.Column(
        db.String(255), nullable=False, default="connect"
    )  # comma-separated: connect,upload,download,clipboard
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    date_start = db.Column(db.DateTime, nullable=True)
    date_expired = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "asset_id": self.asset_id,
            "system_account_id": self.system_account_id,
            "actions": self.actions,
            "is_active": self.is_active,
            "date_start": self.date_start.isoformat() if self.date_start else None,
            "date_expired": self.date_expired.isoformat() if self.date_expired else None,
            "created_at": _iso(self.created_at),
        }


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    system_account_id = db.Column(
        db.String(36),
        db.ForeignKey("system_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_type = db.Column(db.String(10), nullable=False)  # ssh / db / rdp
    protocol = db.Column(db.String(20), nullable=False)
    remote_addr = db.Column(db.String(45), nullable=True)
    date_start = db.Column(db.DateTime, default=_utcnow, nullable=False)
    date_end = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_finished = db.Column(db.Boolean, default=False, nullable=False)
    command_count = db.Column(db.Integer, default=0, nullable=False)
    replay_file = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    # Relationships
    command_logs = db.relationship("CommandLog", backref="session", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "asset_id": self.asset_id,
            "system_account_id": self.system_account_id,
            "session_type": self.session_type,
            "protocol": self.protocol,
            "remote_addr": self.remote_addr,
            "date_start": _iso(self.date_start),
            "date_end": _iso(self.date_end),
            "is_active": self.is_active,
            "is_finished": self.is_finished,
            "command_count": self.command_count,
            "replay_file": self.replay_file,
            "created_at": _iso(self.created_at),
        }


# ---------------------------------------------------------------------------
# CommandLog
# ---------------------------------------------------------------------------

class CommandLog(db.Model):
    __tablename__ = "command_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(
        db.String(36),
        db.ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    input_command = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=True)
    risk_level = db.Column(
        db.String(10), nullable=False, default="normal"
    )  # normal / warning / danger
    timestamp = db.Column(db.DateTime, default=_utcnow, nullable=False)

    VALID_RISK_LEVELS = ("normal", "warning", "danger")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "asset_id": self.asset_id,
            "input_command": self.input_command,
            "output": self.output,
            "risk_level": self.risk_level,
            "timestamp": _iso(self.timestamp),
        }


# ---------------------------------------------------------------------------
# LoginLog
# ---------------------------------------------------------------------------

class LoginLog(db.Model):
    __tablename__ = "login_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    login_type = db.Column(
        db.String(10), nullable=False, default="web"
    )  # web / api / token
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    status = db.Column(
        db.String(10), nullable=False, default="success"
    )  # success / failed
    reason = db.Column(db.String(255), nullable=True)
    datetime = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "login_type": self.login_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "reason": self.reason,
            "datetime": _iso(self.datetime),
        }


# ---------------------------------------------------------------------------
# SystemSetting — dynamic UI-configured settings (e.g. AD / LDAP)
# ---------------------------------------------------------------------------

class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": _iso(self.updated_at),
        }

    @staticmethod
    def get(key: str, default: str = None) -> str:
        try:
            s = SystemSetting.query.filter_by(key=key).first()
            return s.value if s and s.value is not None else default
        except Exception:
            return default

    @staticmethod
    def set(key: str, value: str, description: str = None):
        try:
            s = SystemSetting.query.filter_by(key=key).first()
            if not s:
                s = SystemSetting(key=key, value=str(value) if value is not None else "", description=description)
                db.session.add(s)
            else:
                s.value = str(value) if value is not None else ""
                if description:
                    s.description = description
            db.session.commit()
            return s
        except Exception:
            db.session.rollback()
            raise

