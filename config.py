"""
Configuration file for Shopify Checker Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8317313649:AAFZFzk_iLy6z8MHaA3oW1sYkM7qdJm8aus')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '6882342807').split(',') if x]

# Database Configuration
DATABASE_PATH = 'database/bot_database.db'

# Shopify Sites (with guest checkout enabled)
# These are real Shopify stores that support guest checkout
SHOPIFY_SITES = [
    "https://www.colourpop.com",
    "https://www.gymshark.com",
    "https://www.fashionnova.com",
    "https://www.allbirds.com",
    "https://www.mvmt.com",
    "https://bombas.com",
    "https://www.teddyfresh.com",
    "https://dryrobe.com",
    "https://www.blenderseyewear.com",
    "https://www.skinnydiplondon.com",
    "https://www.outdoorvoices.com",
    "https://www.everlane.com",
    "https://kith.com",
    "https://judy.co",
    "https://www.drinkhydrant.com",
    "https://www.chubbiesshorts.com",
    "https://www.tentree.com",
    "https://www.puravidabracelets.com",
    "https://www.mvmtwatches.com",
    "https://www.brooklinen.com",
]

# Checker Configuration
CHECK_TIMEOUT = 15
CHECK_RETRIES = 2
DELAY_BETWEEN_CHECKS = 2  # seconds

# Admin Panel Configuration
ADMIN_PANEL_HOST = '0.0.0.0'
ADMIN_PANEL_PORT = 5000
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Subscription Plans (in days)
SUBSCRIPTION_PLANS = {
    'free': 0,
    'weekly': 7,
    'monthly': 30,
    'yearly': 365,
}
