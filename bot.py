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
        if not self.token:
            raise ValueError("❌ TELEGRAM_TOKEN not found in environment variables")
        
        self.admin_ids = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',')]
        self.ua = UserAgent()
        self.setup_database()
        
        # قائمة مواقع شوبيفاي
        self.shopify_sites = [
            "https://kith.com", "https://offwhite.com", "https://fearofgod.com",
            "https://supremenewyork.com", "https://palaceskateboards.com",
            "https://bdgastore.com", "https://undefeated.com", "https://concepts.com",
            "https://aimeleondore.com", "https://noahny.com", "https://stoneisland.com",
            "https://canadagoose.com", "https://moncler.com", "https://ssense.com",
            "https://endclothing.com", "https://slamjamsocialism.com", "https://havenshop.com",
            "https://notre-shop.com", "https://cactusplantfleamarket.com",
            "https://unionlosangeles.com", "https://bodega.com", "https://packershoes.com",
            "https://sneakerpolitics.com", "https://onenessboutique.com",
            "https://a-ma-maniere.com", "https://socialstatus.com", "https://apbstore.com",
            "https://burnrubbersneakers.com", "https://properlbc.com", "https://feature.com"
        ]
        
        print("🚀 Shopify Bot Initialized on Railway!")

    def get_db_path(self):
        """الحصول على مسار آمن للداتابيز على Railway"""
        return 'shopify_bot.db'

    def setup_database(self):
        """إعداد قاعدة البيانات"""
        self.conn = sqlite3.connect(self.get_db_path(), check_same_thread=False)
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

    def generate_token(self, user_id, username):
        """توليد توكن للمستخدم"""
        token = f"TOKEN_{user_id}_{int(time.time())}"
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, token, balance) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, token, 10.0))
        
        self.conn.commit()
        return token

    def verify_token(self, token):
        """التحقق من صحة التوكن"""
        self.cursor.execute("SELECT user_id, username, balance, is_admin FROM users WHERE token = ?", (token,))
        result = self.cursor.fetchone()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'balance': result[2],
                'is_admin': result[3]
            }
        return None

    def is_admin(self, user_id):
        """التحقق إذا كان المستخدم أدمن"""
        return user_id in self.admin_ids

    def deduct_balance(self, user_id, amount):
        """خصم رصيد من المستخدم"""
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        
        if result and result[0] >= amount:
            self.cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            self.conn.commit()
            return True
        return False

    def add_balance(self, user_id, amount):
        """إضافة رصيد للمستخدم"""
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
        return True

    async def simulate_check(self, combo, site):
        """محاكاة عملية فحص البطاقة"""
        await asyncio.sleep(2)  # محاكاة وقت الانتظار
        
        cc_number = combo.split('|')[0] if '|' in combo else combo
        results = [
            f"✅ [CHARGED] {cc_number} | ${random.uniform(1, 50):.2f} | Payment Successful",
            f"❌ [DECLINED] {cc_number} | Card Declined", 
            f"🛡️ [VBV] {cc_number} | 3D Secure Required",
            f"💰 [LIVE] {cc_number} | Card Live - ${random.uniform(10, 100):.2f}",
            f"💳 [CCN] {cc_number} | Incorrect CVC"
        ]
        
        return random.choice(results)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        token = self.generate_token(user_id, username)
        
        welcome_message = f"""
🤖 **Shopify Bot Pro - Railway Edition** 🚀

🔐 **Your Token:** `{token}`
💰 **Starting Balance:** $10.00

📋 **Available Commands:**
/check `<token>` `<site>` `<combo>` - Check a card
/balance `<token>` - Check your balance  
/sites - Show available sites
/mysites `<token>` - Show your checked sites

👑 **Admin Commands:**
/addbalance `<user_id>` `<amount>` - Add balance to user
/stats - Show bot statistics

💡 **Example:**
/check {token} kith.com 4111111111111111|12|2026|123

🔗 **Bot is running on Railway - 24/7 Uptime!**
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /check command"""
        if len(context.args) < 3:
            await update.message.reply_text("""
❌ **Usage:** 
/check `<token>` `<site>` `<combo>`

💡 **Example:**
/check TOKEN_123 kith.com 4111111111111111|12|2026|123
            """, parse_mode='Markdown')
            return
        
        token = context.args[0]
        site = context.args[1]
        combo = ' '.join(context.args[2:])
        
        user_data = self.verify_token(token)
        
        if not user_data:
            await update.message.reply_text("❌ **Invalid token!** Use /start to get a new token.")
            return
        
        # خصم الرصيد
        if not self.deduct_balance(user_data['user_id'], 1.0):
            await update.message.reply_text("❌ **Insufficient balance!** Contact admin to add balance.")
            return
        
        await update.message.reply_text("🔄 **Processing your request...**")
        
        # محاكاة الفحص
        result = await self.simulate_check(combo, site)
        
        # حفظ النتيجة
        self.cursor.execute('''
            INSERT INTO results (user_id, site, combo, result)
            VALUES (?, ?, ?, ?)
        ''', (user_data['user_id'], site, combo, result))
        self.conn.commit()
        
        # تحديث الرصيد
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_data['user_id'],))
        new_balance = self.cursor.fetchone()[0]
        
        response_message = f"""
📊 **Check Result**

🔍 **Site:** {site}
💳 **Card:** `{combo.split('|')[0]}****`
🎯 **Result:** {result}

💰 **Remaining Balance:** ${new_balance:.2f}
🆔 **User:** {user_data['username']}
        """
        
        await update.message.reply_text(response_message, parse_mode='Markdown')

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /balance command"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ **Usage:** /balance `<token>`")
            return
        
        token = context.args[0]
        user_data = self.verify_token(token)
        
        if not user_data:
            await update.message.reply_text("❌ **Invalid token!**")
            return
        
        balance_message = f"""
💰 **Account Balance**

👤 **User:** {user_data['username']}
💵 **Balance:** ${user_data['balance']:.2f}
🆔 **User ID:** {user_data['user_id']}
        """
        
        await update.message.reply_text(balance_message)

    async def sites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /sites command"""
        sites_list = "\n".join([f"• `{site}`" for site in self.shopify_sites[:15]])
        
        sites_message = f"""
🌐 **Available Shopify Sites**

{sites_list}

📝 **Total Sites:** {len(self.shopify_sites)}
💡 **Use:** /check `<token>` `<site>` `<combo>`
        """
        
        await update.message.reply_text(sites_message, parse_mode='Markdown')

    async def addbalance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /addbalance command (Admin only)"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ **Admin access required!**")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ **Usage:** /addbalance `<user_id>` `<amount>`")
            return
        
        try:
            user_id = int(context.args[0])
            amount = float(context.args[1])
            
            if self.add_balance(user_id, amount):
                await update.message.reply_text(f"✅ **Added ${amount:.2f} to user {user_id}**")
            else:
                await update.message.reply_text("❌ **Failed to add balance**")
                
        except ValueError:
            await update.message.reply_text("❌ **Invalid user_id or amount**")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /stats command (Admin only)"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ **Admin access required!**")
            return
        
        # إحصائيات البوت
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM results")
        total_checks = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT SUM(balance) FROM users")
        total_balance = self.cursor.fetchone()[0] or 0
        
        stats_message = f"""
📊 **Bot Statistics - Railway**

👥 **Total Users:** {total_users}
🔢 **Total Checks:** {total_checks}
💰 **Total Balance:** ${total_balance:.2f}
⚡ **Active Sites:** {len(self.shopify_sites)}
🏢 **Host:** Railway

🚀 **Bot is running smoothly!**
        """
        
        await update.message.reply_text(stats_message)

    async def mysites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /mysites command"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ **Usage:** /mysites `<token>`")
            return
        
        token = context.args[0]
        user_data = self.verify_token(token)
        
        if not user_data:
            await update.message.reply_text("❌ **Invalid token!**")
            return
        
        # الحصول على آخر 10 نتائج للمستخدم
        self.cursor.execute('''
            SELECT site, combo, result, created_at 
            FROM results 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user_data['user_id'],))
        
        results = self.cursor.fetchall()
        
        if not results:
            await update.message.reply_text("📭 **No checks yet!** Use /check to start.")
            return
        
        sites_list = "\n".join([f"• **{row[0]}** - `{row[1].split('|')[0]}****` - {row[2]}" for row in results])
        
        mysites_message = f"""
📋 **Your Last 10 Checks**

{sites_list}

💵 **Current Balance:** ${user_data['balance']:.2f}
        """
        
        await update.message.reply_text(mysites_message, parse_mode='Markdown')

    def setup_handlers(self, application):
        """إعداد ال handlers"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("check", self.check_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("sites", self.sites_command))
        application.add_handler(CommandHandler("addbalance", self.addbalance_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("mysites", self.mysites_command))

async def main():
    """الدالة الرئيسية"""
    print("🚀 Starting Shopify Bot on Railway...")
    
    # إنشاء البوت
    bot = ShopifyRailwayBot()
    
    # إنشاء التطبيق
    application = Application.builder().token(bot.token).build()
    
    # إعداد ال handlers
    bot.setup_handlers(application)
    
    # بدء البوت
    print("✅ Bot started successfully!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
