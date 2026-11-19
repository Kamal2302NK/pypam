"""
PyPAM Configuration Module
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "pypam-super-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        f"sqlite:///{os.path.join(BASE_DIR, 'pypam.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_EXPIRY_HOURS", "8"))
    )
    # query_string lets browser downloads/new tabs (RDP file, terminal) pass ?token=
    JWT_TOKEN_LOCATION = ["headers", "query_string"]
    JWT_QUERY_STRING_NAME = "token"
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Fernet encryption key for SystemAccount credentials
    # .env / deploy.sh / docker-compose use ENCRYPTION_KEY; accept both names
    FERNET_KEY = os.getenv("FERNET_KEY") or os.getenv("ENCRYPTION_KEY") or None

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # SSH connection pool
    SSH_POOL_MAX_SIZE = int(os.getenv("SSH_POOL_MAX_SIZE", "20"))
    SSH_CONNECT_TIMEOUT = int(os.getenv("SSH_CONNECT_TIMEOUT", "10"))
    SSH_COMMAND_TIMEOUT = int(os.getenv("SSH_COMMAND_TIMEOUT", "30"))

    # Session recording - Primary directory requested by user: /data/jump-2
    SESSION_RECORDING_PATH = os.getenv("SESSION_RECORDING_PATH", "/data/jump-2/recording")
    # Older recording folders: still searched so recordings made before the move keep playing
    LEGACY_RECORDING_PATHS = [p.strip() for p in os.getenv(
        "LEGACY_RECORDING_PATHS", "/opt/pypam/data/sessions,/data/jump-2,/opt/pypam/recordings").split(",") if p.strip()]

    # Retention: older data is zipped into ARCHIVE_PATH, then removed from the live system
    ARCHIVE_PATH = os.getenv("ARCHIVE_PATH", "/data/jump-2/archive")
    VIDEO_RETENTION_DAYS = int(os.getenv("VIDEO_RETENTION_DAYS", "60"))
    AUDIT_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "180"))
    RETENTION_ENABLED = os.getenv("RETENTION_ENABLED", "true").lower() in ("true", "1", "yes")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Active Directory / LDAP Integration (for UI Console Login)
    AD_ENABLED = os.getenv("AD_ENABLED", "false").lower() in ("true", "1", "yes")
    AD_SERVER = os.getenv("AD_SERVER", "ldap://192.168.5.10")  # IP or hostname of Domain Controller
    AD_DOMAIN = os.getenv("AD_DOMAIN", "tnega.local")         # NetBIOS or DNS domain name
    AD_BASE_DN = os.getenv("AD_BASE_DN", "dc=tnega,dc=local") # Base DN for search
    AD_PORT = int(os.getenv("AD_PORT", "389"))
    AD_USE_SSL = os.getenv("AD_USE_SSL", "false").lower() in ("true", "1", "yes")
    AD_BIND_USER = os.getenv("AD_BIND_USER", "")              # Optional service user
    AD_BIND_PASSWORD = os.getenv("AD_BIND_PASSWORD", "")

    # Risk keywords for command auditing
    DANGER_COMMANDS = [
        "rm -rf",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init 0",
        "init 6",
        "> /dev/sda",
        "chmod 777",
        "DROP DATABASE",
        "DROP TABLE",
        "TRUNCATE",
        "DELETE FROM",
        "FORMAT",
    ]
    WARNING_COMMANDS = [
        "rm ",
        "kill",
        "pkill",
        "chmod",
        "chown",
        "iptables",
        "systemctl stop",
        "service stop",
        "ALTER TABLE",
        "UPDATE ",
        "GRANT ",
        "REVOKE ",
    ]


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "WARNING"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
