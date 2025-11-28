import os
import asyncio
import sqlite3
import requests
import random
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from fake_useragent import UserAgent

class ShopifyRailwayBot:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_TOKEN')
        
        # إذا لم يوجد التوكن، استخدم وضع التطوير
        if not self.token:
            print("⚠️  TELEGRAM_TOKEN not found. Running in development mode.")
            print("ℹ️  Please set TELEGRAM_TOKEN environment variable on Railway")
            # يمكنك إضافة منطق بديل هنا أو الخروج
            self.token = "DEV_MODE_TOKEN"  # توكن مؤقت للتطوير
        
        self.admin_ids = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',')]
        self.ua = UserAgent()
        self.setup_database()
        
        # قائمة مواقع شوبيفاي
        self.shopify_sites = [
            "https://kith.com", "https://offwhite.com", "https://fearofgod.com",
            "https://supremenewyork.com", "https://palaceskateboards.com",
            "https://bdgastore.com", "https://undefeated.com", "https://concepts.com",
            # ... باقي المواقع
        ]
        
        print("🚀 Shopify Bot Initialized!")

    def setup_database(self):
        """إعداد قاعدة البيانات"""
        try:
            self.conn = sqlite3.connect('shopify_bot.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # إنشاء الجداول
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    token TEXT UNIQUE,
                    balance REAL DEFAULT 10.0,
                    is_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    site TEXT,
                    combo TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # إضافة الأدمن الافتراضي
            for admin_id in self.admin_ids:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, token, balance, is_admin) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (admin_id, f'admin_{admin_id}', f'ADMIN_{admin_id}', 1000.0, 1))
            
            self.conn.commit()
            print("✅ Database setup completed")
        except Exception as e:
            print(f"❌ Database setup failed: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        token = self.generate_token(user_id, username)
        
        welcome_message = f"""
🤖 **Shopify Bot Pro** 🚀

🔐 **Your Token:** `{token}`
💰 **Starting Balance:** $10.00

📋 **Available Commands:**
/check `<token>` `<site>` `<combo>` - Check a card
/balance `<token>` - Check your balance  
/sites - Show available sites

💡 **Example:**
/check {token} kith.com 4111111111111111|12|2026|123

{'⚠️ **DEV MODE** - Token not set on Railway' if not os.environ.get('TELEGRAM_TOKEN') else '✅ **Production Mode**'}
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    def generate_token(self, user_id, username):
        """توليد توكن للمستخدم"""
        token = f"TOKEN_{user_id}_{int(time.time())}"
        
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, token, balance) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, token, 10.0))
            
            self.conn.commit()
            return token
        except Exception as e:
            print(f"❌ Token generation failed: {e}")
            return f"ERROR_{user_id}"

    # ... باقي الدوال بنفس الطريقة

async def main():
    """الدالة الرئيسية"""
    print("🚀 Starting Shopify Bot...")
    
    try:
        # إنشاء البوت
        bot = ShopifyRailwayBot()
        
        # إذا كان في وضع التطوير، لا تشغل بوت التليجرام
        if not os.environ.get('TELEGRAM_TOKEN'):
            print("🛑 Running in development mode - Telegram bot disabled")
            print("💡 Set TELEGRAM_TOKEN environment variable to enable the bot")
            # استمر في تشغيل خادم الويب فقط
            while True:
                time.sleep(10)
            return
        
        # إنشاء التطبيق
        application = Application.builder().token(bot.token).build()
        
        # إعداد ال handlers
        bot.setup_handlers(application)
        
        # بدء البوت
        print("✅ Bot started successfully!")
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        print("💡 Check your TELEGRAM_TOKEN and try again")

if __name__ == "__main__":
    asyncio.run(main())
