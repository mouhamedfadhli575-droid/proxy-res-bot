"""
Enhanced Database management module with Subscription Codes
"""

import sqlite3
import datetime
import secrets
import string
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscription_type TEXT DEFAULT 'free',
                subscription_end DATE,
                credits INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Proxies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_string TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                card_number TEXT,
                result TEXT,
                message TEXT,
                gateway TEXT,
                site_used TEXT,
                time_taken REAL,
                check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                total_checks INTEGER DEFAULT 0,
                successful_checks INTEGER DEFAULT 0,
                failed_checks INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0
            )
        ''')
        
        # Subscription codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                hours INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                used_by INTEGER,
                used_at TEXT,
                is_used INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # User Management
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add new user or update existing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return dict(zip(columns, row))
        
        conn.close()
        return None
    
    def update_user_subscription(self, user_id: int, subscription_type: str, days: float):
        """Update user subscription"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        end_date = datetime.datetime.now() + datetime.timedelta(days=days)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_type = ?, subscription_end = ?
            WHERE user_id = ?
        ''', (subscription_type, end_date, user_id))
        
        conn.commit()
        conn.close()
    
    def is_user_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user['subscription_type'] == 'free':
            return False
        
        if user['subscription_end']:
            try:
                end_date = datetime.datetime.strptime(user['subscription_end'], '%Y-%m-%d %H:%M:%S')
                return datetime.datetime.now() < end_date
            except:
                return False
        
        return False
    
    def ban_user(self, user_id: int, ban: bool = True):
        """Ban or unban user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (1 if ban else 0, user_id))
        
        conn.commit()
        conn.close()
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        user = self.get_user(user_id)
        return user['is_banned'] == 1 if user else False
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY joined_date DESC')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # Proxy Management
    def add_proxy(self, proxy_string: str):
        """Add new proxy"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO proxies (proxy_string) VALUES (?)', (proxy_string,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_active_proxies(self) -> List[str]:
        """Get all active proxies"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT proxy_string FROM proxies WHERE is_active = 1 ORDER BY RANDOM()')
        proxies = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return proxies
    
    def update_proxy_stats(self, proxy_string: str, success: bool):
        """Update proxy statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE proxies 
                SET success_count = success_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE proxy_string = ?
            ''', (proxy_string,))
        else:
            cursor.execute('''
                UPDATE proxies 
                SET fail_count = fail_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE proxy_string = ?
            ''', (proxy_string,))
        
        conn.commit()
        conn.close()
    
    def toggle_proxy(self, proxy_id: int, active: bool):
        """Enable or disable proxy"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE proxies SET is_active = ? WHERE id = ?', (1 if active else 0, proxy_id))
        
        conn.commit()
        conn.close()
    
    def delete_proxy(self, proxy_id: int):
        """Delete proxy"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM proxies WHERE id = ?', (proxy_id,))
        
        conn.commit()
        conn.close()
    
    def get_all_proxies(self) -> List[Dict[str, Any]]:
        """Get all proxies with statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM proxies ORDER BY added_date DESC')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # Check History
    def add_check_history(self, user_id: int, card_number: str, result: str, 
                         message: str, gateway: str, site_used: str, time_taken: float):
        """Add check to history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Mask card number for security
        masked_card = card_number[:6] + 'X' * (len(card_number) - 10) + card_number[-4:]
        
        cursor.execute('''
            INSERT INTO check_history 
            (user_id, card_number, result, message, gateway, site_used, time_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, masked_card, result, message, gateway, site_used, time_taken))
        
        conn.commit()
        conn.close()
    
    def get_user_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user check history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM check_history 
            WHERE user_id = ? 
            ORDER BY check_date DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # Statistics
    def update_statistics(self, success: bool):
        """Update daily statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        today = datetime.date.today()
        
        cursor.execute('''
            INSERT INTO statistics (date, total_checks, successful_checks, failed_checks)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_checks = total_checks + 1,
                successful_checks = successful_checks + ?,
                failed_checks = failed_checks + ?
        ''', (today, 1 if success else 0, 0 if success else 1, 1 if success else 0, 0 if success else 1))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get statistics for last N days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM statistics 
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        ''', (days,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    # Subscription Codes Management
    @staticmethod
    def generate_code(length: int = 12) -> str:
        """Generate random subscription code"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def add_subscription_code(self, code: str, hours: int, created_by: int) -> bool:
        """Add a new subscription code"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''\n                INSERT INTO subscription_codes (code, hours, created_by, created_at)
                VALUES (?, ?, ?, ?)
            ''', (code, hours, created_by, now))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_subscription_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get subscription code details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subscription_codes WHERE code = ?', (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'code': row[1],
                'hours': row[2],
                'created_by': row[3],
                'created_at': row[4],
                'used_by': row[5],
                'used_at': row[6],
                'is_used': row[7]
            }
        return None
    
    def redeem_subscription_code(self, code: str, user_id: int) -> tuple:
        """Redeem a subscription code"""
        code_info = self.get_subscription_code(code)
        
        if not code_info:
            return False, "كود غير صحيح"
        
        if code_info['is_used']:
            return False, "تم استخدام هذا الكود من قبل"
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Mark code as used
            cursor.execute('''
                UPDATE subscription_codes
                SET used_by = ?, used_at = ?, is_used = 1
                WHERE code = ?
            ''', (user_id, now, code))
            
            # Update user subscription
            hours = code_info['hours']
            days = hours / 24
            end_date = datetime.datetime.now() + datetime.timedelta(days=days)
            
            cursor.execute('''
                UPDATE users 
                SET subscription_type = ?, subscription_end = ?
                WHERE user_id = ?
            ''', ('redeemed', end_date, user_id))
            
            conn.commit()
            conn.close()
            return True, hours
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def get_all_subscription_codes(self) -> List[Dict[str, Any]]:
        """Get all subscription codes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subscription_codes ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for row in rows:
            codes.append({
                'id': row[0],
                'code': row[1],
                'hours': row[2],
                'created_by': row[3],
                'created_at': row[4],
                'used_by': row[5],
                'used_at': row[6],
                'is_used': row[7]
            })
        return codes
    
    def delete_subscription_code(self, code: str) -> bool:
        """Delete a subscription code"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM subscription_codes WHERE code = ?', (code,))
            conn.commit()
            conn.close()
            return True
        except:
            return False
