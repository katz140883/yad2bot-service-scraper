"""
Config module for Yad2 scraper.
This module contains configuration settings for the application.
"""
import os
import logging

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
RAW_HTML_DIR = os.path.join(RAW_DATA_DIR, 'html')
RAW_JSON_DIR = os.path.join(RAW_DATA_DIR, 'json')
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Yad2 URL configuration
BASE_URL = "https://www.yad2.co.il/realestate/rent?city=4000&property=1&rooms=3-5&price=3000-8000"

# ZenRows API configuration
ZENROWS_API_KEY = os.environ.get('ZENROWS_API_KEY', 'your_zenrows_api_key')
ZENROWS_PREMIUM = os.environ.get('ZENROWS_PREMIUM', 'true').lower() == 'true'
ZENROWS_JS_RENDER = os.environ.get('ZENROWS_JS_RENDER', 'true').lower() == 'true'
ZENROWS_ANTIBOT = os.environ.get('ZENROWS_ANTIBOT', 'true').lower() == 'true'
ZENROWS_RETRY_NUM = int(os.environ.get('ZENROWS_RETRY_NUM', '3'))

# Scheduling configuration
SCHEDULE_TIME = os.environ.get('SCHEDULE_TIME', '09:00')

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
LOG_LEVEL_NUM = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)

# Notification configuration
ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', '')
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', '')
EMAIL_SMTP_SERVER = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587'))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# Testing configuration
ENABLE_AUTOMATED_TESTING = os.environ.get('ENABLE_AUTOMATED_TESTING', 'true').lower() == 'true'
TEST_INTERVAL_HOURS = int(os.environ.get('TEST_INTERVAL_HOURS', '24'))

# Error handling configuration
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.environ.get('RETRY_DELAY_SECONDS', '5'))
ENABLE_SAFE_MODE = os.environ.get('ENABLE_SAFE_MODE', 'true').lower() == 'true'

# Extraction strategies configuration
EXTRACTION_STRATEGIES = os.environ.get('EXTRACTION_STRATEGIES', 'nextjs,html,api').split(',')
DEFAULT_EXTRACTION_STRATEGY = os.environ.get('DEFAULT_EXTRACTION_STRATEGY', 'nextjs')


# File naming configuration
TODAY_NUMBERS_FILENAME = "today_numbers.csv"
ALL_NUMBERS_FILENAME = "all_numbers.csv"

