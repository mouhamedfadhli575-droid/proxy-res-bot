"""
Complete Shopify Checker Bot with Payment System and Subscription Codes
Bot By: R3D_TN⚡️
"""

import telebot
import time
import os
import threading
from datetime import datetime, timedelta
from telebot import types

# Import modules
from config import *
from database.database_v2 import Database
from modules.checker import ShopifyChecker
from modules.formatter_v2 import MessageFormatter
from modules.payment import PaymentSystem

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize database
db = Database(DATABASE_PATH)

# Initialize formatter and payment system
formatter = MessageFormatter()
payment = PaymentSystem()

# User states and checking sessions
user_states = {}
checking_sessions = {}


class CheckingSession:
    """Class to manage checking session state"""
    def __init__(self, user_id, chat_id, cards):
        self.user_id = user_id
        self.chat_id = chat_id
        self.cards = cards
        self.total = len(cards)
        self.current = 0
        self.charged = 0
        self.approved = 0
        self.risk = 0
        self.declined = 0
        self.is_paused = False
        self.is_stopped = False
        self.progress_message_id = None
        self.pinned_message_id = None
        
    def get_progress_percentage(self):
        return (self.current / self.total * 100) if self.total > 0 else 0
    
    def get_progress_bar(self, length=20):
        filled = int((self.current / self.total) * length) if self.total > 0 else 0
        return '●' * filled + '○' * (length - filled)


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


def check_user_access(user_id: int) -> tuple:
    """Check if user has access to bot - SUBSCRIPTION REQUIRED"""
    user = db.get_user(user_id)
    if not user:
        return False, "User not found. Please use /start first."
    
    if db.is_user_banned(user_id):
        return False, "banned"
    
    # Admin always has access
    if is_admin(user_id):
        return True, "ok"
    
    # Regular users MUST have active subscription
    if not db.is_user_subscribed(user_id):
        return False, "no_subscription"
    
    return True, "ok"


def create_main_menu_keyboard():
    """Create main menu keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🛠 Commands"),
        types.KeyboardButton("🧰 Tools")
    )
    markup.add(types.KeyboardButton("💰 Pricing"))
    return markup


def format_progress_message(session: CheckingSession) -> str:
    """Format the progress message with statistics"""
    progress_bar = session.get_progress_bar()
    percentage = session.get_progress_percentage()
    
    status = "⏸ Check Paused" if session.is_paused else "▶️ Checking..."
    
    message = f"""{'⏸' if session.is_paused else '📊'} {status}

📊 Progress: {percentage:.1f}%
{progress_bar}

• CHARGE 💵 ➜ [ {session.charged} ] •
• APPROVED ✅ ➜ [ {session.approved} ] •
• RISK 🔨 ➜ [ {session.risk} ] •
• DECLINED ❌ ➜ [ {session.declined} ] •
• TOTAL ⭐ ➜ [ {session.current}/{session.total} ] •

• Gate ➜ [ shopify ] •"""
    
    return message


def create_control_buttons(session: CheckingSession):
    """Create control buttons for checking"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if session.is_paused:
        markup.add(types.InlineKeyboardButton("🔄 RESUME CHECK", callback_data=f"resume_{session.user_id}"))
    else:
        markup.add(types.InlineKeyboardButton("⏸ PAUSE CHECK", callback_data=f"pause_{session.user_id}"))
    
    markup.add(types.InlineKeyboardButton("🛑 STOP CHECK", callback_data=f"stop_{session.user_id}"))
    
    return markup


@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    db.add_user(user_id, username, first_name, last_name)
    
    # Send welcome message
    welcome_text = """🌟 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 𝗕𝗼𝘁! 🌟

مرحباً بك في بوت فحص البطاقات الأكثر تطوراً! 💳

🔹 𝗖𝗮𝗿𝗱 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗼𝗻 & 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴:
- Generate and check cards easily

🔹 𝗦𝘂𝗽𝗽𝗼𝗿𝘁:
- For help contact: @Support

🎉 Enjoy your experience!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_menu_keyboard()
    )


@bot.message_handler(commands=['redeem'])
def redeem_command(message):
    """Handle /redeem command for subscription codes"""
    user_id = message.from_user.id
    
    user_states[user_id] = 'waiting_redeem_code'
    bot.send_message(
        message.chat.id,
        "🎁 أرسل كود الاشتراك الخاص بك:\n\nمثال: ABC123XYZ456"
    )


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_redeem_code')
def handle_redeem_code(message):
    """Handle redeem code input"""
    user_id = message.from_user.id
    code = message.text.strip().upper()
    
    success, result = db.redeem_subscription_code(code, user_id)
    
    if success:
        hours = result
        duration = payment.format_subscription_duration(hours)
        user = db.get_user(user_id)
        expiry = user['subscription_end']
        
        success_msg = f"""✅ 𝗖𝗼𝗱𝗲 𝗥𝗲𝗱𝗲𝗲𝗺𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!

--» 🎁 𝐂𝐨𝐝𝐞 : {code}
--» ⏰ 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧 : {duration}
--» 📅 𝐄𝐱𝐩𝐢𝐫𝐲 : {expiry}

🎊 يمكنك الآن استخدام جميع ميزات البوت!

استخدم /mass لبدء الفحص

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
        
        bot.send_message(message.chat.id, success_msg)
    else:
        bot.send_message(message.chat.id, f"❌ {result}")
    
    user_states[user_id] = None


@bot.message_handler(commands=['gencode'])
def gencode_command(message):
    """Handle /gencode command - Admin only"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "❌ هذا الأمر متاح للمسؤولين فقط")
        return
    
    user_states[user_id] = 'waiting_code_hours'
    bot.send_message(
        message.chat.id,
        "⏰ أدخل عدد الساعات للكود:\n\nمثال: 24 (ليوم واحد)\nمثال: 168 (لأسبوع واحد)"
    )


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_code_hours')
def handle_code_hours(message):
    """Handle code hours input"""
    user_id = message.from_user.id
    
    try:
        hours = int(message.text.strip())
        
        if hours < 1:
            bot.send_message(message.chat.id, "❌ الحد الأدنى هو ساعة واحدة")
            return
        
        # Generate code
        code = db.generate_code()
        
        # Add to database
        if db.add_subscription_code(code, hours, user_id):
            duration = payment.format_subscription_duration(hours)
            
            code_msg = f"""✅ 𝗖𝗼𝗱𝗲 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!

--» 🎁 𝐂𝐨𝐝𝐞 : `{code}`
--» ⏰ 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧 : {duration}
--» 📊 𝐇𝐨𝐮𝐫𝐬 : {hours}h

يمكن استخدام هذا الكود مرة واحدة فقط.

للاستخدام: /redeem {code}

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
            
            bot.send_message(message.chat.id, code_msg, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ في إنشاء الكود")
        
        user_states[user_id] = None
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال رقم صحيح")


@bot.message_handler(commands=['codes'])
def codes_command(message):
    """Handle /codes command - Admin only - List all codes"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "❌ هذا الأمر متاح للمسؤولين فقط")
        return
    
    codes = db.get_all_subscription_codes()
    
    if not codes:
        bot.send_message(message.chat.id, "📭 لا توجد أكواد اشتراك")
        return
    
    codes_text = "📋 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗖𝗼𝗱𝗲𝘀\n\n"
    
    for code_info in codes[:20]:  # Show last 20 codes
        status = "✅ Used" if code_info['is_used'] else "⏳ Available"
        duration = payment.format_subscription_duration(code_info['hours'])
        codes_text += f"• `{code_info['code']}` - {duration} - {status}\n"
    
    if len(codes) > 20:
        codes_text += f"\n... و {len(codes) - 20} كود آخر"
    
    codes_text += "\n\n--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"
    
    bot.send_message(message.chat.id, codes_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == "🛠 Commands")
def commands_menu(message):
    """Handle Commands button"""
    commands_text = """🛠 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀

/start - بدء البوت
/chg - فحص بطاقة واحدة (سريع)
/mass - فحص عدة بطاقات
/info - معلومات الاشتراك
/redeem - تفعيل كود اشتراك
/help - المساعدة

𝗔𝗱𝗺𝗶𝗻 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:
/gencode - توليد كود اشتراك
/codes - عرض جميع الأكواد

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
    
    bot.send_message(message.chat.id, commands_text)


@bot.message_handler(func=lambda message: message.text == "🧰 Tools")
def tools_menu(message):
    """Handle Tools button"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ Quick Check", callback_data="tool_chg"),
        types.InlineKeyboardButton("📦 Mass Check", callback_data="tool_mass")
    )
    markup.add(
        types.InlineKeyboardButton("ℹ️ My Info", callback_data="tool_info"),
        types.InlineKeyboardButton("🎁 Redeem Code", callback_data="tool_redeem")
    )
    
    bot.send_message(
        message.chat.id,
        "🧰 𝗧𝗼𝗼𝗹𝘀\n\nاختر أداة:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "💰 Pricing")
def pricing_menu(message):
    """Handle Pricing button"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⭐ Subscribe with Stars", callback_data="pricing_subscribe"),
        types.InlineKeyboardButton("🎁 Redeem Code", callback_data="pricing_redeem")
    )
    markup.add(
        types.InlineKeyboardButton("💝 Donate", callback_data="pricing_donate"),
        types.InlineKeyboardButton("⬅️ Back", callback_data="pricing_back")
    )
    
    bot.send_message(
        message.chat.id,
        payment.format_pricing_message(),
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('tool_'))
def handle_tool_callbacks(call):
    """Handle tool button callbacks"""
    if call.data == "tool_chg":
        chg_command(call.message)
    elif call.data == "tool_mass":
        mass_command(call.message)
    elif call.data == "tool_info":
        info_command(call.message)
    elif call.data == "tool_redeem":
        redeem_command(call.message)
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('pricing_'))
def handle_pricing_callbacks(call):
    """Handle pricing button callbacks"""
    user_id = call.from_user.id
    
    if call.data == "pricing_subscribe":
        user_states[user_id] = 'waiting_hours'
        bot.send_message(
            call.message.chat.id,
            "⏰ Please enter the number of hours you want to subscribe for (e.g. 1, 5, 12...):\n\n💡 Minimum: 1 hour\n💡 Maximum: 168 hours (1 week)",
            reply_markup=types.ForceReply()
        )
        
    elif call.data == "pricing_redeem":
        redeem_command(call.message)
        
    elif call.data == "pricing_donate":
        bot.answer_callback_query(call.id, "💝 Thank you for your support!", show_alert=True)
        
    elif call.data == "pricing_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_hours')
def handle_hours_input(message):
    """Handle hours input for subscription"""
    user_id = message.from_user.id
    
    try:
        hours = int(message.text.strip())
        
        is_valid, error_msg = payment.validate_hours(hours)
        if not is_valid:
            bot.send_message(message.chat.id, error_msg)
            return
        
        stars = payment.calculate_stars(hours)
        payload = payment.create_invoice_payload(user_id, hours)
        duration = payment.format_subscription_duration(hours)
        
        prices = [types.LabeledPrice(label=f"{duration} Subscription", amount=stars)]
        
        bot.send_invoice(
            message.chat.id,
            title=f"{duration} Subscription (full)",
            description=f"Purchase {hours} hours of full access for {stars} stars.",
            invoice_payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="subscription"
        )
        
        user_states[user_id] = None
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال رقم صحيح")


@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(pre_checkout_query):
    """Handle pre-checkout query"""
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    """Handle successful payment"""
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    payment_info = payment.parse_invoice_payload(payload)
    
    if payment_info:
        hours = payment_info['hours']
        db.update_user_subscription(user_id, 'paid', hours / 24)
        expiry_time = datetime.now() + timedelta(hours=hours)
        
        bot.send_message(
            message.chat.id,
            payment.format_payment_success(hours, expiry_time)
        )


@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    bot.send_message(message.chat.id, formatter.format_help_message())


@bot.message_handler(commands=['info'])
def info_command(message):
    """Handle /info command"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "Please use /start first.")
        return
    
    bot.send_message(message.chat.id, formatter.format_subscription_info(user))


@bot.message_handler(commands=['chg'])
def chg_command(message):
    """Handle /chg command - Quick single card check"""
    user_id = message.from_user.id
    
    has_access, reason = check_user_access(user_id)
    if not has_access:
        if reason == "banned":
            bot.send_message(message.chat.id, formatter.format_banned_message())
        elif reason == "no_subscription":
            bot.send_message(message.chat.id, formatter.format_no_subscription_message())
        else:
            bot.send_message(message.chat.id, formatter.format_error_message(reason))
        return
    
    user_states[user_id] = 'waiting_chg_card'
    
    bot.send_message(
        message.chat.id,
        "⚡ 𝗤𝘂𝗶𝗰𝗸 𝗖𝗵𝗲𝗰𝗸\n\n📝 أرسل البطاقة:\n\nnumber|month|year|cvv\n\nمثال: 5488093802407960|09|2026|954"
    )


@bot.message_handler(commands=['mass'])
def mass_command(message):
    """Handle /mass command"""
    user_id = message.from_user.id
    
    has_access, reason = check_user_access(user_id)
    if not has_access:
        if reason == "banned":
            bot.send_message(message.chat.id, formatter.format_banned_message())
        elif reason == "no_subscription":
            bot.send_message(message.chat.id, formatter.format_no_subscription_message())
        else:
            bot.send_message(message.chat.id, formatter.format_error_message(reason))
        return
    
    user_states[user_id] = 'waiting_mass_cards'
    
    bot.send_message(
        message.chat.id,
        "📦 أرسل البطاقات (كل بطاقة في سطر منفصل) أو أرسل ملف نصي:\n\nمثال:\n5488093802407960|09|2026|954\n4532123456789012|12|2025|123\n..."
    )


@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Handle file uploads"""
    user_id = message.from_user.id
    
    if user_states.get(user_id) != 'waiting_mass_cards':
        bot.send_message(message.chat.id, "يرجى استخدام /mass أولاً")
        return
    
    has_access, reason = check_user_access(user_id)
    if not has_access:
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        cards = downloaded_file.decode('utf-8').splitlines()
        cards = [card.strip() for card in cards if card.strip()]
        
        if not cards:
            bot.send_message(message.chat.id, formatter.format_error_message("الملف فارغ"))
            return
        
        process_mass_check_advanced(message, cards)
        
    except Exception as e:
        bot.send_message(message.chat.id, formatter.format_error_message(f"خطأ في قراءة الملف: {str(e)}"))
    
    user_states[user_id] = None


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Handle text messages"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    state = user_states.get(user_id)
    
    if state == 'waiting_chg_card':
        process_chg_check(message, text)
        user_states[user_id] = None
        
    elif state == 'waiting_mass_cards':
        cards = text.split('\n')
        cards = [card.strip() for card in cards if card.strip()]
        
        if not cards:
            bot.send_message(message.chat.id, formatter.format_error_message("لم يتم العثور على بطاقات"))
            return
        
        process_mass_check_advanced(message, cards)
        user_states[user_id] = None


def process_chg_check(message, card_string: str):
    """Process quick check with full response"""
    user_id = message.from_user.id
    
    checking_msg = bot.send_message(message.chat.id, "⏳ جاري الفحص...")
    
    try:
        proxies = db.get_active_proxies()
        checker = ShopifyChecker(
            sites=SHOPIFY_SITES,
            proxies=proxies,
            timeout=CHECK_TIMEOUT,
            retries=CHECK_RETRIES
        )
        
        result = checker.check_card(card_string)
        
        bot.delete_message(message.chat.id, checking_msg.message_id)
        
        # Always show full response for /chg command
        user = db.get_user(user_id)
        user_info = {
            'user_id': user_id,
            'first_name': message.from_user.first_name
        }
        
        if result['success'] and result['status'] == 'charged':
            formatted_result = formatter.format_card_result(result, user_info)
            bot.send_message(message.chat.id, formatted_result)
            
            db.add_check_history(
                user_id=user_id,
                card_number=card_string,
                result='charged',
                message=result['message'],
                gateway='Shopify GraphQL',
                site_used=result['site'],
                time_taken=result['time_taken']
            )
            db.update_statistics(success=True)
        else:
            # Show declined/failed response too
            declined_msg = f"""• 𝐑𝐞𝐬𝐮𝐥𝐭 :- 
--» 💳 𝐂𝐚𝐫𝐝 : {card_string}
--» 📌 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 : ❌ {result.get('message', 'Declined')}
--» 🌐 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗚𝗿𝗮𝗽𝗵𝗤𝗟

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
            
            bot.send_message(message.chat.id, declined_msg)
            db.update_statistics(success=False)
    
    except Exception as e:
        bot.delete_message(message.chat.id, checking_msg.message_id)
        bot.send_message(message.chat.id, formatter.format_error_message(str(e)))


def process_mass_check_advanced(message, cards: list):
    """Process multiple cards with advanced UI - Only send CHARGED cards"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    session = CheckingSession(user_id, chat_id, cards)
    checking_sessions[user_id] = session
    
    progress_msg = bot.send_message(
        chat_id,
        format_progress_message(session),
        reply_markup=create_control_buttons(session)
    )
    session.progress_message_id = progress_msg.message_id
    
    try:
        bot.pin_chat_message(chat_id, progress_msg.message_id, disable_notification=True)
        session.pinned_message_id = progress_msg.message_id
    except:
        pass
    
    thread = threading.Thread(target=check_cards_thread, args=(session,))
    thread.daemon = True
    thread.start()


def check_cards_thread(session: CheckingSession):
    """Thread function to check cards - Only send CHARGED results"""
    try:
        proxies = db.get_active_proxies()
        checker = ShopifyChecker(
            sites=SHOPIFY_SITES,
            proxies=proxies,
            timeout=CHECK_TIMEOUT,
            retries=CHECK_RETRIES
        )
        
        user = db.get_user(session.user_id)
        user_info = {
            'user_id': session.user_id,
            'first_name': user.get('first_name', 'User')
        }
        
        for i, card in enumerate(session.cards):
            if session.is_stopped:
                break
            
            while session.is_paused and not session.is_stopped:
                time.sleep(1)
            
            if session.is_stopped:
                break
            
            # Check subscription status
            if not is_admin(session.user_id) and not db.is_user_subscribed(session.user_id):
                session.is_paused = True
                bot.send_message(
                    session.chat_id,
                    formatter.format_subscription_expired_during_check(session.current, session.total)
                )
                break
            
            result = checker.check_card(card)
            session.current = i + 1
            
            if result['success'] and result['status'] == 'charged':
                session.charged += 1
                
                # Only send charged cards
                formatted_result = formatter.format_card_result(result, user_info)
                bot.send_message(session.chat_id, formatted_result)
                
                db.add_check_history(
                    user_id=session.user_id,
                    card_number=card,
                    result='charged',
                    message=result['message'],
                    gateway='Shopify GraphQL',
                    site_used=result['site'],
                    time_taken=result['time_taken']
                )
                db.update_statistics(success=True)
                
            elif 'APPROVED' in result.get('message', '').upper():
                session.approved += 1
                db.update_statistics(success=False)
            elif 'RISK' in result.get('message', '').upper():
                session.risk += 1
                db.update_statistics(success=False)
            else:
                session.declined += 1
                db.update_statistics(success=False)
            
            if session.current % 3 == 0 or session.current == session.total:
                try:
                    bot.edit_message_text(
                        format_progress_message(session),
                        session.chat_id,
                        session.progress_message_id,
                        reply_markup=create_control_buttons(session)
                    )
                except:
                    pass
            
            time.sleep(DELAY_BETWEEN_CHECKS)
        
        try:
            if session.pinned_message_id:
                bot.unpin_chat_message(session.chat_id, session.pinned_message_id)
        except:
            pass
        
        if not session.is_stopped and not session.is_paused:
            completion_msg = f"""✅ 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱!

--» 💳 𝐓𝐨𝐭𝐚𝐥 : {session.total}
--» 💵 𝐂𝐡𝐚𝐫𝐠𝐞𝐝 : {session.charged}
--» ✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 : {session.approved}
--» 🔨 𝐑𝐢𝐬𝐤 : {session.risk}
--» ❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 : {session.declined}

🎉 تم الانتهاء من الفحص!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : R3D_TN⚡️"""
            
            bot.send_message(session.chat_id, completion_msg)
        else:
            bot.send_message(session.chat_id, "🛑 تم إيقاف الفحص")
        
        if session.user_id in checking_sessions:
            del checking_sessions[session.user_id]
    
    except Exception as e:
        bot.send_message(session.chat_id, formatter.format_error_message(str(e)))
        if session.user_id in checking_sessions:
            del checking_sessions[session.user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith(('pause_', 'resume_', 'stop_')))
def handle_control_callbacks(call):
    """Handle control button callbacks"""
    user_id = call.from_user.id
    
    if user_id not in checking_sessions:
        bot.answer_callback_query(call.id, "لا يوجد فحص نشط")
        return
    
    session = checking_sessions[user_id]
    
    if call.data.startswith('pause_'):
        session.is_paused = True
        bot.answer_callback_query(call.id, "⏸ تم إيقاف الفحص مؤقتاً")
        
    elif call.data.startswith('resume_'):
        session.is_paused = False
        bot.answer_callback_query(call.id, "▶️ تم استئناف الفحص")
        
    elif call.data.startswith('stop_'):
        session.is_stopped = True
        bot.answer_callback_query(call.id, "🛑 جاري إيقاف الفحص...")
    
    try:
        bot.edit_message_text(
            format_progress_message(session),
            session.chat_id,
            session.progress_message_id,
            reply_markup=create_control_buttons(session)
        )
    except:
        pass


def main():
    """Main function to start the bot"""
    print("🤖 Shopify Checker Bot Started!")
    print(f"📊 Database: {DATABASE_PATH}")
    print(f"🌐 Shopify sites: {len(SHOPIFY_SITES)}")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Payment: Telegram Stars enabled")
    print(f"🎁 Subscription Codes: enabled")
    print(f"⚡ Bot By: R3D_TN⚡️")
    print("\n⏳ Waiting for messages...")
    
    bot.infinity_polling()


if __name__ == '__main__':
    main()
