from flask import Flask, jsonify
import os
import time
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Shopify Bot Pro",
        "bot_status": "running" if os.environ.get('TELEGRAM_TOKEN') else "development_mode",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "telegram_token_set": bool(os.environ.get('TELEGRAM_TOKEN')),
        "environment": "production" if os.environ.get('TELEGRAM_TOKEN') else "development"
    })

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Web server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    run_web_server()
