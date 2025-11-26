# PROXY RES Bot 

A Telegram bot for proxy management with user authentication, recharge options, and proxy services.

## Features

### For Non-Logged In Users:
- **Login**: Sign in to your existing account
- **Signup**: Create a new account
- **Verify Email**: Email verification (to be implemented)
- **Forget Password**: Password recovery (to be implemented)
- **Lang**: Change bot language
- **Contact Support**: Get support contact information
- **Prices**: View proxy pricing

### For Logged In Users:
- **New Proxy**: Create a new proxy
- **My Profile**: View your profile information
- **My Proxies**: View your active proxies
- **Recharge**: Add balance to your account with multiple payment methods:
  - Payeer (Auto)
  - Binance (Auto)
  - Celo Coin
  - Crypto AUTO (ltc, trx, usdt, etc)
  - BKASH (Auto)
  - Nagad (Auto)
  - Rocket
- **Referral +10%**: Get your referral link and earn 10% commission
- **Lang**: Change bot language
- **Contact Support**: Get support contact information
- **Prices**: View proxy pricing
- **Tutorial**: Learn how to use the bot
- **Logout**: Sign out from your account

## Installation

### Prerequisites
- Python 3.11 or higher
- pip3 package manager

### Steps

1. **Clone or download the bot files**

2. **Install required packages:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Create a Telegram Bot:**
   - Open Telegram and search for [@BotFather](https://t.me/BotFather)
   - Send `/newbot` command
   - Follow the instructions to create your bot
   - Choose a name: `PROXY RES` (or any name you prefer)
   - Choose a username: must end with `bot` (e.g., `proxy_res_bot`)
   - Copy the bot token provided by BotFather

4. **Configure the bot:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` file and replace `your_bot_token_here` with your actual bot token:
     ```
     TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
     ```

5. **Run the bot:**
   ```bash
   python3 bot.py
   ```

## Usage

1. **Start the bot:**
   - Open Telegram and search for your bot username
   - Send `/start` command
   - You will see the welcome menu

2. **Create an account:**
   - Click "Signup" button
   - Enter your email address
   - Enter a password
   - You will be automatically logged in

3. **Login:**
   - Click "Login" button
   - Enter your email address
   - Enter your password

4. **Use bot features:**
   - After logging in, you can access all features from the main menu
   - Create proxies, recharge your account, view your profile, etc.

## Project Structure

```
proxy_res_bot/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env               # Your actual environment variables (create this)
└── README.md          # This file
```

## Important Notes

### Current Implementation
- This is a **demo version** with basic functionality
- User data is stored in memory (will be lost when bot restarts)
- Authentication is simplified (not secure for production)
- Payment methods are placeholders (need real payment integration)

### For Production Use
You should implement:
1. **Database**: Use PostgreSQL, MySQL, or MongoDB for persistent storage
2. **Secure Authentication**: Hash passwords using bcrypt or similar
3. **Email Verification**: Implement real email verification
4. **Payment Integration**: Integrate real payment gateways
5. **Proxy Management**: Implement actual proxy creation and management
6. **Error Handling**: Add comprehensive error handling
7. **Logging**: Implement proper logging for debugging and monitoring
8. **Rate Limiting**: Add rate limiting to prevent abuse
9. **Admin Panel**: Create admin interface for management

## Customization

### Change Support Contact
Edit the `contact_support` section in `bot.py`:
```python
await query.edit_message_text(
    text="Contact Support: @YourSupportUsername\n\nFeel free to reach out for any assistance!",
    reply_markup=reply_markup
)
```

### Change Pricing
Edit the `prices` section in `bot.py`:
```python
await query.edit_message_text(
    text="Proxy Prices:\n\n1 Month - $5\n3 Months - $12\n6 Months - $20\n1 Year - $35",
    reply_markup=reply_markup
)
```

### Add More Languages
Implement language switching in the `lang_en` and `lang_ar` callbacks.

## Troubleshooting

### Bot doesn't respond
- Check if the bot is running
- Verify the bot token is correct in `.env` file
- Check internet connection

### Import errors
- Make sure all dependencies are installed: `pip3 install -r requirements.txt`
- Use Python 3.11 or higher

### Bot crashes
- Check the console for error messages
- Ensure the `.env` file exists and contains the correct token

## Support

For any questions or issues, please contact the developer.

## License

This project is provided as-is for educational and personal use.
