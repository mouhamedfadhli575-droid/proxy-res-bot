"""
Admin Panel Web Application for Shopify Checker Bot
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Database
from config import *

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize database
db = Database(DATABASE_PATH)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class AdminUser(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    # In production, load from database
    return AdminUser(user_id, 'admin')


@app.route('/')
@login_required
def dashboard():
    """Dashboard page"""
    # Get statistics
    stats = db.get_statistics(30)
    users = db.get_all_users()
    proxies = db.get_all_proxies()
    
    # Calculate totals
    total_checks = sum(s['total_checks'] for s in stats)
    successful_checks = sum(s['successful_checks'] for s in stats)
    failed_checks = sum(s['failed_checks'] for s in stats)
    success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
    
    active_subscriptions = sum(1 for u in users if db.is_user_subscribed(u['user_id']))
    active_proxies = sum(1 for p in proxies if p['is_active'])
    
    return render_template('dashboard.html',
                         total_users=len(users),
                         active_subscriptions=active_subscriptions,
                         total_checks=total_checks,
                         success_rate=success_rate,
                         active_proxies=active_proxies,
                         total_proxies=len(proxies))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication (in production, use database)
        if username == 'admin' and password == 'admin123':
            user = AdminUser(1, username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    return redirect(url_for('login'))


@app.route('/users')
@login_required
def users():
    """Users management page"""
    all_users = db.get_all_users()
    return render_template('users.html', users=all_users)


@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user"""
    user = db.get_user(user_id)
    
    if request.method == 'POST':
        subscription_type = request.form.get('subscription_type')
        days = int(request.form.get('days', 0))
        
        db.update_user_subscription(user_id, subscription_type, days)
        flash('User updated successfully', 'success')
        return redirect(url_for('users'))
    
    return render_template('edit_user.html', user=user, plans=SUBSCRIPTION_PLANS)


@app.route('/users/ban/<int:user_id>')
@login_required
def ban_user(user_id):
    """Ban user"""
    db.ban_user(user_id, True)
    flash('User banned successfully', 'success')
    return redirect(url_for('users'))


@app.route('/users/unban/<int:user_id>')
@login_required
def unban_user(user_id):
    """Unban user"""
    db.ban_user(user_id, False)
    flash('User unbanned successfully', 'success')
    return redirect(url_for('users'))


@app.route('/proxies')
@login_required
def proxies():
    """Proxies management page"""
    all_proxies = db.get_all_proxies()
    return render_template('proxies.html', proxies=all_proxies)


@app.route('/proxies/add', methods=['POST'])
@login_required
def add_proxy():
    """Add new proxy"""
    proxy_string = request.form.get('proxy_string')
    
    if proxy_string:
        success = db.add_proxy(proxy_string)
        if success:
            flash('Proxy added successfully', 'success')
        else:
            flash('Proxy already exists', 'error')
    
    return redirect(url_for('proxies'))


@app.route('/proxies/add_bulk', methods=['POST'])
@login_required
def add_bulk_proxies():
    """Add multiple proxies"""
    proxies_text = request.form.get('proxies_text')
    
    if proxies_text:
        proxies_list = proxies_text.strip().split('\n')
        added_count = 0
        
        for proxy in proxies_list:
            proxy = proxy.strip()
            if proxy:
                if db.add_proxy(proxy):
                    added_count += 1
        
        flash(f'{added_count} proxies added successfully', 'success')
    
    return redirect(url_for('proxies'))


@app.route('/proxies/toggle/<int:proxy_id>')
@login_required
def toggle_proxy(proxy_id):
    """Toggle proxy active status"""
    # Get current status
    proxies = db.get_all_proxies()
    proxy = next((p for p in proxies if p['id'] == proxy_id), None)
    
    if proxy:
        new_status = not proxy['is_active']
        db.toggle_proxy(proxy_id, new_status)
        flash('Proxy status updated', 'success')
    
    return redirect(url_for('proxies'))


@app.route('/proxies/delete/<int:proxy_id>')
@login_required
def delete_proxy(proxy_id):
    """Delete proxy"""
    db.delete_proxy(proxy_id)
    flash('Proxy deleted successfully', 'success')
    return redirect(url_for('proxies'))


@app.route('/statistics')
@login_required
def statistics():
    """Statistics page"""
    stats = db.get_statistics(30)
    
    # Prepare data for charts
    dates = [s['date'] for s in reversed(stats)]
    total_checks = [s['total_checks'] for s in reversed(stats)]
    successful_checks = [s['successful_checks'] for s in reversed(stats)]
    failed_checks = [s['failed_checks'] for s in reversed(stats)]
    
    return render_template('statistics.html',
                         dates=dates,
                         total_checks=total_checks,
                         successful_checks=successful_checks,
                         failed_checks=failed_checks)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Update settings (in production, save to database or config file)
        flash('Settings updated successfully', 'success')
    
    return render_template('settings.html',
                         shopify_sites=SHOPIFY_SITES,
                         check_timeout=CHECK_TIMEOUT,
                         check_retries=CHECK_RETRIES)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for real-time statistics"""
    stats = db.get_statistics(1)
    users = db.get_all_users()
    
    if stats:
        today_stats = stats[0]
    else:
        today_stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0
        }
    
    return jsonify({
        'total_users': len(users),
        'today_checks': today_stats['total_checks'],
        'today_success': today_stats['successful_checks'],
        'today_failed': today_stats['failed_checks']
    })


def main():
    """Run the admin panel"""
    print(f"🌐 Admin Panel starting on http://{ADMIN_PANEL_HOST}:{ADMIN_PANEL_PORT}")
    print(f"👤 Default credentials: admin / admin123")
    app.run(host=ADMIN_PANEL_HOST, port=ADMIN_PANEL_PORT, debug=True)


if __name__ == '__main__':
    main()
