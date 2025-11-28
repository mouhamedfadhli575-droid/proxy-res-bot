"""
Enhanced Message formatter module with payment system
"""

from datetime import datetime
from typing import Dict, Any


class MessageFormatter:
    
    @staticmethod
    def format_card_result(result: Dict[str, Any], user_info: Dict[str, Any]) -> str:
        """Format card check result in elegant style"""
        card = result.get('card', 'N/A')
        message = result.get('message', 'Unknown')
        amount = result.get('amount', '0')
        site = result.get('site', 'Unknown')
        time_taken = result.get('time_taken', 0)
        retries = result.get('retries', 0)
        
        bin_info = result.get('bin_info', {})
        bank = bin_info.get('bank', 'UNKNOWN')
        brand = bin_info.get('brand', 'UNKNOWN')
        card_type = bin_info.get('type', 'UNKNOWN')
        country = bin_info.get('country', 'UNKNOWN')
        emoji = bin_info.get('emoji', '🌍')
        
        now = datetime.now()
        date_str = now.strftime("%d-%m-%Y %H:%M:%S")
        
        formatted_message = f"""• 𝐑𝐞𝐬𝐮𝐥𝐭 :- 
--» 💳 𝐂𝐚𝐫𝐝 : {card}
--» 📌 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 : ✅ 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ${amount} ( {message} )
--» 🌐 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗚𝗿𝗮𝗽𝗵𝗤𝗟 ${amount} 𝗖𝗵𝗮𝗿𝗴𝗲

• 𝐁𝐢𝐧 𝐈𝐧𝐟𝐨 :- 
--» 🏦 𝐁𝐚𝐧𝐤 : {bank} - {brand} {card_type} - {country} {emoji} 

• 𝐎𝐭𝐡𝐞𝐫 𝐈𝐧𝐟𝐨 :- 
--» 🤵 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 : {user_info.get('first_name', 'User')} [ {user_info.get('user_id', 'N/A')} ] | (Date - {date_str})
--» ⌛ 𝐓𝐨𝐨𝐤 : {time_taken} 𝐬𝐞𝐜𝐬 (𝐑𝐞𝐭𝐫𝐢𝐞𝐬 - {retries})
--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
        
        return formatted_message
    
    @staticmethod
    def format_welcome_message() -> str:
        """Format welcome message with image"""
        return """🌟 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 𝗕𝗼𝘁! 🌟

مرحباً بك في بوت فحص البطاقات الأكثر تطوراً! 💳

🔹 𝗖𝗮𝗿𝗱 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗼𝗻 & 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴:
- Generate and check cards easily

🔹 𝗦𝘂𝗽𝗽𝗼𝗿𝘁:
- For help contact: @Support

🎉 Enjoy your experience!"""
    
    @staticmethod
    def format_subscription_info(user: Dict[str, Any]) -> str:
        """Format subscription information"""
        subscription_end = user.get('subscription_end', 'N/A')
        
        # Check if subscription is active
        if subscription_end and subscription_end != 'N/A':
            try:
                end_time = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                
                if end_time > now:
                    # Active subscription
                    time_left = end_time - now
                    hours_left = int(time_left.total_seconds() / 3600)
                    
                    return f"""✅ 𝗔𝗰𝘁𝗶𝘃𝗲 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻

--» ⏰ 𝐓𝐢𝐦𝐞 𝐋𝐞𝐟𝐭 : {hours_left} hours
--» 📅 𝐄𝐱𝐩𝐢𝐫𝐲 : {subscription_end}
--» ✅ 𝐒𝐭𝐚𝐭𝐮𝐬 : ACTIVE

🎊 استمتع بالفحص غير المحدود!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
            except:
                pass
        
        # No active subscription
        return """⚠️ 𝗡𝗼 𝗔𝗰𝘁𝗶𝘃𝗲 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻

--» ❌ ليس لديك اشتراك نشط
--» 💎 اشترك الآن للوصول الكامل!

اضغط على 💰 Pricing للاشتراك

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_help_message() -> str:
        """Format help message"""
        return """📖 𝗛𝗲𝗹𝗽 & 𝗚𝘂𝗶𝗱𝗲

🔍 𝗖𝗵𝗲𝗰𝗸 𝗦𝗶𝗻𝗴𝗹𝗲 𝗖𝗮𝗿𝗱:
--» استخدم: /check
--» ثم أرسل البطاقة بالصيغة: number|month|year|cvv
--» مثال: 5488093802407960|09|2026|954

📦 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸:
--» استخدم: /mass
--» ثم أرسل عدة بطاقات (كل بطاقة في سطر)
--» أو أرسل ملف نصي يحتوي على البطاقات

⚠️ 𝗜𝗺𝗽𝗼𝗿𝘁𝗮𝗻𝘁 𝗡𝗼𝘁𝗲𝘀:
--» البوت يعرض فقط البطاقات التي تم شحنها بنجاح
--» البطاقات المرفوضة لا تظهر في النتائج
--» يتم استخدام بروكسيات لتجنب الحظر

💬 للدعم، تواصل مع @Support

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_checking_message(current: int, total: int) -> str:
        """Format checking progress message"""
        percentage = int((current / total) * 100)
        progress_bar = "█" * (percentage // 10) + "░" * (10 - percentage // 10)
        
        return f"""⏳ 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗖𝗮𝗿𝗱𝘀...

--» 📊 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 : {current}/{total} ({percentage}%)
--» [{progress_bar}]

⏰ يرجى الانتظار..."""
    
    @staticmethod
    def format_completed_message(charged_count: int, total_count: int, time_taken: float) -> str:
        """Format completion message"""
        return f"""✅ 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱!

--» 💳 𝐓𝐨𝐭𝐚𝐥 𝐂𝐚𝐫𝐝𝐬 : {total_count}
--» ✅ 𝐂𝐡𝐚𝐫𝐠𝐞𝐝 : {charged_count}
--» ❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 : {total_count - charged_count}
--» ⏱️ 𝐓𝐢𝐦𝐞 : {time_taken:.2f} seconds

🎉 تم إرسال جميع البطاقات الناجحة!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_error_message(error: str) -> str:
        """Format error message"""
        return f"""❌ 𝗘𝗿𝗿𝗼𝗿

--» ⚠️ {error}

يرجى المحاولة مرة أخرى أو التواصل مع الدعم.

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_no_subscription_message() -> str:
        """Format no subscription message"""
        return """⚠️ 𝗡𝗼 𝗔𝗰𝘁𝗶𝘃𝗲 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻

--» ❌ ليس لديك اشتراك نشط
--» 💎 يرجى الاشتراك للاستمرار

اضغط على 💰 Pricing للاشتراك الآن!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_banned_message() -> str:
        """Format banned user message"""
        return """🚫 𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗕𝗮𝗻𝗻𝗲𝗱

--» ❌ تم حظر حسابك من استخدام البوت
--» 📞 للاستفسار، تواصل مع @Support

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
    
    @staticmethod
    def format_subscription_expired_during_check(checked: int, total: int) -> str:
        """Format message when subscription expires during check"""
        return f"""⚠️ Your subscription has expired while a check was running.
📊 Checked: {checked}/{total}

🔄 To continue, please renew your subscription /start and then press the 'Resume' button in the check message."""
