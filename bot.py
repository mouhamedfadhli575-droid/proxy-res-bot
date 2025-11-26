#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROXY RES Bot - Complete Version v5
Features:
- Wallet System with Balance
- Heleket Payment Gateway (Auto-add balance)
- Manual Payment Methods (Admin approval)
- Admin Panel: Settings, Countries, Payment Methods, Broadcast
- Order Management System
"""

import os
import logging
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from heleket import HeleketPayment
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

# Load environment variables
if os.path.exists('config.env'):
    load_dotenv('config.env')
else:
    load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(WAITING_EMAIL, WAITING_PASSWORD, WAITING_NEW_EMAIL, WAITING_NEW_PASSWORD,
 WAITING_PAYMENT_PROOF, WAITING_PROXY_DETAILS, WAITING_PRICE_EDIT,
 WAITING_SUPPORT_USERNAME, WAITING_NEW_COUNTRY, WAITING_NEW_PAYMENT_METHOD,
 WAITING_BROADCAST_MESSAGE, WAITING_EDIT_PAYMENT_WALLET, WAITING_RECHARGE_AMOUNT,
 WAITING_HELEKET_CONFIG, WAITING_MANUAL_BALANCE_USER, WAITING_MANUAL_BALANCE_AMOUNT) = range(16)

# Configuration
ADMIN_IDS = set()
admin_ids_str = os.getenv('ADMIN_ID', '')
if admin_ids_str:
    try:
        ADMIN_IDS = set(int(id.strip()) for id in admin_ids_str.split(',') if id.strip())
    except ValueError:
        logger.error("Invalid ADMIN_ID format")

ORDERS_CHANNEL_ID = os.getenv('ORDERS_CHANNEL_ID', '')
if ORDERS_CHANNEL_ID:
    try:
        ORDERS_CHANNEL_ID = int(ORDERS_CHANNEL_ID)
    except ValueError:
        logger.error("Invalid ORDERS_CHANNEL_ID format")
        ORDERS_CHANNEL_ID = None
else:
    ORDERS_CHANNEL_ID = None

# Bot configuration (editable from admin panel)
bot_config = {
    'support_username': os.getenv('SUPPORT_USERNAME', 'ProxyResSupport'),
    'heleket_api_key': '',
    'heleket_merchant_id': '',
    'heleket_enabled': False
}

# Database (in production, use real database)
users_db = {}  # {user_id: {email, password, balance, created_at}}
logged_in_users = set()
pending_orders = {}
recharge_requests = {}  # {request_id: {user_id, amount, method, proof, status}}
order_counter = 1000
recharge_counter = 5000

# Pricing
pricing_config = {
    'duration': {'1_month': 5.0, '3_months': 12.0, '6_months': 20.0, '1_year': 35.0},
    'gb': {'10gb': 0.0, '50gb': 5.0, '100gb': 10.0, '250gb': 20.0, 'unlimited': 30.0},
    'country': {
        'random': 0.0, 'usa': 2.0, 'uk': 2.0, 'germany': 2.0, 'france': 2.0,
        'canada': 2.0, 'netherlands': 2.0, 'singapore': 3.0, 'japan': 3.0, 'australia': 3.0
    }
}

countries = {
    'random': '🌍 Random', 'usa': '🇺🇸 USA', 'uk': '🇬🇧 UK', 'germany': '🇩🇪 Germany',
    'france': '🇫🇷 France', 'canada': '🇨🇦 Canada', 'netherlands': '🇳🇱 Netherlands',
    'singapore': '🇸🇬 Singapore', 'japan': '🇯🇵 Japan', 'australia': '🇦🇺 Australia'
}

payment_methods = {
    'heleket': {'name': '💳 Heleket', 'type': 'gateway', 'enabled': True},
    'crypto_btc': {'name': '₿ Bitcoin (BTC)', 'wallet': 'YOUR_BTC_WALLET', 'type': 'manual', 'enabled': True},
    'crypto_eth': {'name': '💎 Ethereum (ETH)', 'wallet': 'YOUR_ETH_WALLET', 'type': 'manual', 'enabled': True},
    'crypto_usdt': {'name': '💵 USDT (TRC20)', 'wallet': 'YOUR_USDT_WALLET', 'type': 'manual', 'enabled': True},
    'crypto_ltc': {'name': '🔷 Litecoin (LTC)', 'wallet': 'YOUR_LTC_WALLET', 'type': 'manual', 'enabled': True},
    'crypto_trx': {'name': '🔴 TRON (TRX)', 'wallet': 'YOUR_TRX_WALLET', 'type': 'manual', 'enabled': True},
    'payeer': {'name': '💳 Payeer', 'wallet': 'YOUR_PAYEER_WALLET', 'type': 'manual', 'enabled': True},
    'binance': {'name': '🟡 Binance Pay', 'wallet': 'YOUR_BINANCE_ID', 'type': 'manual', 'enabled': True},
    'bkash': {'name': '💰 bKash', 'wallet': 'YOUR_BKASH_NUMBER', 'type': 'manual', 'enabled': True},
    'nagad': {'name': '🟠 Nagad', 'wallet': 'YOUR_NAGAD_NUMBER', 'type': 'manual', 'enabled': True},
    'rocket': {'name': '🚀 Rocket', 'wallet': 'YOUR_ROCKET_NUMBER', 'type': 'manual', 'enabled': True}
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def calculate_price(duration, gb, country):
    base = pricing_config['duration'].get(duration, 0)
    gb_price = pricing_config['gb'].get(gb, 0)
    country_price = pricing_config['country'].get(country, 0)
    return round(base + gb_price + country_price, 2)


def get_user_balance(user_id: int) -> float:
    if user_id in users_db:
        return users_db[user_id].get('balance', 0.0)
    return 0.0


def add_balance(user_id: int, amount: float):
    if user_id in users_db:
        users_db[user_id]['balance'] = users_db[user_id].get('balance', 0.0) + amount
    else:
        users_db[user_id] = {'balance': amount}


def deduct_balance(user_id: int, amount: float) -> bool:
    if user_id in users_db:
        current = users_db[user_id].get('balance', 0.0)
        if current >= amount:
            users_db[user_id]['balance'] = current - amount
            return True
    return False


# ========== HELEKET PAYMENT GATEWAY ==========

def get_heleket_client():
    """Get Heleket client instance"""
    if not bot_config['heleket_enabled']:
        return None
    return HeleketPayment(
        merchant_id=bot_config['heleket_merchant_id'],
        api_key=bot_config['heleket_api_key']
    )


# ========== START & MENUS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_admin(user_id):
        await show_admin_menu(update, context)
    elif user_id in logged_in_users:
        await show_main_menu(update, context)
    else:
        await show_welcome_menu(update, context)


async def show_welcome_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Login", callback_data="login"),
         InlineKeyboardButton("Signup", callback_data="signup")],
        [InlineKeyboardButton("Contact Support", callback_data="contact_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🌐 Welcome to PROXY RES Bot!\n\nYour trusted proxy service provider.\n\nPlease login or signup to continue:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💰 My Wallet", callback_data="my_wallet")],
        [InlineKeyboardButton("🌐 Buy New Proxy", callback_data="new_proxy")],
        [InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
         InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
        [InlineKeyboardButton("💵 Pricing", callback_data="prices"),
         InlineKeyboardButton("📞 Support", callback_data="contact_support")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🌐 PROXY RES - Main Menu\n\n💰 Balance: ${balance:.2f}\n\nWhat would you like to do?"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("💵 Edit Prices", callback_data="admin_edit_prices")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("🌍 Manage Countries", callback_data="manage_countries")],
        [InlineKeyboardButton("💳 Manage Payments", callback_data="manage_payments")],
        [InlineKeyboardButton("💰 Manage Balances", callback_data="manage_balances")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_start")],
        [InlineKeyboardButton("👤 User Mode", callback_data="user_mode")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔐 Admin Control Panel\n\nWelcome Admin!"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


# ========== WALLET SYSTEM ==========

async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    # Get recharge history
    user_recharges = [r for r in recharge_requests.values() if r['user_id'] == user_id]
    completed_recharges = [r for r in user_recharges if r['status'] == 'approved']
    total_recharged = sum(r['amount'] for r in completed_recharges)
    
    text = f"""💰 My Wallet

💵 Current Balance: ${balance:.2f}
📊 Total Recharged: ${total_recharged:.2f}
📈 Total Recharges: {len(completed_recharges)}

Recharge your wallet to buy proxies instantly!
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Recharge Balance", callback_data="recharge_balance")],
        [InlineKeyboardButton("📜 Recharge History", callback_data="recharge_history")],
        [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_recharge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    text = """💳 Recharge Balance

Please enter the amount you want to recharge (in USD):

Example: 10.50

Minimum: $5.00
Maximum: $500.00

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text)
    return WAITING_RECHARGE_AMOUNT


async def receive_recharge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.strip())
        
        if amount < 5.0:
            await update.message.reply_text("❌ Minimum recharge amount is $5.00")
            return WAITING_RECHARGE_AMOUNT
        
        if amount > 500.0:
            await update.message.reply_text("❌ Maximum recharge amount is $500.00")
            return WAITING_RECHARGE_AMOUNT
        
        context.user_data['recharge_amount'] = amount
        
        # Show payment methods
        text = f"💳 Recharge ${amount:.2f}\n\nChoose payment method:"
        
        keyboard = []
        
        # Add Heleket if enabled
        if bot_config['heleket_enabled'] and payment_methods['heleket']['enabled']:
            keyboard.append([InlineKeyboardButton("💳 Heleket (Instant)", callback_data="recharge_heleket")])
        
        # Add manual payment methods
        for key, method in payment_methods.items():
            if key != 'heleket' and method.get('enabled', True) and method.get('type') == 'manual':
                keyboard.append([InlineKeyboardButton(method['name'], callback_data=f"recharge_{key}")])
        
        keyboard.append([InlineKeyboardButton("« Cancel", callback_data="my_wallet")])
        
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
        return WAITING_RECHARGE_AMOUNT


async def process_recharge_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, method_key: str) -> int:
    query = update.callback_query
    await query.answer()
    
    amount = context.user_data.get('recharge_amount', 0)
    user_id = update.effective_user.id
    
    if method_key == 'heleket':
        # Heleket instant payment - Create invoice
        heleket = get_heleket_client()
        
        if not heleket:
            await query.answer("❌ Heleket not configured!", show_alert=True)
            return ConversationHandler.END
        
        await query.edit_message_text("🔄 Creating payment invoice... Please wait.")
        
        # Create unique order ID
        global recharge_counter
        recharge_counter += 1
        order_id = f"RC{recharge_counter}_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create invoice
        result = heleket.create_invoice(
            amount=amount,
            order_id=order_id,
            return_url=f"https://t.me/{context.bot.username}",
            success_url=f"https://t.me/{context.bot.username}",
            additional_data=f"Recharge ${amount:.2f} for User {user_id}"
        )
        
        if result['success']:
            # Store order info
            context.user_data['heleket_order_id'] = order_id
            context.user_data['heleket_amount'] = amount
            
            text = f"""💳 Heleket Payment

Amount: ${amount:.2f}
Order ID: {order_id}

🔗 Click the button below to complete payment:
"""
            
            keyboard = [
                [InlineKeyboardButton("💳 Pay Now", url=result['payment_url'])],
                [InlineKeyboardButton("✅ I've Paid - Verify", callback_data=f"verify_heleket_{order_id}")],
                [InlineKeyboardButton("« Cancel", callback_data="my_wallet")]
            ]
            
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
        else:
            await query.edit_message_text(
                f"❌ Failed to create payment invoice!\n\nError: {result.get('error', 'Unknown error')}\n\nPlease try again or contact support."
            )
            return ConversationHandler.END
    
    else:
        # Manual payment method
        method = payment_methods.get(method_key, {})
        method_name = method.get('name', method_key)
        wallet = method.get('wallet', 'NOT_CONFIGURED')
        
        text = f"""💳 {method_name}

Amount: ${amount:.2f}

📋 Payment Details:
{wallet}

Please send payment to the above address/number and send proof (screenshot or TX ID).

Your recharge will be processed after admin approval.

Send /cancel to cancel.
"""
        await query.edit_message_text(text=text)
        context.user_data['recharge_method'] = method_key
        return WAITING_PAYMENT_PROOF


async def verify_heleket_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    """Verify Heleket payment when user clicks verification button"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    await query.edit_message_text("🔄 Verifying payment with Heleket... Please wait.")
    
    heleket = get_heleket_client()
    if not heleket:
        await query.edit_message_text("❌ Heleket not configured!")
        return
    
    # Verify payment
    result = heleket.verify_payment(order_id)
    
    if result['success'] and result['paid']:
        verified_amount = result['amount']
        
        # Add balance automatically
        add_balance(user_id, verified_amount)
        
        # Log the recharge
        global recharge_counter
        recharge_counter += 1
        recharge_id = f"RC{recharge_counter}"
        recharge_requests[recharge_id] = {
            'user_id': user_id,
            'amount': verified_amount,
            'method': 'heleket',
            'order_id': order_id,
            'status': 'approved',
            'created_at': datetime.now().isoformat(),
            'approved_at': datetime.now().isoformat()
        }
        
        new_balance = get_user_balance(user_id)
        
        await query.edit_message_text(
            f"✅ Payment Verified!\n\n💰 ${verified_amount:.2f} has been added to your wallet!\n\n💵 New Balance: ${new_balance:.2f}\n\nYou can now buy proxies instantly!"
        )
    elif result['success'] and not result['paid']:
        await query.edit_message_text(
            f"⏳ Payment Pending\n\nOrder ID: {order_id}\n\nPayment not completed yet. Please complete the payment first, then click verify again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Verify Again", callback_data=f"verify_heleket_{order_id}")],
                [InlineKeyboardButton("« Back", callback_data="my_wallet")]
            ])
        )
    else:
        await query.edit_message_text(
            f"❌ Verification Failed\n\nError: {result.get('error', 'Unknown error')}\n\nPlease contact support if you've already paid.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"verify_heleket_{order_id}")],
                [InlineKeyboardButton("« Back", callback_data="my_wallet")]
            ])
        )


async def receive_recharge_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global recharge_counter
    
    user_id = update.effective_user.id
    amount = context.user_data.get('recharge_amount', 0)
    method = context.user_data.get('recharge_method', 'unknown')
    
    # Handle Heleket - This shouldn't be reached anymore as Heleket uses callback buttons
    if method == 'heleket':
        await update.message.reply_text(
            "❌ Invalid operation. Please use the payment button to complete Heleket payment."
        )
        return ConversationHandler.END
    
    # Handle manual payment proof
    else:
        proof_text = ""
        proof_file_id = None
        
        if update.message.photo:
            proof_file_id = update.message.photo[-1].file_id
            proof_text = update.message.caption or "Photo proof"
        else:
            proof_text = update.message.text
        
        # Create recharge request
        recharge_counter += 1
        recharge_id = f"RC{recharge_counter}"
        
        recharge_requests[recharge_id] = {
            'user_id': user_id,
            'amount': amount,
            'method': method,
            'proof_text': proof_text,
            'proof_file_id': proof_file_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Send to admin
        user_info = users_db.get(user_id, {})
        email = user_info.get('email', 'N/A')
        
        admin_text = f"""💰 New Recharge Request

🆔 Request ID: {recharge_id}
👤 User: {update.effective_user.first_name}
📧 Email: {email}
💵 Amount: ${amount:.2f}
💳 Method: {payment_methods.get(method, {}).get('name', method)}

📋 Proof:
{proof_text}
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_recharge_{recharge_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_recharge_{recharge_id}")]
        ]
        
        # Send to all admins
        for admin_id in ADMIN_IDS:
            try:
                if proof_file_id:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=proof_file_id,
                        caption=admin_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Recharge request submitted!\n\n🆔 Request ID: {recharge_id}\n💵 Amount: ${amount:.2f}\n\nYour balance will be updated after admin approval.\n\nYou'll receive a notification once approved!"
        )
        
        return ConversationHandler.END


async def handle_recharge_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, recharge_id: str, decision: str):
    query = update.callback_query
    
    if recharge_id not in recharge_requests:
        await query.answer("❌ Recharge request not found!", show_alert=True)
        return
    
    recharge = recharge_requests[recharge_id]
    
    if recharge['status'] != 'pending':
        await query.answer("❌ This request has already been processed!", show_alert=True)
        return
    
    user_id = recharge['user_id']
    amount = recharge['amount']
    
    if decision == 'approve':
        # Add balance to user
        add_balance(user_id, amount)
        
        recharge['status'] = 'approved'
        recharge['approved_at'] = datetime.now().isoformat()
        recharge['approved_by'] = update.effective_user.id
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Recharge Approved!\n\n💰 ${amount:.2f} has been added to your wallet!\n\nYou can now buy proxies instantly!"
            )
        except:
            pass
        
        await query.answer("✅ Recharge approved and balance added!", show_alert=True)
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ APPROVED by Admin")
    
    else:
        recharge['status'] = 'rejected'
        recharge['rejected_at'] = datetime.now().isoformat()
        recharge['rejected_by'] = update.effective_user.id
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Recharge Rejected\n\n🆔 Request ID: {recharge_id}\n💵 Amount: ${amount:.2f}\n\nPlease contact support for more information."
            )
        except:
            pass
        
        await query.answer("❌ Recharge rejected!", show_alert=True)
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ REJECTED by Admin")


async def show_recharge_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_recharges = [r for r_id, r in recharge_requests.items() if r['user_id'] == user_id]
    
    if not user_recharges:
        text = "📜 Recharge History\n\nNo recharge history yet."
    else:
        text = f"📜 Recharge History ({len(user_recharges)} recharges)\n\n"
        for r_id, r in recharge_requests.items():
            if r['user_id'] == user_id:
                status_emoji = "✅" if r['status'] == 'approved' else "⏳" if r['status'] == 'pending' else "❌"
                method_name = payment_methods.get(r['method'], {}).get('name', r['method'])
                text += f"{status_emoji} {r_id}: ${r['amount']:.2f} ({method_name})\n"
    
    keyboard = [[InlineKeyboardButton("« Back", callback_data="my_wallet")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


# ========== ADMIN: MANAGE BALANCES ==========

async def show_manage_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    total_balance = sum(u.get('balance', 0) for u in users_db.values())
    pending_recharges = sum(1 for r in recharge_requests.values() if r['status'] == 'pending')
    
    text = f"""💰 Manage User Balances

💵 Total User Balances: ${total_balance:.2f}
⏳ Pending Recharges: {pending_recharges}

What would you like to do?
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Balance Manually", callback_data="add_balance_manual")],
        [InlineKeyboardButton("📊 View All Balances", callback_data="view_all_balances")],
        [InlineKeyboardButton("« Back", callback_data="back_to_admin")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def add_balance_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """➕ Add Balance Manually

Please send the User ID:

You can find User ID from /start command or user profile.

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text)
    return WAITING_MANUAL_BALANCE_USER


async def receive_manual_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())
        context.user_data['manual_balance_user'] = user_id
        
        await update.message.reply_text(
            f"User ID: {user_id}\n\nNow send the amount to add (can be negative to deduct):\n\nExample: 10.50 or -5.00"
        )
        return WAITING_MANUAL_BALANCE_AMOUNT
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID. Please send a valid number.")
        return WAITING_MANUAL_BALANCE_USER


async def receive_manual_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
        user_id = context.user_data.get('manual_balance_user')
        
        if user_id not in users_db:
            await update.message.reply_text("❌ User not found!")
            return ConversationHandler.END
        
        old_balance = get_user_balance(user_id)
        add_balance(user_id, amount)
        new_balance = get_user_balance(user_id)
        
        await update.message.reply_text(
            f"✅ Balance updated!\n\nUser ID: {user_id}\nOld Balance: ${old_balance:.2f}\nNew Balance: ${new_balance:.2f}"
        )
        
        # Notify user
        try:
            if amount > 0:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 Balance Added!\n\n${amount:.2f} has been added to your wallet by admin!"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 Balance Deducted\n\n${abs(amount):.2f} has been deducted from your wallet by admin."
                )
        except:
            pass
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please send a valid number.")
        return WAITING_MANUAL_BALANCE_AMOUNT


async def view_all_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not users_db:
        text = "📊 User Balances\n\nNo users yet."
    else:
        text = "📊 User Balances\n\n"
        sorted_users = sorted(users_db.items(), key=lambda x: x[1].get('balance', 0), reverse=True)
        for user_id, user_data in sorted_users[:20]:  # Show top 20
            balance = user_data.get('balance', 0)
            email = user_data.get('email', 'N/A')
            text += f"💰 ${balance:.2f} - {email} (ID: {user_id})\n"
        
        if len(users_db) > 20:
            text += f"\n... and {len(users_db) - 20} more users"
    
    keyboard = [[InlineKeyboardButton("« Back", callback_data="manage_balances")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


# ========== PROXY PURCHASE (WITH BALANCE) ==========

async def show_new_proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("1 Month - $5", callback_data="duration_1_month")],
        [InlineKeyboardButton("3 Months - $12", callback_data="duration_3_months")],
        [InlineKeyboardButton("6 Months - $20", callback_data="duration_6_months")],
        [InlineKeyboardButton("1 Year - $35", callback_data="duration_1_year")],
        [InlineKeyboardButton("« Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text="🌐 New Proxy Order\n\n📅 Step 1/3: Choose Duration",
        reply_markup=reply_markup
    )


async def show_gb_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    duration = context.user_data.get('proxy_duration')
    keyboard = [
        [InlineKeyboardButton("10 GB - +$0", callback_data="gb_10gb")],
        [InlineKeyboardButton("50 GB - +$5", callback_data="gb_50gb")],
        [InlineKeyboardButton("100 GB - +$10", callback_data="gb_100gb")],
        [InlineKeyboardButton("250 GB - +$20", callback_data="gb_250gb")],
        [InlineKeyboardButton("Unlimited - +$30", callback_data="gb_unlimited")],
        [InlineKeyboardButton("« Back", callback_data="new_proxy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text=f"🌐 New Proxy Order\n\n📅 Duration: {duration}\n\n💾 Step 2/3: Choose GB Package",
        reply_markup=reply_markup
    )


async def show_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    duration = context.user_data.get('proxy_duration')
    gb = context.user_data.get('proxy_gb')
    keyboard = []
    for code, name in countries.items():
        price_add = pricing_config['country'][code]
        price_text = f" - +${price_add}" if price_add > 0 else ""
        keyboard.append([InlineKeyboardButton(f"{name}{price_text}", callback_data=f"country_{code}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_gb")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text=f"🌐 New Proxy Order\n\n📅 Duration: {duration}\n💾 GB: {gb}\n\n🌍 Step 3/3: Choose Country",
        reply_markup=reply_markup
    )


async def show_order_summary_with_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    duration = context.user_data.get('proxy_duration')
    gb = context.user_data.get('proxy_gb')
    country = context.user_data.get('proxy_country')
    duration_key = context.user_data.get('proxy_duration_key')
    gb_key = context.user_data.get('proxy_gb_key')
    country_key = context.user_data.get('proxy_country_key')
    total_price = calculate_price(duration_key, gb_key, country_key)
    
    summary = f"""📋 Order Summary

📅 Duration: {duration}
💾 GB Package: {gb}
🌍 Country: {country}

💰 Total Price: ${total_price:.2f}
💵 Your Balance: ${balance:.2f}
"""
    
    keyboard = []
    
    if balance >= total_price:
        summary += f"\n✅ Sufficient balance!"
        keyboard.append([InlineKeyboardButton("✅ Buy Now (Pay from Balance)", callback_data="buy_with_balance")])
    else:
        summary += f"\n❌ Insufficient balance!\n\nYou need ${total_price - balance:.2f} more."
        keyboard.append([InlineKeyboardButton("💳 Recharge Balance", callback_data="recharge_balance")])
    
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="back_to_menu")])
    
    await update.callback_query.edit_message_text(text=summary, reply_markup=InlineKeyboardMarkup(keyboard))


async def process_balance_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global order_counter
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    duration = context.user_data.get('proxy_duration')
    gb = context.user_data.get('proxy_gb')
    country = context.user_data.get('proxy_country')
    duration_key = context.user_data.get('proxy_duration_key')
    gb_key = context.user_data.get('proxy_gb_key')
    country_key = context.user_data.get('proxy_country_key')
    total_price = calculate_price(duration_key, gb_key, country_key)
    
    if balance < total_price:
        await query.answer("❌ Insufficient balance!", show_alert=True)
        return
    
    # Deduct balance
    if not deduct_balance(user_id, total_price):
        await query.answer("❌ Failed to deduct balance!", show_alert=True)
        return
    
    # Create order
    order_counter += 1
    order_id = f"ORD{order_counter}"
    
    pending_orders[order_id] = {
        'user_id': user_id,
        'duration': duration,
        'gb': gb,
        'country': country,
        'total_price': total_price,
        'payment_method': 'balance',
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    # Send to channel
    user_info = users_db.get(user_id, {})
    email = user_info.get('email', 'N/A')
    new_balance = get_user_balance(user_id)
    
    channel_text = f"""🌐 New Proxy Order

🆔 Order ID: {order_id}
👤 Customer: {update.effective_user.first_name}
📧 Email: {email}
💰 User Balance: ${new_balance:.2f}

📋 Order Details:
━━━━━━━━━━━━━━━━
📅 Duration: {duration}
💾 GB Package: {gb}
🌍 Country: {country}
💵 Price: ${total_price:.2f}
💳 Payment: Paid from Balance

📅 Order Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Accept Order", callback_data=f"accept_{order_id}")],
        [InlineKeyboardButton("❌ Reject Order", callback_data=f"reject_{order_id}")]
    ]
    
    if ORDERS_CHANNEL_ID:
        try:
            msg = await context.bot.send_message(
                chat_id=ORDERS_CHANNEL_ID,
                text=channel_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            pending_orders[order_id]['channel_message_id'] = msg.message_id
        except Exception as e:
            logger.error(f"Failed to send to channel: {e}")
    
    # Notify user
    await query.edit_message_text(
        f"✅ Order Placed Successfully!\n\n🆔 Order ID: {order_id}\n💰 Paid: ${total_price:.2f}\n💵 Remaining Balance: ${new_balance:.2f}\n\nYour proxy will be delivered after admin confirmation!\n\nThank you for choosing PROXY RES! 🌐"
    )


# ========== ORDER MANAGEMENT ==========

async def handle_order_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, decision: str):
    query = update.callback_query
    
    if order_id not in pending_orders:
        await query.answer("❌ Order not found!", show_alert=True)
        return
    
    order = pending_orders[order_id]
    user_id = order['user_id']
    
    if decision == "accept":
        order['status'] = 'accepted'
        order['accepted_at'] = datetime.now().isoformat()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Order Accepted!\n\n🆔 Order ID: {order_id}\n\nYour proxy is being prepared and will be delivered shortly!"
            )
        except:
            pass
        
        await query.answer("✅ Order accepted! Now send proxy details.", show_alert=True)
        
        # Update channel message
        await query.edit_message_text(
            text=f"{query.message.text}\n\n✅ ACCEPTED",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 Send Proxy Details", callback_data=f"send_proxy_{order_id}")
            ]])
        )
    
    elif decision == "reject":
        order['status'] = 'rejected'
        order['rejected_at'] = datetime.now().isoformat()
        
        # Refund if paid from balance
        if order.get('payment_method') == 'balance':
            add_balance(user_id, order['total_price'])
            refund_text = f"\n💰 ${order['total_price']:.2f} has been refunded to your wallet."
        else:
            refund_text = ""
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Order Rejected\n\n🆔 Order ID: {order_id}\n\nPlease contact support for more information.{refund_text}"
            )
        except:
            pass
        
        await query.answer("❌ Order rejected!", show_alert=True)
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ REJECTED")


async def request_proxy_details(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> int:
    query = update.callback_query
    await query.answer()
    
    if order_id not in pending_orders:
        await query.answer("❌ Order not found!", show_alert=True)
        return ConversationHandler.END
    
    context.user_data['sending_proxy_for_order'] = order_id
    
    await query.edit_message_text(
        text=f"📤 Send Proxy Details for Order {order_id}\n\nPlease send the proxy details (IP:Port:User:Pass or any format):\n\nSend /cancel to cancel."
    )
    
    return WAITING_PROXY_DETAILS


async def receive_proxy_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    order_id = context.user_data.get('sending_proxy_for_order')
    
    if not order_id or order_id not in pending_orders:
        await update.message.reply_text("❌ Order not found!")
        return ConversationHandler.END
    
    order = pending_orders[order_id]
    user_id = order['user_id']
    proxy_details = update.message.text
    
    # Send to customer
    try:
        customer_message = f"""✅ Your Proxy is Ready!

Order ID: {order_id}

🌐 Proxy Details:
━━━━━━━━━━━━━━━━
{proxy_details}
━━━━━━━━━━━━━━━━

📋 Order Info:
• Duration: {order['duration']}
• GB Package: {order['gb']}
• Country: {order['country']}

📅 Activated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
📅 Expires: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}

Thank you for choosing PROXY RES! 🌐

Need help? Contact @{bot_config['support_username']}
"""
        
        await context.bot.send_message(
            chat_id=user_id,
            text=customer_message
        )
        
        # Update order status
        order['status'] = 'completed'
        order['proxy_details'] = proxy_details
        order['completed_at'] = datetime.now().isoformat()
        
        # Confirm to admin
        await update.message.reply_text(
            f"✅ Proxy details sent successfully to customer!\n\nOrder {order_id} is now completed."
        )
        
        # Update channel message
        if ORDERS_CHANNEL_ID and 'channel_message_id' in order:
            try:
                await context.bot.edit_message_text(
                    chat_id=ORDERS_CHANNEL_ID,
                    message_id=order['channel_message_id'],
                    text=f"{update.message.reply_to_message.text if update.message.reply_to_message else ''}\n\n✅ COMPLETED"
                )
            except:
                pass
        
    except Exception as e:
        logger.error(f"Failed to send proxy details: {e}")
        await update.message.reply_text(f"❌ Failed to send to customer: {e}")
    
    return ConversationHandler.END


# ========== ADMIN: SETTINGS ==========

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    heleket_status = "✅ Enabled" if bot_config['heleket_enabled'] else "❌ Disabled"
    
    text = f"""⚙️ Bot Settings

📞 Support Username: @{bot_config['support_username']}
📢 Orders Channel: {ORDERS_CHANNEL_ID}
💳 Heleket Gateway: {heleket_status}

What would you like to configure?
"""
    keyboard = [
        [InlineKeyboardButton("📞 Edit Support Username", callback_data="edit_support_username")],
        [InlineKeyboardButton("💳 Configure Heleket", callback_data="configure_heleket")],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data="back_to_admin")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_support_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """📞 Edit Support Username

Please send the new support username (without @):

Example: ProxyResSupport

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text)
    return WAITING_SUPPORT_USERNAME


async def receive_support_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().replace('@', '')
    
    if not username or len(username) < 5:
        await update.message.reply_text("❌ Invalid username. Please try again or send /cancel.")
        return WAITING_SUPPORT_USERNAME
    
    bot_config['support_username'] = username
    
    await update.message.reply_text(
        f"✅ Support username updated to: @{username}\n\nReturning to settings..."
    )
    
    # Show settings again
    heleket_status = "✅ Enabled" if bot_config['heleket_enabled'] else "❌ Disabled"
    
    text = f"""⚙️ Bot Settings

📞 Support Username: @{bot_config['support_username']}
📢 Orders Channel: {ORDERS_CHANNEL_ID}
💳 Heleket Gateway: {heleket_status}

What would you like to configure?
"""
    keyboard = [
        [InlineKeyboardButton("📞 Edit Support Username", callback_data="edit_support_username")],
        [InlineKeyboardButton("💳 Configure Heleket", callback_data="configure_heleket")],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data="back_to_admin")]
    ]
    await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def configure_heleket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""💳 Configure Heleket Gateway

Current Status: {"✅ Enabled" if bot_config['heleket_enabled'] else "❌ Disabled"}
API Key: {"✅ Set" if bot_config['heleket_api_key'] else "❌ Not Set"}
Merchant ID: {"✅ Set" if bot_config['heleket_merchant_id'] else "❌ Not Set"}

Please send the configuration in this format:

`API_KEY|MERCHANT_ID`

Example:
`sk_live_abc123xyz|merchant_12345`

Or send "DISABLE" to disable Heleket.

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text, parse_mode='Markdown')
    return WAITING_HELEKET_CONFIG


async def receive_heleket_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.upper() == "DISABLE":
        bot_config['heleket_enabled'] = False
        await update.message.reply_text("✅ Heleket gateway disabled!")
        return ConversationHandler.END
    
    try:
        parts = text.split('|')
        if len(parts) != 2:
            raise ValueError("Invalid format")
        
        api_key, merchant_id = parts
        api_key = api_key.strip()
        merchant_id = merchant_id.strip()
        
        if not api_key or not merchant_id:
            raise ValueError("Empty values")
        
        bot_config['heleket_api_key'] = api_key
        bot_config['heleket_merchant_id'] = merchant_id
        bot_config['heleket_enabled'] = True
        
        await update.message.reply_text(
            f"✅ Heleket gateway configured!\n\nAPI Key: {api_key[:10]}...\nMerchant ID: {merchant_id}\n\nHeleket is now enabled!"
        )
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease use the correct format:\n`API_KEY|MERCHANT_ID`",
            parse_mode='Markdown'
        )
        return WAITING_HELEKET_CONFIG


# ========== ADMIN: MANAGE COUNTRIES ==========

async def manage_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🌍 Manage Countries\n\n"
    text += f"Total Countries: {len(countries)}\n\n"
    text += "Current Countries:\n"
    for key, name in countries.items():
        price = pricing_config['country'].get(key, 0)
        text += f"• {name} - ${price:.2f}\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add New Country", callback_data="add_country")],
        [InlineKeyboardButton("🗑️ Remove Country", callback_data="remove_country")],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data="back_to_admin")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def add_country_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """➕ Add New Country

Please send the country information in this format:

`country_code|Country Name|Emoji|Price`

Example:
`brazil|Brazil|🇧🇷|2.5`

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text, parse_mode='Markdown')
    return WAITING_NEW_COUNTRY


async def receive_new_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split('|')
        if len(parts) != 4:
            raise ValueError("Invalid format")
        
        code, name, emoji, price = parts
        code = code.strip().lower()
        name = name.strip()
        emoji = emoji.strip()
        price = float(price.strip())
        
        if code in countries:
            await update.message.reply_text(f"❌ Country code '{code}' already exists!")
            return WAITING_NEW_COUNTRY
        
        countries[code] = f"{emoji} {name}"
        pricing_config['country'][code] = price
        
        await update.message.reply_text(
            f"✅ Country added successfully!\n\n{emoji} {name} - ${price:.2f}"
        )
        
        # Show countries panel again
        text = "🌍 Manage Countries\n\n"
        text += f"Total Countries: {len(countries)}\n\n"
        text += "Current Countries:\n"
        for key, country_name in countries.items():
            country_price = pricing_config['country'].get(key, 0)
            text += f"• {country_name} - ${country_price:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add New Country", callback_data="add_country")],
            [InlineKeyboardButton("🗑️ Remove Country", callback_data="remove_country")],
            [InlineKeyboardButton("« Back to Admin Panel", callback_data="back_to_admin")]
        ]
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease use the correct format:\n`code|Name|Emoji|Price`",
            parse_mode='Markdown'
        )
        return WAITING_NEW_COUNTRY


async def remove_country_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if len(countries) <= 1:
        await query.edit_message_text("❌ Cannot remove all countries!")
        return ConversationHandler.END
    
    keyboard = []
    for code, name in countries.items():
        if code != 'random':  # Don't allow removing random
            keyboard.append([InlineKeyboardButton(f"🗑️ {name}", callback_data=f"remove_country_{code}")])
    
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="manage_countries")])
    
    await query.edit_message_text(
        "🗑️ Select country to remove:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def remove_country_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str):
    query = update.callback_query
    await query.answer()
    
    if country_code in countries:
        country_name = countries[country_code]
        del countries[country_code]
        if country_code in pricing_config['country']:
            del pricing_config['country'][country_code]
        
        await query.edit_message_text(f"✅ {country_name} removed successfully!")
    else:
        await query.edit_message_text("❌ Country not found!")


# ========== ADMIN: MANAGE PAYMENT METHODS ==========

async def manage_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "💳 Manage Payment Methods\n\n"
    text += f"Total Methods: {len(payment_methods)}\n\n"
    text += "Current Methods:\n"
    for key, method in payment_methods.items():
        status = "✅" if method.get('enabled', True) else "❌"
        method_type = method.get('type', 'manual')
        text += f"{status} {method['name']} ({method_type})\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Payment Method", callback_data="add_payment_method")],
        [InlineKeyboardButton("✏️ Edit Payment Method", callback_data="edit_payment_method")],
        [InlineKeyboardButton("🗑️ Remove Payment Method", callback_data="remove_payment_method")],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data="back_to_admin")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def add_payment_method_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """➕ Add New Payment Method

Please send the payment method information in this format:

`method_code|Display Name|Wallet Address`

Example:
`perfectmoney|💰 Perfect Money|U12345678`

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text, parse_mode='Markdown')
    return WAITING_NEW_PAYMENT_METHOD


async def receive_new_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split('|')
        if len(parts) != 3:
            raise ValueError("Invalid format")
        
        code, name, wallet = parts
        code = code.strip().lower()
        name = name.strip()
        wallet = wallet.strip()
        
        if code in payment_methods:
            await update.message.reply_text(f"❌ Payment method '{code}' already exists!")
            return WAITING_NEW_PAYMENT_METHOD
        
        payment_methods[code] = {'name': name, 'wallet': wallet, 'type': 'manual', 'enabled': True}
        
        await update.message.reply_text(
            f"✅ Payment method added successfully!\n\n{name}\nWallet: {wallet}"
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease use the correct format:\n`code|Name|Wallet`",
            parse_mode='Markdown'
        )
        return WAITING_NEW_PAYMENT_METHOD


async def edit_payment_method_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for code, method in payment_methods.items():
        if code != 'heleket':  # Don't allow editing Heleket here
            keyboard.append([InlineKeyboardButton(f"✏️ {method['name']}", callback_data=f"edit_payment_{code}")])
    
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="manage_payments")])
    
    await query.edit_message_text(
        "✏️ Select payment method to edit:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def edit_payment_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE, method_code: str):
    query = update.callback_query
    await query.answer()
    
    method = payment_methods.get(method_code, {})
    current_wallet = method.get('wallet', 'N/A')
    
    text = f"""✏️ Edit {method['name']}

Current Wallet: {current_wallet}

Please send the new wallet address/number:

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text)
    context.user_data['editing_payment_method'] = method_code
    return WAITING_EDIT_PAYMENT_WALLET


async def receive_payment_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method_code = context.user_data.get('editing_payment_method')
    new_wallet = update.message.text.strip()
    
    if method_code in payment_methods:
        payment_methods[method_code]['wallet'] = new_wallet
        await update.message.reply_text(
            f"✅ Wallet updated successfully!\n\n{payment_methods[method_code]['name']}\nNew Wallet: {new_wallet}"
        )
    else:
        await update.message.reply_text("❌ Payment method not found!")
    
    return ConversationHandler.END


async def remove_payment_method_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for code, method in payment_methods.items():
        if code != 'heleket':  # Don't allow removing Heleket
            keyboard.append([InlineKeyboardButton(f"🗑️ {method['name']}", callback_data=f"remove_payment_{code}")])
    
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="manage_payments")])
    
    await query.edit_message_text(
        "🗑️ Select payment method to remove:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def remove_payment_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, method_code: str):
    query = update.callback_query
    await query.answer()
    
    if method_code in payment_methods:
        method_name = payment_methods[method_code]['name']
        del payment_methods[method_code]
        await query.edit_message_text(f"✅ {method_name} removed successfully!")
    else:
        await query.edit_message_text("❌ Payment method not found!")


# ========== ADMIN: BROADCAST ==========

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""📢 Broadcast Message

Total Users: {len(users_db)}
Logged In Users: {len(logged_in_users)}

Please send the message you want to broadcast to all users.

You can send:
• Text
• Photo with caption
• Video with caption

Send /cancel to cancel.
"""
    await query.edit_message_text(text=text)
    return WAITING_BROADCAST_MESSAGE


async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # Store message for confirmation
    context.user_data['broadcast_message'] = message
    context.user_data['broadcast_step'] = 'confirm'
    
    text = f"""📢 Broadcast Preview

Message Type: {message.content_type}
Target Users: {len(users_db)}

Send "CONFIRM" to broadcast or /cancel to cancel.
"""
    await message.reply_text(text)
    return WAITING_BROADCAST_MESSAGE


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('broadcast_step') != 'confirm':
        return WAITING_BROADCAST_MESSAGE
    
    if update.message.text.upper() != "CONFIRM":
        await update.message.reply_text("❌ Cancelled. Send CONFIRM to proceed or /cancel to exit.")
        return WAITING_BROADCAST_MESSAGE
    
    broadcast_msg = context.user_data.get('broadcast_message')
    if not broadcast_msg:
        await update.message.reply_text("❌ No message to broadcast!")
        return ConversationHandler.END
    
    await update.message.reply_text("📤 Broadcasting... Please wait.")
    
    success_count = 0
    fail_count = 0
    
    for user_id in users_db.keys():
        try:
            if broadcast_msg.text:
                await context.bot.send_message(chat_id=user_id, text=broadcast_msg.text)
            elif broadcast_msg.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=broadcast_msg.photo[-1].file_id,
                    caption=broadcast_msg.caption
                )
            elif broadcast_msg.video:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=broadcast_msg.video.file_id,
                    caption=broadcast_msg.caption
                )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    
    await update.message.reply_text(
        f"""✅ Broadcast Complete!

📤 Sent: {success_count}
❌ Failed: {fail_count}
📊 Total: {len(users_db)}
"""
    )
    
    return ConversationHandler.END


# ========== ADMIN: STATISTICS & PRICES ==========

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    total_orders = len(pending_orders)
    completed = sum(1 for o in pending_orders.values() if o['status'] == 'completed')
    pending = sum(1 for o in pending_orders.values() if o['status'] == 'pending')
    revenue = sum(o['total_price'] for o in pending_orders.values() if o['status'] == 'completed')
    total_balance = sum(u.get('balance', 0) for u in users_db.values())
    
    text = f"""📊 Bot Statistics

👥 Total Users: {len(users_db)}
📦 Total Orders: {total_orders}
✅ Completed: {completed}
⏳ Pending: {pending}
💰 Revenue: ${revenue:.2f}
💵 Total User Balances: ${total_balance:.2f}
"""
    keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_admin")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_admin_edit_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("⏱️ Edit Duration Prices", callback_data="edit_duration_prices")],
        [InlineKeyboardButton("💾 Edit GB Prices", callback_data="edit_gb_prices")],
        [InlineKeyboardButton("🌍 Edit Country Prices", callback_data="edit_country_prices")],
        [InlineKeyboardButton("📋 View All Prices", callback_data="view_all_prices")],
        [InlineKeyboardButton("« Back", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text="💵 Edit Prices\n\nChoose what to edit:",
        reply_markup=reply_markup
    )


async def show_duration_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "⏱️ Duration Prices:\n\n"
    keyboard = []
    for key, price in pricing_config['duration'].items():
        name = key.replace('_', ' ').title()
        text += f"{name}: ${price:.2f}\n"
        keyboard.append([InlineKeyboardButton(f"Edit {name}", callback_data=f"edit_dur_{key}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="admin_edit_prices")])
    await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_gb_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "💾 GB Prices (Additional Cost):\n\n"
    keyboard = []
    for key, price in pricing_config['gb'].items():
        name = key.upper()
        text += f"{name}: +${price:.2f}\n"
        keyboard.append([InlineKeyboardButton(f"Edit {name}", callback_data=f"edit_gb_{key}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="admin_edit_prices")])
    await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_country_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "🌍 Country Prices (Additional Cost):\n\n"
    keyboard = []
    for key, price in pricing_config['country'].items():
        name = countries.get(key, key)
        text += f"{name}: +${price:.2f}\n"
        keyboard.append([InlineKeyboardButton(f"Edit {name}", callback_data=f"edit_country_{key}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="admin_edit_prices")])
    await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def receive_price_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_price = float(update.message.text.strip())
        editing = context.user_data.get('editing_price', '')
        
        if editing.startswith('edit_dur_'):
            key = editing.replace('edit_dur_', '')
            pricing_config['duration'][key] = new_price
            await update.message.reply_text(f"✅ Duration price updated to ${new_price:.2f}")
        
        elif editing.startswith('edit_gb_'):
            key = editing.replace('edit_gb_', '')
            pricing_config['gb'][key] = new_price
            await update.message.reply_text(f"✅ GB price updated to ${new_price:.2f}")
        
        elif editing.startswith('edit_country_'):
            key = editing.replace('edit_country_', '')
            pricing_config['country'][key] = new_price
            await update.message.reply_text(f"✅ Country price updated to ${new_price:.2f}")
        
        return ConversationHandler.END
    
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a valid number.")
        return WAITING_PRICE_EDIT


# ========== USER AUTH ==========

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip().lower()
    
    if email not in [u['email'] for u in users_db.values()]:
        await update.message.reply_text("❌ Email not found! Please signup first.")
        return ConversationHandler.END
    
    context.user_data['login_email'] = email
    await update.message.reply_text("🔐 Please enter your password:")
    return WAITING_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    email = context.user_data.get('login_email')
    user_id = update.effective_user.id
    
    user = next((u for u in users_db.values() if u['email'] == email), None)
    
    if user and user['password'] == password:
        logged_in_users.add(user_id)
        await update.message.reply_text("✅ Login successful!")
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Invalid password!")
        return ConversationHandler.END


async def receive_new_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip().lower()
    
    if '@' not in email:
        await update.message.reply_text("❌ Invalid email format!")
        return WAITING_NEW_EMAIL
    
    if email in [u['email'] for u in users_db.values()]:
        await update.message.reply_text("❌ Email already registered!")
        return WAITING_NEW_EMAIL
    
    context.user_data['signup_email'] = email
    await update.message.reply_text("🔐 Please create a password:")
    return WAITING_NEW_PASSWORD


async def receive_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    email = context.user_data.get('signup_email')
    user_id = update.effective_user.id
    
    if len(password) < 6:
        await update.message.reply_text("❌ Password must be at least 6 characters!")
        return WAITING_NEW_PASSWORD
    
    users_db[user_id] = {
        'email': email,
        'password': password,
        'balance': 0.0,
        'created_at': datetime.now().isoformat()
    }
    
    logged_in_users.add(user_id)
    
    await update.message.reply_text("✅ Registration successful!")
    await show_main_menu(update, context)
    return ConversationHandler.END


# ========== BUTTON CALLBACK HANDLER ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Recharge decisions
    if data.startswith("approve_recharge_"):
        recharge_id = data.replace("approve_recharge_", "")
        await handle_recharge_decision(update, context, recharge_id, "approve")
        return ConversationHandler.END
    
    elif data.startswith("reject_recharge_"):
        recharge_id = data.replace("reject_recharge_", "")
        await handle_recharge_decision(update, context, recharge_id, "reject")
        return ConversationHandler.END
    
    # Order decisions
    elif data.startswith("accept_"):
        order_id = data.replace("accept_", "")
        await handle_order_decision(update, context, order_id, "accept")
        return ConversationHandler.END
    
    elif data.startswith("reject_"):
        order_id = data.replace("reject_", "")
        await handle_order_decision(update, context, order_id, "reject")
        return ConversationHandler.END
    
    elif data.startswith("send_proxy_"):
        order_id = data.replace("send_proxy_", "")
        return await request_proxy_details(update, context, order_id)
    
    # Admin
    elif data == "admin_stats":
        if not is_admin(user_id):
            await query.answer("⛔ Access denied!", show_alert=True)
            return ConversationHandler.END
        await show_admin_stats(update, context)
        return ConversationHandler.END
    
    elif data == "admin_edit_prices":
        await show_admin_edit_prices(update, context)
        return ConversationHandler.END
    
    elif data == "admin_settings":
        await admin_settings(update, context)
        return ConversationHandler.END
    
    elif data == "edit_support_username":
        return await edit_support_username(update, context)
    
    elif data == "configure_heleket":
        return await configure_heleket(update, context)
    
    elif data == "manage_countries":
        await manage_countries(update, context)
        return ConversationHandler.END
    
    elif data == "add_country":
        return await add_country_start(update, context)
    
    elif data == "remove_country":
        await remove_country_start(update, context)
        return ConversationHandler.END
    
    elif data.startswith("remove_country_"):
        country_code = data.replace("remove_country_", "")
        await remove_country_confirm(update, context, country_code)
        return ConversationHandler.END
    
    elif data == "manage_payments":
        await manage_payments(update, context)
        return ConversationHandler.END
    
    elif data == "add_payment_method":
        return await add_payment_method_start(update, context)
    
    elif data == "edit_payment_method":
        await edit_payment_method_start(update, context)
        return ConversationHandler.END
    
    elif data.startswith("edit_payment_"):
        method_code = data.replace("edit_payment_", "")
        return await edit_payment_wallet_start(update, context, method_code)
    
    elif data == "remove_payment_method":
        await remove_payment_method_start(update, context)
        return ConversationHandler.END
    
    elif data.startswith("remove_payment_"):
        method_code = data.replace("remove_payment_", "")
        await remove_payment_confirm(update, context, method_code)
        return ConversationHandler.END
    
    elif data == "manage_balances":
        await show_manage_balances(update, context)
        return ConversationHandler.END
    
    elif data == "add_balance_manual":
        return await add_balance_manual_start(update, context)
    
    elif data == "view_all_balances":
        await view_all_balances(update, context)
        return ConversationHandler.END
    
    elif data == "broadcast_start":
        return await broadcast_start(update, context)
    
    elif data == "edit_duration_prices":
        await show_duration_prices(update, context)
        return ConversationHandler.END
    
    elif data == "edit_gb_prices":
        await show_gb_prices(update, context)
        return ConversationHandler.END
    
    elif data == "edit_country_prices":
        await show_country_prices(update, context)
        return ConversationHandler.END
    
    elif data.startswith("edit_dur_") or data.startswith("edit_gb_") or data.startswith("edit_country_"):
        context.user_data['editing_price'] = data
        await query.edit_message_text("💵 Enter new price (numbers only, e.g., 10.50):")
        return WAITING_PRICE_EDIT
    
    elif data == "view_all_prices":
        text = "💵 All Current Prices:\n\n⏱️ Duration:\n"
        for k, v in pricing_config['duration'].items():
            text += f"  {k.replace('_', ' ').title()}: ${v:.2f}\n"
        text += "\n💾 GB (Additional):\n"
        for k, v in pricing_config['gb'].items():
            text += f"  {k.upper()}: +${v:.2f}\n"
        text += "\n🌍 Countries (Additional):\n"
        for k, v in pricing_config['country'].items():
            text += f"  {countries.get(k, k)}: +${v:.2f}\n"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="admin_edit_prices")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "back_to_admin":
        await show_admin_menu(update, context)
        return ConversationHandler.END
    
    elif data == "user_mode":
        if user_id in logged_in_users:
            await show_main_menu(update, context)
        else:
            await show_welcome_menu(update, context)
        return ConversationHandler.END
    
    # User flows
    elif data == "login":
        await query.edit_message_text("📧 Please enter your email:")
        return WAITING_EMAIL
    
    elif data == "signup":
        await query.edit_message_text("📧 Please enter your email for registration:")
        return WAITING_NEW_EMAIL
    
    elif data == "my_wallet":
        await show_wallet(update, context)
        return ConversationHandler.END
    
    elif data == "recharge_balance":
        return await show_recharge_menu(update, context)
    
    elif data == "recharge_history":
        await show_recharge_history(update, context)
        return ConversationHandler.END
    
    elif data.startswith("verify_heleket_"):
        order_id = data.replace("verify_heleket_", "")
        await verify_heleket_payment_callback(update, context, order_id)
        return ConversationHandler.END
    
    elif data.startswith("recharge_"):
        method_key = data.replace("recharge_", "")
        return await process_recharge_payment(update, context, method_key)
    
    elif data == "new_proxy":
        await show_new_proxy_menu(update, context)
        return ConversationHandler.END
    
    elif data.startswith("duration_"):
        duration_key = data.replace("duration_", "")
        duration_name = duration_key.replace('_', ' ').title()
        context.user_data['proxy_duration'] = duration_name
        context.user_data['proxy_duration_key'] = duration_key
        await show_gb_selection(update, context)
        return ConversationHandler.END
    
    elif data.startswith("gb_"):
        gb_key = data.replace("gb_", "")
        gb_name = gb_key.upper()
        context.user_data['proxy_gb'] = gb_name
        context.user_data['proxy_gb_key'] = gb_key
        await show_country_selection(update, context)
        return ConversationHandler.END
    
    elif data.startswith("country_"):
        country_key = data.replace("country_", "")
        country_name = countries.get(country_key, country_key)
        context.user_data['proxy_country'] = country_name
        context.user_data['proxy_country_key'] = country_key
        await show_order_summary_with_balance(update, context)
        return ConversationHandler.END
    
    elif data == "buy_with_balance":
        await process_balance_purchase(update, context)
        return ConversationHandler.END
    
    elif data == "back_to_gb":
        await show_gb_selection(update, context)
        return ConversationHandler.END
    
    elif data == "my_orders":
        user_orders = [o for o in pending_orders.values() if o['user_id'] == user_id]
        if user_orders:
            text = f"📋 Your Orders ({len(user_orders)}):\n\n"
            for order_id, order in pending_orders.items():
                if order['user_id'] == user_id:
                    status_emoji = "✅" if order['status'] == 'completed' else "⏳" if order['status'] == 'pending' else "❌"
                    text += f"{status_emoji} {order_id}: {order['country']} - ${order['total_price']:.2f}\n"
        else:
            text = "📋 You don't have any orders yet.\n\nClick 'Buy New Proxy' to get started!"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "my_profile":
        user_data = users_db.get(user_id, {})
        balance = get_user_balance(user_id)
        email = user_data.get('email', 'N/A')
        created = user_data.get('created_at', 'N/A')
        
        text = f"""👤 My Profile

📧 Email: {email}
💰 Balance: ${balance:.2f}
📅 Member Since: {created[:10] if created != 'N/A' else 'N/A'}
🆔 User ID: {user_id}
"""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "prices":
        text = "💵 Pricing Information\n\n"
        text += "⏱️ Duration Prices:\n"
        for k, v in pricing_config['duration'].items():
            text += f"  • {k.replace('_', ' ').title()}: ${v:.2f}\n"
        text += "\n💾 GB Packages (Additional):\n"
        for k, v in pricing_config['gb'].items():
            text += f"  • {k.upper()}: +${v:.2f}\n"
        text += "\n🌍 Country Selection (Additional):\n"
        for k, v in pricing_config['country'].items():
            text += f"  • {countries.get(k, k)}: +${v:.2f}\n"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "contact_support":
        text = f"📞 Contact Support\n\nFor any questions or issues, please contact:\n\n@{bot_config['support_username']}"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "logout":
        logged_in_users.discard(user_id)
        await query.edit_message_text("👋 Logged out successfully!")
        await show_welcome_menu(update, context)
        return ConversationHandler.END
    
    elif data == "back_to_menu":
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END


# ========== MAIN ==========

def main() -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return
    
    if not ADMIN_IDS:
        logger.warning("ADMIN_ID not configured!")
    else:
        logger.info(f"Admin IDs: {ADMIN_IDS}")
    
    if not ORDERS_CHANNEL_ID:
        logger.warning("ORDERS_CHANNEL_ID not configured! Orders won't be sent to channel.")
    else:
        logger.info(f"Orders Channel: {ORDERS_CHANNEL_ID}")
    
    application = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(button_callback)
        ],
        states={
            WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            WAITING_NEW_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_email)],
            WAITING_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_password)],
            WAITING_PAYMENT_PROOF: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, receive_recharge_proof)],
            WAITING_PROXY_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_proxy_details)],
            WAITING_PRICE_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price_edit)],
            WAITING_SUPPORT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_username)],
            WAITING_NEW_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_country)],
            WAITING_NEW_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_payment_method)],
            WAITING_BROADCAST_MESSAGE: [MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, lambda u, c: receive_broadcast_message(u, c) if c.user_data.get('broadcast_step') != 'confirm' else confirm_broadcast(u, c))],
            WAITING_EDIT_PAYMENT_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_wallet)],
            WAITING_RECHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_recharge_amount)],
            WAITING_HELEKET_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_heleket_config)],
            WAITING_MANUAL_BALANCE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_balance_user)],
            WAITING_MANUAL_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_balance_amount)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(button_callback)
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    logger.info("🚀 PROXY RES Bot v5 started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
