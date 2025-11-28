"""
Telegram Stars Payment System Module
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class PaymentSystem:
    """Handle Telegram Stars payments"""
    
    # Pricing: Stars per hour
    STARS_PER_HOUR = 8  # 8 stars = 1 hour
    
    # Payment plans (for reference)
    PAYMENT_PLANS = {
        '1_hour': {'hours': 1, 'stars': 8},
        '5_hours': {'hours': 5, 'stars': 39},
        '12_hours': {'hours': 12, 'stars': 95},
        '24_hours': {'hours': 24, 'stars': 189},
        '1_week': {'hours': 168, 'stars': 1340},  # Max with Stars
    }
    
    @staticmethod
    def calculate_stars(hours: int) -> int:
        """Calculate stars needed for given hours"""
        # Special pricing for common packages
        if hours == 5:
            return 39
        elif hours == 12:
            return 95
        elif hours == 24:
            return 189
        elif hours == 168:  # 1 week
            return 1340
        else:
            # Standard pricing
            return hours * PaymentSystem.STARS_PER_HOUR
    
    @staticmethod
    def calculate_hours_from_stars(stars: int) -> float:
        """Calculate hours from stars amount"""
        return stars / PaymentSystem.STARS_PER_HOUR
    
    @staticmethod
    def format_subscription_duration(hours: int) -> str:
        """Format hours into readable duration"""
        if hours < 24:
            return f"{hours} Hour{'s' if hours > 1 else ''}"
        elif hours < 168:
            days = hours // 24
            remaining_hours = hours % 24
            if remaining_hours > 0:
                return f"{days} Day{'s' if days > 1 else ''} {remaining_hours} Hour{'s' if remaining_hours > 1 else ''}"
            return f"{days} Day{'s' if days > 1 else ''}"
        else:
            weeks = hours // 168
            remaining_days = (hours % 168) // 24
            if remaining_days > 0:
                return f"{weeks} Week{'s' if weeks > 1 else ''} {remaining_days} Day{'s' if remaining_days > 1 else ''}"
            return f"{weeks} Week{'s' if weeks > 1 else ''}"
    
    @staticmethod
    def create_invoice_payload(user_id: int, hours: int) -> str:
        """Create unique invoice payload"""
        timestamp = int(time.time())
        return f"sub_{user_id}_{hours}h_{timestamp}"
    
    @staticmethod
    def parse_invoice_payload(payload: str) -> Optional[Dict[str, Any]]:
        """Parse invoice payload"""
        try:
            parts = payload.split('_')
            if len(parts) >= 4 and parts[0] == 'sub':
                return {
                    'user_id': int(parts[1]),
                    'hours': int(parts[2].replace('h', '')),
                    'timestamp': int(parts[3])
                }
        except:
            pass
        return None
    
    @staticmethod
    def validate_hours(hours: int) -> tuple:
        """Validate hours input"""
        if hours < 1:
            return False, "❌ الحد الأدنى هو ساعة واحدة"
        
        if hours > 168:  # Max 1 week with Stars
            return False, "❌ الحد الأقصى هو 168 ساعة (أسبوع واحد) مع نجوم تيليجرام"
        
        return True, "OK"
    
    @staticmethod
    def format_pricing_message() -> str:
        """Format pricing information message"""
        message = """💰 𝗣𝗿𝗶𝗰𝗶𝗻𝗴 𝗣𝗹𝗮𝗻𝘀

🌟 𝐏𝐚𝐲 𝐰𝐢𝐭𝐡 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐒𝐭𝐚𝐫𝐬 ⭐ (Auto Activation)

📦 𝐏𝐚𝐜𝐤𝐚𝐠𝐞𝐬:
--» 1 Hour = 8 ⭐
--» 5 Hours = 39 ⭐ 💎
--» 12 Hours = 95 ⭐
--» 24 Hours = 189 ⭐
--» 1 Week (168h) = 1340 ⭐

💡 𝐂𝐮𝐬𝐭𝐨𝐦 𝐒𝐮𝐛𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧:
--» اختر أي عدد من الساعات (1-168)
--» السعر: 8 نجوم لكل ساعة

✨ 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:
--» ✅ تفعيل فوري بعد الدفع
--» ✅ فحص غير محدود خلال المدة
--» ✅ دعم فني 24/7

🎁 𝐁𝐞𝐬𝐭 𝐕𝐚𝐥𝐮𝐞: 5 Hours Package!

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
        
        return message
    
    @staticmethod
    def format_subscription_confirmation(hours: int, stars: int) -> str:
        """Format subscription confirmation message"""
        duration = PaymentSystem.format_subscription_duration(hours)
        
        message = f"""✅ 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗖𝗼𝗻𝗳𝗶𝗿𝗺𝗮𝘁𝗶𝗼𝗻

--» ⏰ 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧 : {duration}
--» 💰 𝐏𝐫𝐢𝐜𝐞 : {stars} ⭐

اضغط على الزر أدناه لإتمام الدفع:"""
        
        return message
    
    @staticmethod
    def format_payment_success(hours: int, expiry_time: datetime) -> str:
        """Format payment success message"""
        duration = PaymentSystem.format_subscription_duration(hours)
        expiry_str = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""🎉 𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹!

--» ✅ تم تفعيل اشتراكك بنجاح
--» ⏰ 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧 : {duration}
--» 📅 𝐄𝐱𝐩𝐢𝐫𝐲 : {expiry_str}

🎊 يمكنك الآن استخدام جميع ميزات البوت!

استخدم /mass لبدء الفحص

--» 🤖 𝗕𝗼𝘁 𝗕𝘆 : 𝗠𝗿𝗛𝗮𝗞𝗲𝗥𝘅𝗭𝘇(〽️)"""
        
        return message
