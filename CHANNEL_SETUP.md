# How to Setup Orders Channel / كيفية إعداد قناة الطلبات

## English Version

### Step 1: Create a Private Channel

1. Open Telegram
2. Click on "New Channel"
3. Enter channel name: **"PROXY RES Orders"** (or any name)
4. Choose **"Private Channel"**
5. Click "Create"

### Step 2: Add Your Bot as Admin

1. Open your channel
2. Click on channel name (top)
3. Click "Administrators"
4. Click "Add Administrator"
5. Search for your bot username (e.g., `@proxy_res_bot`)
6. Select your bot
7. Give permissions:
   - ✅ Post Messages
   - ✅ Edit Messages
   - ✅ Delete Messages
8. Click "Done"

### Step 3: Get Channel ID

**Method 1: Using @userinfobot**

1. Forward any message from your channel to `@userinfobot`
2. The bot will reply with channel information
3. Look for "Id:" - it will be a negative number like `-1001234567890`
4. Copy this number (including the minus sign!)

**Method 2: Using @getmyid_bot**

1. Forward any message from your channel to `@getmyid_bot`
2. The bot will show the channel ID
3. Copy the ID (it starts with `-100`)

**Method 3: Manual**

1. Open your channel in web browser: `https://web.telegram.org`
2. Click on your channel
3. Look at the URL: `https://web.telegram.org/z/#-1001234567890`
4. The number after `#` is your channel ID

### Step 4: Add Channel ID to config.env

Open `config.env` file and add:

```
ORDERS_CHANNEL_ID=-1001234567890
```

**Important:**
- The ID MUST start with `-100`
- Include the minus sign `-`
- No spaces before or after `=`

**Example:**
```
TELEGRAM_BOT_TOKEN=8574194260:AAEIRmz0_5ZCv1EbzaAXSEYDt4Fy-pT2yC8
ADMIN_ID=8573455220
ORDERS_CHANNEL_ID=-1003005959006
```

### Step 5: Test

1. Run the bot: `python3 bot.py`
2. Make a test order
3. Check if the order appears in your channel

---

## النسخة العربية

### الخطوة 1: إنشاء قناة خاصة

1. افتح تيليجرام
2. اضغط "قناة جديدة" / "New Channel"
3. اكتب اسم القناة: **"PROXY RES Orders"** (أو أي اسم)
4. اختر **"قناة خاصة"** / **"Private Channel"**
5. اضغط "إنشاء" / "Create"

### الخطوة 2: إضافة البوت كمسؤول

1. افتح قناتك
2. اضغط على اسم القناة (في الأعلى)
3. اضغط "المسؤولون" / "Administrators"
4. اضغط "إضافة مسؤول" / "Add Administrator"
5. ابحث عن اسم البوت (مثلاً `@proxy_res_bot`)
6. اختر البوت
7. أعطه الصلاحيات:
   - ✅ نشر الرسائل / Post Messages
   - ✅ تعديل الرسائل / Edit Messages
   - ✅ حذف الرسائل / Delete Messages
8. اضغط "تم" / "Done"

### الخطوة 3: الحصول على معرف القناة

**الطريقة 1: استخدام @userinfobot**

1. أرسل أي رسالة من قناتك إلى `@userinfobot`
2. البوت سيرد بمعلومات القناة
3. ابحث عن "Id:" - سيكون رقم سالب مثل `-1001234567890`
4. انسخ هذا الرقم (مع علامة الناقص!)

**الطريقة 2: استخدام @getmyid_bot**

1. أرسل أي رسالة من قناتك إلى `@getmyid_bot`
2. البوت سيعرض معرف القناة
3. انسخ المعرف (يبدأ بـ `-100`)

**الطريقة 3: يدوياً**

1. افتح قناتك في المتصفح: `https://web.telegram.org`
2. اضغط على قناتك
3. انظر إلى الرابط: `https://web.telegram.org/z/#-1001234567890`
4. الرقم بعد `#` هو معرف قناتك

### الخطوة 4: إضافة معرف القناة في config.env

افتح ملف `config.env` وأضف:

```
ORDERS_CHANNEL_ID=-1001234567890
```

**مهم:**
- المعرف يجب أن يبدأ بـ `-100`
- ضع علامة الناقص `-`
- لا مسافات قبل أو بعد `=`

**مثال:**
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
ORDERS_CHANNEL_ID=-1001234567890
```

### الخطوة 5: الاختبار

1. شغّل البوت: `python3 bot.py`
2. اعمل طلب تجريبي
3. تحقق من ظهور الطلب في قناتك

---

## What Happens When Order is Placed / ماذا يحدث عند الطلب

### 1. Customer Places Order / العميل يضع طلب

Customer chooses:
- Duration (1 month, 3 months, etc.)
- GB Package (10GB, 50GB, etc.)
- Country (USA, UK, Random, etc.)
- Payment Method

العميل يختار:
- المدة (شهر، 3 شهور، إلخ)
- باقة الـ GB (10GB, 50GB, إلخ)
- الدولة (USA, UK, Random, إلخ)
- طريقة الدفع

### 2. Customer Sends Payment Proof / العميل يرسل إثبات الدفع

Customer sends:
- Screenshot of payment
- OR Transaction ID (TX ID)

العميل يرسل:
- صورة للدفع
- أو معرف المعاملة (TX ID)

### 3. Order Appears in Channel / الطلب يظهر في القناة

You will see in your channel:

```
🆕 NEW ORDER - ORD1001

👤 Customer Info:
• Name: John Doe
• Username: @johndoe
• User ID: 123456789

📦 Order Details:
• Duration: 1 Month
• GB Package: 50GB
• Country: 🇺🇸 USA

💰 Payment:
• Method: ₿ Bitcoin (BTC)
• Amount: $12.00

📅 Order Time: 2025-11-25 23:45:30

[✅ Accept] [❌ Reject]
```

Plus payment proof image/text below

بالإضافة إلى صورة/نص إثبات الدفع أسفله

### 4. You Accept or Reject / أنت تقبل أو ترفض

**If you click ✅ Accept:**

1. Customer gets notification: "Order Approved!"
2. Channel message updates: "ACCEPTED - Waiting for proxy details..."
3. New button appears: "📝 Send Proxy Details"

**إذا ضغطت ✅ قبول:**

1. العميل يحصل على إشعار: "تم قبول الطلب!"
2. رسالة القناة تتحدث: "تم القبول - في انتظار تفاصيل البروكسي..."
3. زر جديد يظهر: "📝 إرسال تفاصيل البروكسي"

**If you click ❌ Reject:**

1. Customer gets notification: "Order Rejected"
2. Channel message updates: "REJECTED"

**إذا ضغطت ❌ رفض:**

1. العميل يحصل على إشعار: "تم رفض الطلب"
2. رسالة القناة تتحدث: "تم الرفض"

### 5. Send Proxy Details / إرسال تفاصيل البروكسي

After accepting:

1. Click "📝 Send Proxy Details"
2. Bot asks you to send proxy info
3. You type/paste:
```
Host: proxy.example.com
Port: 8080
Username: user123
Password: pass123
Protocol: HTTP/HTTPS/SOCKS5
```
4. Bot sends it to customer automatically
5. Customer receives: "✅ Your Proxy is Ready!"
6. Order marked as COMPLETED

بعد القبول:

1. اضغط "📝 إرسال تفاصيل البروكسي"
2. البوت يطلب منك إرسال معلومات البروكسي
3. أنت تكتب/تلصق:
```
Host: proxy.example.com
Port: 8080
Username: user123
Password: pass123
Protocol: HTTP/HTTPS/SOCKS5
```
4. البوت يرسلها للعميل تلقائياً
5. العميل يستلم: "✅ البروكسي جاهز!"
6. الطلب يُعلّم كمكتمل

---

## Troubleshooting / حل المشاكل

### Problem: Orders not appearing in channel / المشكلة: الطلبات لا تظهر في القناة

**Solution / الحل:**

1. Check bot is admin in channel / تأكد أن البوت مسؤول في القناة
2. Check ORDERS_CHANNEL_ID is correct / تأكد أن ORDERS_CHANNEL_ID صحيح
3. Check ID starts with `-100` / تأكد أن المعرف يبدأ بـ `-100`
4. Restart bot after changing config.env / أعد تشغيل البوت بعد تعديل config.env

### Problem: Bot can't send to channel / المشكلة: البوت لا يستطيع الإرسال للقناة

**Solution / الحل:**

1. Make sure bot has "Post Messages" permission / تأكد أن البوت لديه صلاحية "نشر الرسائل"
2. Make sure channel is private, not public / تأكد أن القناة خاصة وليست عامة
3. Try removing and re-adding bot as admin / جرب حذف وإعادة إضافة البوت كمسؤول

### Problem: Can't get channel ID / المشكلة: لا أستطيع الحصول على معرف القناة

**Solution / الحل:**

1. Make sure you forward a message, not just share link / تأكد أنك ترسل رسالة وليس فقط مشاركة رابط
2. Try different bot (@userinfobot or @getmyid_bot) / جرب بوت آخر
3. Use web.telegram.org method / استخدم طريقة web.telegram.org

---

## Example config.env File / مثال على ملف config.env

```
# Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Your Telegram User ID from @userinfobot
ADMIN_ID=123456789

# Channel ID from forwarding message to @userinfobot
ORDERS_CHANNEL_ID=-1001234567890
```

---

**All set! Your orders will now appear in your channel! 🎉**

**جاهز! طلباتك ستظهر الآن في قناتك! 🎉**
