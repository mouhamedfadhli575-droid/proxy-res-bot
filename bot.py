#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROXY RES Bot - Fixed Version
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
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
 WAITING_WALLET_EDIT) = range(8)

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

# Database
users_db = {}
logged_in_users = set()
pending_orders = {}
order_counter = 1000

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
    'crypto_btc': {'name': '₿ Bitcoin (BTC)', 'wallet': 'YOUR_BTC_WALLET', 'enabled': True},
    'crypto_eth': {'name': '💎 Ethereum (ETH)', 'wallet': 'YOUR_ETH_WALLET', 'enabled': True},
    'crypto_usdt': {'name': '💵 USDT (TRC20)', 'wallet': 'YOUR_USDT_WALLET', 'enabled': True},
    'crypto_ltc': {'name': '🔷 Litecoin (LTC)', 'wallet': 'YOUR_LTC_WALLET', 'enabled': True},
    'crypto_trx': {'name': '🔴 TRON (TRX)', 'wallet': 'YOUR_TRX_WALLET', 'enabled': True},
    'payeer': {'name': '💳 Payeer', 'wallet': 'YOUR_PAYEER_WALLET', 'enabled': True},
    'binance': {'name': '🟡 Binance Pay', 'wallet': 'YOUR_BINANCE_ID', 'enabled': True},
    'bkash': {'name': '💰 bKash', 'wallet': 'YOUR_BKASH_NUMBER', 'enabled': True},
    'nagad': {'name': '🟠 Nagad', 'wallet': 'YOUR_NAGAD_NUMBER', 'enabled': True},
    'rocket': {'name': '🚀 Rocket', 'wallet': 'YOUR_ROCKET_NUMBER', 'enabled': True}
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def calculate_price(duration, gb, country):
    base = pricing_config['duration'].get(duration, 0)
    gb_price = pricing_config['gb'].get(gb, 0)
    country_price = pricing_config['country'].get(country, 0)
    return round(base + gb_price + country_price, 2)


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
    keyboard = [
        [InlineKeyboardButton("🌐 Buy New Proxy", callback_data="new_proxy")],
        [InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
         InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
        [InlineKeyboardButton("💵 Pricing", callback_data="prices"),
         InlineKeyboardButton("📞 Support", callback_data="contact_support")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🌐 PROXY RES - Main Menu\n\nWhat would you like to do?"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("💵 Edit Prices", callback_data="admin_edit_prices")],
        [InlineKeyboardButton("💳 Payment Methods", callback_data="admin_payment_methods")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("👤 User Mode", callback_data="user_mode")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔐 Admin Control Panel\n\nWelcome Admin!"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def show_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin settings menu."""
    keyboard = [
        [InlineKeyboardButton("📢 Orders Channel", callback_data="settings_channel")],
        [InlineKeyboardButton("👥 Admin List", callback_data="settings_admins")],
        [InlineKeyboardButton("📞 Support Contact", callback_data="settings_support")],
        [InlineKeyboardButton("« Back", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    channel_status = f"✅ Connected: {ORDERS_CHANNEL_ID}" if ORDERS_CHANNEL_ID else "❌ Not configured"
    admin_count = len(ADMIN_IDS)
    
    text = f"""⚙️ Bot Settings

📢 Orders Channel: {channel_status}
👥 Admins: {admin_count}
📞 Support: @YourSupport

Configure your bot settings here.
"""
    
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)


async def show_payment_methods_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show payment methods management."""
    keyboard = []
    
    text = "💳 Payment Methods Management\n\n"
    
    for key, method in payment_methods.items():
        status = "✅" if method.get('enabled', True) else "❌"
        text += f"{status} {method['name']}\n"
        text += f"   Wallet: {method['wallet']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"Edit {method['name']}", callback_data=f"edit_payment_{key}")
        ])
    
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)


async def show_edit_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE, method_key: str) -> int:
    """Show edit options for a payment method."""
    method = payment_methods.get(method_key, {})
    
    keyboard = [
        [InlineKeyboardButton("📝 Edit Wallet Address", callback_data=f"edit_wallet_{method_key}")],
        [InlineKeyboardButton("🔄 Toggle Enable/Disable", callback_data=f"toggle_payment_{method_key}")],
        [InlineKeyboardButton("« Back", callback_data="admin_payment_methods")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "✅ Enabled" if method.get('enabled', True) else "❌ Disabled"
    
    text = f"""💳 Edit Payment Method

Name: {method['name']}
Status: {status}
Wallet: {method['wallet']}

Choose an action:
"""
    
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    return ConversationHandler.END


async def request_wallet_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, method_key: str) -> int:
    """Request new wallet address."""
    context.user_data['editing_wallet'] = method_key
    method = payment_methods.get(method_key, {})
    
    await update.callback_query.edit_message_text(
        text=f"💳 Edit {method['name']}\n\nCurrent wallet: {method['wallet']}\n\nPlease send the new wallet address:"
    )
    return WAITING_WALLET_EDIT


async def receive_wallet_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and save new wallet address."""
    method_key = context.user_data.get('editing_wallet')
    new_wallet = update.message.text.strip()
    
    if method_key and method_key in payment_methods:
        payment_methods[method_key]['wallet'] = new_wallet
        await update.message.reply_text(f"✅ Wallet address updated successfully!\n\nNew address: {new_wallet}")
    else:
        await update.message.reply_text("❌ Error updating wallet address!")
    
    await show_admin_menu(update, context)
    return ConversationHandler.END


async def toggle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE, method_key: str) -> None:
    """Toggle payment method enabled/disabled."""
    if method_key in payment_methods:
        current_status = payment_methods[method_key].get('enabled', True)
        payment_methods[method_key]['enabled'] = not current_status
        new_status = "✅ Enabled" if not current_status else "❌ Disabled"
        
        await update.callback_query.answer(f"Payment method {new_status}!", show_alert=True)
        await show_edit_payment_method(update, context, method_key)


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


async def show_order_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

Please choose a payment method:
"""
    
    keyboard = []
    for key, method in payment_methods.items():
        if method.get('enabled', True):
            keyboard.append([InlineKeyboardButton(method['name'], callback_data=f"pay_{key}")])
    
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=summary, reply_markup=reply_markup)


async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, method_key: str) -> int:
    method = payment_methods.get(method_key, {})
    method_name = method.get('name', method_key)
    wallet = method.get('wallet', 'NOT_CONFIGURED')
    
    duration_key = context.user_data.get('proxy_duration_key')
    gb_key = context.user_data.get('proxy_gb_key')
    country_key = context.user_data.get('proxy_country_key')
    total_price = calculate_price(duration_key, gb_key, country_key)
    
    context.user_data['payment_method'] = method_name
    context.user_data['payment_method_key'] = method_key
    context.user_data['total_price'] = total_price
    
    text = f"""💳 Payment Instructions

Payment Method: {method_name}
Amount: ${total_price:.2f}

📍 Send payment to:
{wallet}

⚠️ Important:
1. Send EXACTLY ${total_price:.2f}
2. After payment, send proof here:
   • Screenshot of transaction
   • OR Transaction ID (TX ID)

📸 Please send your payment proof now:
"""
    
    keyboard = [[InlineKeyboardButton("« Cancel Order", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    return WAITING_PAYMENT_PROOF


async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global order_counter
    user = update.effective_user
    user_id = user.id
    username = user.username or "No username"
    full_name = user.full_name or "No name"
    
    duration = context.user_data.get('proxy_duration')
    gb = context.user_data.get('proxy_gb')
    country = context.user_data.get('proxy_country')
    payment_method = context.user_data.get('payment_method')
    total_price = context.user_data.get('total_price')
    
    order_id = f"ORD{order_counter}"
    order_counter += 1
    
    pending_orders[order_id] = {
        'user_id': user_id,
        'username': username,
        'full_name': full_name,
        'duration': duration,
        'gb': gb,
        'country': country,
        'payment_method': payment_method,
        'total_price': total_price,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    order_message = f"""🆕 NEW ORDER - {order_id}

👤 Customer Info:
• Name: {full_name}
• Username: @{username}
• User ID: {user_id}

📦 Order Details:
• Duration: {duration}
• GB Package: {gb}
• Country: {country}

💰 Payment:
• Method: {payment_method}
• Amount: ${total_price:.2f}

📅 Order Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    if ORDERS_CHANNEL_ID:
        try:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Accept", callback_data=f"accept_{order_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            channel_msg = await context.bot.send_message(
                chat_id=ORDERS_CHANNEL_ID,
                text=order_message,
                reply_markup=reply_markup
            )
            
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=ORDERS_CHANNEL_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=f"💳 Payment Proof for {order_id}"
                )
            elif update.message.text:
                await context.bot.send_message(
                    chat_id=ORDERS_CHANNEL_ID,
                    text=f"💳 Payment Proof for {order_id}:\n\n{update.message.text}"
                )
            
            pending_orders[order_id]['channel_message_id'] = channel_msg.message_id
            
        except Exception as e:
            logger.error(f"Failed to send to channel: {e}")
    
    await update.message.reply_text(
        f"""✅ Order Submitted Successfully!

Order ID: {order_id}

Your order has been received and is being processed.
You will be notified once it's approved.

⏱️ Processing Time: Usually 5-30 minutes
📞 Need help? Contact support

Thank you for choosing PROXY RES! 🌐
"""
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END


async def handle_order_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, decision: str) -> None:
    query = update.callback_query
    await query.answer()
    
    if order_id not in pending_orders:
        await query.edit_message_text("❌ Order not found or already processed.")
        return
    
    order = pending_orders[order_id]
    user_id = order['user_id']
    
    if decision == "accept":
        order['status'] = 'accepted'
        
        updated_text = query.message.text + "\n\n✅ ACCEPTED - Waiting for proxy details..."
        keyboard = [[InlineKeyboardButton("📝 Send Proxy Details", callback_data=f"send_proxy_{order_id}")]]
        await query.edit_message_text(text=updated_text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""✅ Order Approved!

Order ID: {order_id}

Your order has been approved!
We are preparing your proxy details now.

You will receive your proxy information shortly.

Thank you for your patience! 🌐
"""
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
    
    elif decision == "reject":
        order['status'] = 'rejected'
        
        updated_text = query.message.text + "\n\n❌ REJECTED"
        await query.edit_message_text(text=updated_text)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""❌ Order Rejected

Order ID: {order_id}

Unfortunately, your order has been rejected.
This may be due to:
• Invalid payment proof
• Incorrect payment amount
• Payment not received

Please contact support for more information.
📞 Support: @YourSupport
"""
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")


async def request_proxy_details(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> int:
    query = update.callback_query
    await query.answer()
    
    if order_id not in pending_orders:
        await query.answer("❌ Order not found!", show_alert=True)
        return ConversationHandler.END
    
    context.user_data['sending_proxy_for_order'] = order_id
    
    await query.edit_message_text(
        text=f"""📝 Send Proxy Details for {order_id}

Please send the proxy details in any format.

Example:
Host: proxy.example.com
Port: 8080
Username: user123
Password: pass123
Protocol: HTTP/HTTPS/SOCKS5

The message will be forwarded to the customer.
"""
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

Thank you for choosing PROXY RES! 🌐

Need help? Contact @YourSupport
"""
        
        await context.bot.send_message(
            chat_id=user_id,
            text=customer_message
        )
        
        order['status'] = 'completed'
        order['proxy_details'] = proxy_details
        order['completed_at'] = datetime.now().isoformat()
        
        await update.message.reply_text(
            f"✅ Proxy details sent successfully to customer!\n\nOrder {order_id} is now completed."
        )
        
        if ORDERS_CHANNEL_ID and 'channel_message_id' in order:
            try:
                original_text = f"""🆕 NEW ORDER - {order_id}

👤 Customer Info:
• Name: {order['full_name']}
• Username: @{order['username']}
• User ID: {order['user_id']}

📦 Order Details:
• Duration: {order['duration']}
• GB Package: {order['gb']}
• Country: {order['country']}

💰 Payment:
• Method: {order['payment_method']}
• Amount: ${order['total_price']:.2f}

📅 Order Time: {order['timestamp']}

✅ COMPLETED"""
                
                await context.bot.edit_message_text(
                    chat_id=ORDERS_CHANNEL_ID,
                    message_id=order['channel_message_id'],
                    text=original_text
                )
            except Exception as e:
                logger.error(f"Failed to update channel message: {e}")
        
    except Exception as e:
        logger.error(f"Failed to send proxy details: {e}")
        await update.message.reply_text(f"❌ Failed to send to customer: {e}")
    
    return ConversationHandler.END


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


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Order decisions
    if data.startswith("accept_"):
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
        
        total_orders = len(pending_orders)
        completed = sum(1 for o in pending_orders.values() if o['status'] == 'completed')
        pending = sum(1 for o in pending_orders.values() if o['status'] == 'pending')
        revenue = sum(o['total_price'] for o in pending_orders.values() if o['status'] == 'completed')
        
        text = f"""📊 Bot Statistics

👥 Total Users: {len(users_db)}
📦 Total Orders: {total_orders}
✅ Completed: {completed}
⏳ Pending: {pending}
💰 Revenue: ${revenue:.2f}
"""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_admin")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "admin_settings":
        await show_admin_settings(update, context)
        return ConversationHandler.END
    
    elif data == "admin_payment_methods":
        await show_payment_methods_admin(update, context)
        return ConversationHandler.END
    
    elif data.startswith("edit_payment_"):
        method_key = data.replace("edit_payment_", "")
        return await show_edit_payment_method(update, context, method_key)
    
    elif data.startswith("edit_wallet_"):
        method_key = data.replace("edit_wallet_", "")
        return await request_wallet_edit(update, context, method_key)
    
    elif data.startswith("toggle_payment_"):
        method_key = data.replace("toggle_payment_", "")
        await toggle_payment_method(update, context, method_key)
        return ConversationHandler.END
    
    elif data == "admin_edit_prices":
        await show_admin_edit_prices(update, context)
        return ConversationHandler.END
    
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
        await show_order_summary(update, context)
        return ConversationHandler.END
    
    elif data == "back_to_gb":
        await show_gb_selection(update, context)
        return ConversationHandler.END
    
    elif data.startswith("pay_"):
        method_key = data.replace("pay_", "")
        return await show_payment_instructions(update, context, method_key)
    
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
        order_count = sum(1 for o in pending_orders.values() if o['user_id'] == user_id)
        text = f"""👤 Your Profile

🆔 User ID: {user_id}
📦 Total Orders: {order_count}
📅 Member Since: Today

💡 Need help? Contact @YourSupport
"""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "prices":
        text = "💵 Proxy Pricing:\n\n⏱️ Duration:\n"
        for k, v in pricing_config['duration'].items():
            text += f"  {k.replace('_', ' ').title()}: ${v:.2f}\n"
        text += "\n💾 GB Packages:\n"
        for k, v in pricing_config['gb'].items():
            text += f"  {k.upper()}: +${v:.2f}\n"
        text += "\n🌍 Country Selection:\n"
        text += "  Random: +$0\n  USA/UK/Germany: +$2\n  Singapore/Japan: +$3\n"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu" if user_id in logged_in_users else "back_to_welcome")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "contact_support":
        text = "📞 Contact Support\n\nTelegram: @YourSupport\n\nWe're here to help 24/7!"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_menu" if user_id in logged_in_users else "back_to_welcome")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == "logout":
        if user_id in logged_in_users:
            logged_in_users.remove(user_id)
        await query.edit_message_text("👋 Logged out successfully!")
        await show_welcome_menu(update, context)
        return ConversationHandler.END
    
    elif data == "back_to_menu":
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    elif data == "back_to_welcome":
        await show_welcome_menu(update, context)
        return ConversationHandler.END
    
    return ConversationHandler.END


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['login_email'] = update.message.text
    await update.message.reply_text("🔒 Please enter your password:")
    return WAITING_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = context.user_data.get('login_email')
    password = update.message.text
    user_id = update.effective_user.id
    
    if email in users_db and users_db[email] == password:
        logged_in_users.add(user_id)
        await update.message.reply_text("✅ Login successful!")
        if is_admin(user_id):
            await show_admin_menu(update, context)
        else:
            await show_main_menu(update, context)
    else:
        await update.message.reply_text("❌ Invalid credentials!")
        await show_welcome_menu(update, context)
    return ConversationHandler.END


async def receive_new_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['signup_email'] = update.message.text
    await update.message.reply_text("🔒 Please enter a password:")
    return WAITING_NEW_PASSWORD


async def receive_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = context.user_data.get('signup_email')
    password = update.message.text
    user_id = update.effective_user.id
    
    if email in users_db:
        await update.message.reply_text("❌ Email already registered!")
        await show_welcome_menu(update, context)
    else:
        users_db[email] = password
        logged_in_users.add(user_id)
        await update.message.reply_text("✅ Registration successful!")
        if is_admin(user_id):
            await show_admin_menu(update, context)
        else:
            await show_main_menu(update, context)
    return ConversationHandler.END


async def receive_price_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_price = float(update.message.text)
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
        
        await show_admin_menu(update, context)
    except ValueError:
        await update.message.reply_text("❌ Invalid price!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if is_admin(user_id):
        await show_admin_menu(update, context)
    elif user_id in logged_in_users:
        await show_main_menu(update, context)
    else:
        await show_welcome_menu(update, context)
    return ConversationHandler.END


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
            WAITING_PAYMENT_PROOF: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, receive_payment_proof)],
            WAITING_PROXY_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_proxy_details)],
            WAITING_PRICE_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price_edit)],
            WAITING_WALLET_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet_edit)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(button_callback)
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    logger.info("🚀 PROXY RES Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
