"""
Overwatch SCADA - Configuration Module
Centralized configuration management
"""
import os

# Application Settings
APP_NAME = "Overwatch SCADA"
APP_VERSION = "2.0.0"
REGION = "Region 5 Bicol"

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
HTML_DIR = os.path.join(STATIC_DIR, 'html')
CSS_DIR = os.path.join(STATIC_DIR, 'css')
JS_DIR = os.path.join(STATIC_DIR, 'js')

# Google Sheets Configuration
SHEET_ID = "1f1OMSgWDZs7p7oxvsLQhNiWytlKpWaj1PLIOQgJKyKU"
SHEET_NAME = "logger"
CREDENTIALS_FILE = "credentials.json"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "7853460988:AAH3eIhrYLcu9gmVzVu2Xq-hAgs1pUJk-wU"
TELEGRAM_CHAT_IDS = ["6493927838"]

# Severity Thresholds (in meters)
SEVERITY_THRESHOLDS = {
    "CRITICAL": 2000,  # > 2000m
    "WARNING": 1000,   # 1000-2000m
    "INFO": 0          # < 1000m
}

# Refresh Intervals (in milliseconds)
REFRESH_INTERVALS = {
    "map": 3000,
    "stats": 5000,
    "logs": 5000,
    "dashboard": 5000
}

# Window Dimensions
WINDOW_SIZES = {
    "dashboard": (1200, 800),
    "map": (1400, 900),
    "stats": (1200, 800),
    "logs": (1300, 850)
}

# Map Configuration
MAP_CENTER = [13.41, 123.35]
MAP_ZOOM = 9

# Auto-open all windows on startup (for multi-monitor setups)
AUTO_OPEN_ALL_WINDOWS = False

# Debug Mode
DEBUG_MODE = True