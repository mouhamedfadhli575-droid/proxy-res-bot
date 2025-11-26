#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Module for PROXY RES Bot
PostgreSQL integration for persistent data storage
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str):
        """Initialize database connection"""
        self.database_url = database_url
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            logger.info("✅ Database connected successfully!")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables"""
        try:
            with self.conn.cursor() as cur:
                # Users table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        balance DECIMAL(10, 2) DEFAULT 0.00,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Orders table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id VARCHAR(50) PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        duration VARCHAR(50) NOT NULL,
                        gb VARCHAR(50) NOT NULL,
                        country VARCHAR(50) NOT NULL,
                        total_price DECIMAL(10, 2) NOT NULL,
                        payment_method VARCHAR(50) NOT NULL,
                        status VARCHAR(50) DEFAULT 'pending',
                        proxy_details TEXT,
                        channel_message_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accepted_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        rejected_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Recharge requests table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS recharge_requests (
                        recharge_id VARCHAR(50) PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        method VARCHAR(50) NOT NULL,
                        proof TEXT,
                        transaction_id VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        approved_at TIMESTAMP,
                        rejected_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Payment methods table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS payment_methods (
                        method_code VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        wallet VARCHAR(255),
                        type VARCHAR(50) NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Countries table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS countries (
                        country_code VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        price DECIMAL(10, 2) DEFAULT 0.00
                    )
                """)
                
                # Bot config table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_config (
                        key VARCHAR(100) PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                
                # Pricing config table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pricing (
                        category VARCHAR(50) NOT NULL,
                        key VARCHAR(50) NOT NULL,
                        price DECIMAL(10, 2) NOT NULL,
                        PRIMARY KEY (category, key)
                    )
                """)
                
                self.conn.commit()
                logger.info("✅ Database tables created successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            self.conn.rollback()
            raise
    
    def execute(self, query: str, params: tuple = None, fetch: bool = False) -> Optional[List[Dict]]:
        """Execute a query"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                self.conn.commit()
                return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            self.conn.rollback()
            raise
    
    # ========== USER OPERATIONS ==========
    
    def create_user(self, user_id: int, email: str, password: str) -> bool:
        """Create a new user"""
        try:
            self.execute(
                "INSERT INTO users (user_id, email, password) VALUES (%s, %s, %s)",
                (user_id, email, password)
            )
            return True
        except:
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        result = self.execute(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,),
            fetch=True
        )
        return dict(result[0]) if result else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        result = self.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,),
            fetch=True
        )
        return dict(result[0]) if result else None
    
    def update_balance(self, user_id: int, amount: float) -> bool:
        """Update user balance"""
        try:
            self.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id = %s",
                (amount, user_id)
            )
            return True
        except:
            return False
    
    def get_balance(self, user_id: int) -> float:
        """Get user balance"""
        user = self.get_user(user_id)
        return float(user['balance']) if user else 0.0
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        result = self.execute("SELECT * FROM users ORDER BY created_at DESC", fetch=True)
        return [dict(row) for row in result] if result else []
    
    # ========== ORDER OPERATIONS ==========
    
    def create_order(self, order_data: Dict) -> bool:
        """Create a new order"""
        try:
            self.execute(
                """INSERT INTO orders (order_id, user_id, duration, gb, country, 
                   total_price, payment_method, status, channel_message_id) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    order_data['order_id'],
                    order_data['user_id'],
                    order_data['duration'],
                    order_data['gb'],
                    order_data['country'],
                    order_data['total_price'],
                    order_data['payment_method'],
                    order_data.get('status', 'pending'),
                    order_data.get('channel_message_id')
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        result = self.execute(
            "SELECT * FROM orders WHERE order_id = %s",
            (order_id,),
            fetch=True
        )
        return dict(result[0]) if result else None
    
    def update_order_status(self, order_id: str, status: str, **kwargs) -> bool:
        """Update order status"""
        try:
            updates = [f"status = %s"]
            params = [status]
            
            if status == 'accepted':
                updates.append("accepted_at = %s")
                params.append(datetime.now())
            elif status == 'completed':
                updates.append("completed_at = %s")
                params.append(datetime.now())
                if 'proxy_details' in kwargs:
                    updates.append("proxy_details = %s")
                    params.append(kwargs['proxy_details'])
            elif status == 'rejected':
                updates.append("rejected_at = %s")
                params.append(datetime.now())
            
            params.append(order_id)
            
            self.execute(
                f"UPDATE orders SET {', '.join(updates)} WHERE order_id = %s",
                tuple(params)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update order: {e}")
            return False
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        """Get all orders for a user"""
        result = self.execute(
            "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
            fetch=True
        )
        return [dict(row) for row in result] if result else []
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        result = self.execute(
            "SELECT * FROM orders WHERE status = 'pending' OR status = 'accepted' ORDER BY created_at DESC",
            fetch=True
        )
        return [dict(row) for row in result] if result else []
    
    # ========== RECHARGE OPERATIONS ==========
    
    def create_recharge(self, recharge_data: Dict) -> bool:
        """Create a new recharge request"""
        try:
            self.execute(
                """INSERT INTO recharge_requests (recharge_id, user_id, amount, method, 
                   proof, transaction_id, status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    recharge_data['recharge_id'],
                    recharge_data['user_id'],
                    recharge_data['amount'],
                    recharge_data['method'],
                    recharge_data.get('proof'),
                    recharge_data.get('transaction_id'),
                    recharge_data.get('status', 'pending')
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create recharge: {e}")
            return False
    
    def get_recharge(self, recharge_id: str) -> Optional[Dict]:
        """Get recharge by ID"""
        result = self.execute(
            "SELECT * FROM recharge_requests WHERE recharge_id = %s",
            (recharge_id,),
            fetch=True
        )
        return dict(result[0]) if result else None
    
    def update_recharge_status(self, recharge_id: str, status: str) -> bool:
        """Update recharge status"""
        try:
            if status == 'approved':
                self.execute(
                    "UPDATE recharge_requests SET status = %s, approved_at = %s WHERE recharge_id = %s",
                    (status, datetime.now(), recharge_id)
                )
            elif status == 'rejected':
                self.execute(
                    "UPDATE recharge_requests SET status = %s, rejected_at = %s WHERE recharge_id = %s",
                    (status, datetime.now(), recharge_id)
                )
            return True
        except:
            return False
    
    def get_user_recharges(self, user_id: int) -> List[Dict]:
        """Get all recharges for a user"""
        result = self.execute(
            "SELECT * FROM recharge_requests WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
            fetch=True
        )
        return [dict(row) for row in result] if result else []
    
    # ========== PAYMENT METHODS ==========
    
    def add_payment_method(self, method_code: str, name: str, wallet: str, method_type: str) -> bool:
        """Add a new payment method"""
        try:
            self.execute(
                "INSERT INTO payment_methods (method_code, name, wallet, type) VALUES (%s, %s, %s, %s)",
                (method_code, name, wallet, method_type)
            )
            return True
        except:
            return False
    
    def get_payment_methods(self) -> Dict[str, Dict]:
        """Get all payment methods"""
        result = self.execute("SELECT * FROM payment_methods WHERE enabled = TRUE", fetch=True)
        if result:
            return {row['method_code']: dict(row) for row in result}
        return {}
    
    def update_payment_wallet(self, method_code: str, wallet: str) -> bool:
        """Update payment method wallet"""
        try:
            self.execute(
                "UPDATE payment_methods SET wallet = %s WHERE method_code = %s",
                (wallet, method_code)
            )
            return True
        except:
            return False
    
    def remove_payment_method(self, method_code: str) -> bool:
        """Remove a payment method"""
        try:
            self.execute("DELETE FROM payment_methods WHERE method_code = %s", (method_code,))
            return True
        except:
            return False
    
    # ========== COUNTRIES ==========
    
    def add_country(self, country_code: str, name: str, price: float) -> bool:
        """Add a new country"""
        try:
            self.execute(
                "INSERT INTO countries (country_code, name, price) VALUES (%s, %s, %s)",
                (country_code, name, price)
            )
            return True
        except:
            return False
    
    def get_countries(self) -> Dict[str, str]:
        """Get all countries"""
        result = self.execute("SELECT * FROM countries", fetch=True)
        if result:
            return {row['country_code']: row['name'] for row in result}
        return {}
    
    def get_country_prices(self) -> Dict[str, float]:
        """Get all country prices"""
        result = self.execute("SELECT * FROM countries", fetch=True)
        if result:
            return {row['country_code']: float(row['price']) for row in result}
        return {}
    
    def update_country_price(self, country_code: str, price: float) -> bool:
        """Update country price"""
        try:
            self.execute(
                "UPDATE countries SET price = %s WHERE country_code = %s",
                (price, country_code)
            )
            return True
        except:
            return False
    
    def remove_country(self, country_code: str) -> bool:
        """Remove a country"""
        try:
            self.execute("DELETE FROM countries WHERE country_code = %s", (country_code,))
            return True
        except:
            return False
    
    # ========== CONFIG ==========
    
    def set_config(self, key: str, value: str) -> bool:
        """Set a config value"""
        try:
            self.execute(
                """INSERT INTO bot_config (key, value) VALUES (%s, %s) 
                   ON CONFLICT (key) DO UPDATE SET value = %s""",
                (key, value, value)
            )
            return True
        except:
            return False
    
    def get_config(self, key: str, default: str = "") -> str:
        """Get a config value"""
        result = self.execute(
            "SELECT value FROM bot_config WHERE key = %s",
            (key,),
            fetch=True
        )
        return result[0]['value'] if result else default
    
    # ========== PRICING ==========
    
    def set_price(self, category: str, key: str, price: float) -> bool:
        """Set a price"""
        try:
            self.execute(
                """INSERT INTO pricing (category, key, price) VALUES (%s, %s, %s) 
                   ON CONFLICT (category, key) DO UPDATE SET price = %s""",
                (category, key, price, price)
            )
            return True
        except:
            return False
    
    def get_prices(self, category: str) -> Dict[str, float]:
        """Get all prices for a category"""
        result = self.execute(
            "SELECT key, price FROM pricing WHERE category = %s",
            (category,),
            fetch=True
        )
        if result:
            return {row['key']: float(row['price']) for row in result}
        return {}
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Global database instance
db: Optional[Database] = None


def init_database(database_url: str):
    """Initialize the global database instance"""
    global db
    db = Database(database_url)
    return db


def get_db() -> Database:
    """Get the global database instance"""
    if db is None:
        raise RuntimeError("Database not initialized! Call init_database() first.")
    return db
