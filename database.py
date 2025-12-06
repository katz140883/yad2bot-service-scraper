"""
Database module for Yad2bot - SQLite database management
"""
import sqlite3
import logging
import os
import json
import pymysql
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# MySQL/TiDB Configuration for CRM
MYSQL_CONFIG = {
    'host': 'gateway02.us-east-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'user': '294YyfcY7uD3vXV.ea533291bdc2',
    'password': 's7ICuZzz7xIKa32A95GW',
    'database': 'RC5zwvrUDJvQBmcJQAHidc',
    'ssl_verify_cert': True,
    'ssl_verify_identity': True
}

class BotDatabase:
    """SQLite database manager for Yad2bot"""
    
    def __init__(self, db_path: str = "yad2bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table - store user preferences and settings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language TEXT DEFAULT 'hebrew',
                        whatsapp_instance_id TEXT,
                        whatsapp_token TEXT,
                        whatsapp_message TEXT,
                        waiting_for TEXT, -- 'instance_id', 'token', 'message', etc.
                        channel_verified BOOLEAN DEFAULT FALSE,
                        terms_agreed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Schedules table - store auto scheduling settings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        schedule_type TEXT, -- 'scraper' or 'whatsapp'
                        mode TEXT, -- 'rent' or 'sale'
                        filter_type TEXT, -- 'today' or 'all'
                        hour INTEGER,
                        minute INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Activity log table - store bot activity history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT,
                        details TEXT,
                        status TEXT, -- 'success', 'failed', 'in_progress'
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Results table - store scraping results metadata
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        mode TEXT,
                        filter_type TEXT,
                        csv_file_path TEXT,
                        total_listings INTEGER DEFAULT 0,
                        phone_numbers_count INTEGER DEFAULT 0,
                        city_code TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                
                # Add channel_verified column if it doesn't exist (for existing databases)
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN channel_verified BOOLEAN DEFAULT FALSE")
                    conn.commit()
                    logger.info("Added channel_verified column to users table")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                
                # Add terms_agreed column if it doesn't exist (for existing databases)
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN terms_agreed BOOLEAN DEFAULT FALSE")
                    conn.commit()
                    logger.info("Added terms_agreed column to users table")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                
                # Add credits system columns
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN credits_balance REAL DEFAULT 0.0")
                    conn.commit()
                    logger.info("Added credits_balance column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN signup_test_claimed BOOLEAN DEFAULT FALSE")
                    conn.commit()
                    logger.info("Added signup_test_claimed column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
                    conn.commit()
                    logger.info("Added referral_code column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
                    conn.commit()
                    logger.info("Added referred_by column to users table")
                except sqlite3.OperationalError:
                    pass
                
                # Add last_daily_test_at column for daily bonus tracking
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN last_daily_test_at TIMESTAMP")
                    conn.commit()
                    logger.info("Added last_daily_test_at column to users table")
                except sqlite3.OperationalError:
                    pass
                
                # Add AI conversation columns
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN ai_enabled BOOLEAN DEFAULT FALSE")
                    conn.commit()
                    logger.info("Added ai_enabled column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN ai_prompt TEXT")
                    conn.commit()
                    logger.info("Added ai_prompt column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN azure_api_key TEXT")
                    conn.commit()
                    logger.info("Added azure_api_key column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN azure_endpoint TEXT")
                    conn.commit()
                    logger.info("Added azure_endpoint column to users table")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN azure_deployment TEXT")
                    conn.commit()
                    logger.info("Added azure_deployment column to users table")
                except sqlite3.OperationalError:
                    pass
                
                # Credits ledger table for transaction history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS credits_ledger (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        transaction_type TEXT, -- 'credit', 'debit'
                        amount REAL,
                        reason TEXT, -- 'signup_test', 'referral_test', 'scraping_cost', etc.
                        balance_after REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # AI conversations table - store conversation history for AI responses
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ai_conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        campaign_id INTEGER,
                        recipient_jid TEXT,
                        message_history TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (campaign_id) REFERENCES results (id)
                    )
                ''')
                
                # CRM Leads table - store all leads (manual + scraped)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS leads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        phone TEXT NOT NULL,
                        name TEXT,
                        city TEXT,
                        address TEXT,
                        floor TEXT,
                        rooms TEXT,
                        price TEXT,
                        published_at TEXT,
                        type TEXT, -- 'manual', 'rent', 'sale'
                        source TEXT DEFAULT 'manual', -- 'manual', 'scraper', 'chat'
                        notes TEXT,
                        status TEXT DEFAULT 'active', -- 'active', 'archived', 'deleted'
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # CRM Followups table - store followup tasks
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS followups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lead_id INTEGER,
                        user_id INTEGER,
                        followup_date TIMESTAMP NOT NULL,
                        frequency TEXT, -- 'once', 'daily', 'weekly', 'monthly'
                        notes TEXT,
                        status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'cancelled'
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lead_id) REFERENCES leads (id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_followups_lead_id ON followups(lead_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_followups_user_id ON followups(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_followups_date ON followups(followup_date)')
                
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data by user_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def add_user(self, user_id: int, username: str = None, 
                first_name: str = None, last_name: str = None) -> bool:
        """Add a new user to the database"""
        return self.update_user(user_id, username, first_name, last_name)
    
    def update_user(self, user_id: int, username: str = None, first_name: str = None,
                             last_name: str = None, language: str = None, 
                             whatsapp_instance_id: str = None, whatsapp_token: str = None,
                             whatsapp_message: str = None, waiting_for: str = None,
                             webhook_url: str = None) -> bool:
        """Create new user or update existing user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing user
                    update_fields = []
                    update_values = []
                    
                    if username is not None:
                        update_fields.append("username = ?")
                        update_values.append(username)
                    if first_name is not None:
                        update_fields.append("first_name = ?")
                        update_values.append(first_name)
                    if last_name is not None:
                        update_fields.append("last_name = ?")
                        update_values.append(last_name)
                    if language is not None:
                        update_fields.append("language = ?")
                        update_values.append(language)
                    if whatsapp_instance_id is not None:
                        update_fields.append("whatsapp_instance_id = ?")
                        update_values.append(whatsapp_instance_id)
                    if whatsapp_token is not None:
                        update_fields.append("whatsapp_token = ?")
                        update_values.append(whatsapp_token)
                    if whatsapp_message is not None:
                        update_fields.append("whatsapp_message = ?")
                        update_values.append(whatsapp_message)
                    if waiting_for is not None:
                        update_fields.append("waiting_for = ?")
                        update_values.append(waiting_for)
                    if webhook_url is not None:
                        update_fields.append("webhook_url = ?")
                        update_values.append(webhook_url)
                    
                    if update_fields:
                        update_fields.append("updated_at = CURRENT_TIMESTAMP")
                        update_values.append(user_id)
                        
                        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
                        cursor.execute(query, update_values)
                else:
                    # Create new user
                    cursor.execute('''
                        INSERT INTO users (user_id, username, first_name, last_name, language, 
                                         whatsapp_instance_id, whatsapp_token, whatsapp_message, waiting_for)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, first_name, last_name, 
                          language or 'hebrew', whatsapp_instance_id, whatsapp_token, whatsapp_message, waiting_for))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {e}")
            return False
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else 'hebrew'
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return 'hebrew'
    
    def set_user_language(self, user_id: int, language: str) -> bool:
        """Set user's preferred language"""
        return self.update_user(user_id, language=language)
    
    def get_user_waiting_for(self, user_id: int) -> Optional[str]:
        """Get what the user is waiting for input"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT waiting_for FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user waiting_for: {e}")
            return None
    
    def set_user_waiting_for(self, user_id: int, waiting_for: str = None) -> bool:
        """Set what the user is waiting for input"""
        return self.update_user(user_id, waiting_for=waiting_for)
    
    def get_user_whatsapp_config(self, user_id: int) -> Dict[str, str]:
        """Get user's WhatsApp configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT whatsapp_instance_id, whatsapp_token, whatsapp_message 
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'instance_id': result[0] or '',
                        'token': result[1] or '',
                        'message': result[2] or ''
                    }
                return {'instance_id': '', 'token': '', 'message': ''}
                
        except Exception as e:
            logger.error(f"Error getting WhatsApp config: {e}")
            return {'instance_id': '', 'token': '', 'message': ''}
    
    def set_user_whatsapp_config(self, user_id: int, instance_id: str = None, 
                                token: str = None, message: str = None) -> bool:
        """Set user's WhatsApp configuration"""
        return self.update_user(user_id, whatsapp_instance_id=instance_id, 
                              whatsapp_token=token, whatsapp_message=message)
    
    def get_user_whatsapp_instance(self, user_id: int) -> str:
        """Get user's WhatsApp instance ID"""
        config = self.get_user_whatsapp_config(user_id)
        return config.get('instance_id', '')
    
    def set_user_whatsapp_instance(self, user_id: int, instance_id: str) -> bool:
        """Set user's WhatsApp instance ID"""
        return self.update_user(user_id, whatsapp_instance_id=instance_id)
    
    def set_user_whatsapp_token(self, user_id: int, token: str) -> bool:
        """Set user's WhatsApp token"""
        return self.update_user(user_id, whatsapp_token=token)
    
    def get_user_webhook_url(self, user_id: int) -> str:
        """Get user's webhook URL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT webhook_url FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else ''
        except Exception as e:
            logger.error(f"Error getting webhook URL: {e}")
            return ''
    
    def set_user_webhook_url(self, user_id: int, webhook_url: str) -> bool:
        """Set user's webhook URL"""
        return self.update_user(user_id, webhook_url=webhook_url)
    
    def set_last_scraping_result(self, user_id: int, file_path: str) -> bool:
        """Store the last scraping result file path for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_scraping_result = ?
                    WHERE user_id = ?
                ''', (file_path, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing last scraping result: {e}")
            return False
    
    def get_last_scraping_result(self, user_id: int) -> Optional[str]:
        """Get the last scraping result file path for user"""
        try:
            user = self.get_user(user_id)
            if user and user.get('last_scraping_result'):
                return user['last_scraping_result']
            return None
        except Exception as e:
            logger.error(f"Error getting last scraping result: {e}")
            return None
    
    # Schedule management methods
    def add_schedule(self, user_id: int, schedule_type: str, mode: str, 
                    filter_type: str, hour: int, minute: int) -> bool:
        """Add a new schedule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, deactivate any existing schedules of the same type for this user
                cursor.execute('''
                    UPDATE schedules 
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ? AND schedule_type = ?
                ''', (user_id, schedule_type))
                
                # Add new schedule
                cursor.execute('''
                    INSERT INTO schedules (user_id, schedule_type, mode, filter_type, hour, minute)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, schedule_type, mode, filter_type, hour, minute))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            return False
    
    def get_user_schedules(self, user_id: int) -> List[Dict]:
        """Get all active schedules for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM schedules 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting user schedules: {e}")
            return []
    
    def get_all_active_schedules(self) -> List[Dict]:
        """Get all active schedules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM schedules 
                    WHERE is_active = 1
                    ORDER BY hour, minute
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting all schedules: {e}")
            return []
    
    def cancel_user_schedules(self, user_id: int, schedule_type: str = None) -> bool:
        """Cancel user schedules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if schedule_type:
                    cursor.execute('''
                        UPDATE schedules 
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ? AND schedule_type = ?
                    ''', (user_id, schedule_type))
                else:
                    cursor.execute('''
                        UPDATE schedules 
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error canceling schedules: {e}")
            return False
    
    # Activity logging methods
    def log_activity(self, user_id: int, action: str, details: str = "", status: str = "success") -> bool:
        """Log user activity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details, status)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, action, details, status))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return False
    
    def get_user_activity(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user activity history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM activity_log 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return []
    
    # Results management methods
    def save_scraping_result(self, user_id: int, mode: str, filter_type: str, 
                           csv_file_path: str, total_listings: int = 0, 
                           phone_numbers_count: int = 0, city_code: str = None) -> bool:
        """Save scraping result metadata and sync leads to MySQL"""
        try:
            # Save metadata to SQLite
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO results (user_id, mode, filter_type, csv_file_path, 
                                       total_listings, phone_numbers_count, city_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, mode, filter_type, csv_file_path, total_listings, phone_numbers_count, city_code))
                conn.commit()
            
            # Sync leads to MySQL/TiDB for CRM
            try:
                import csv
                if os.path.exists(csv_file_path):
                    with open(csv_file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        success_count = 0
                        for row in reader:
                            # Only sync if there's a phone number
                            if row.get('phone_number', '').strip():
                                # Create WhatsApp link
                                phone = row.get('phone_number', '').strip()
                                if phone.startswith('0'):
                                    phone = '972' + phone[1:]  # Convert to international format
                                row['whatsapp_link'] = f'https://wa.me/{phone}'
                                
                                if save_lead_to_mysql(user_id, row, mode, filter_type):
                                    success_count += 1
                                else:
                                    logger.warning(f"Failed to save lead: {row.get('phone_number')}")
                    logger.info(f"Synced {success_count} leads to MySQL for user {user_id}")
            except Exception as sync_error:
                logger.error(f"Error syncing leads to MySQL: {sync_error}")
                # Don't fail the whole operation if MySQL sync fails
            
            return True
                
        except Exception as e:
            logger.error(f"Error saving scraping result: {e}")
            return False
    
    def get_user_results(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Get user's scraping results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM results 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting user results: {e}")
            return []
    
    def get_user_credits_balance(self, user_id: int) -> float:
        """Get user's current credits balance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT credits_balance FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Error getting credits balance for user {user_id}: {e}")
            return 0.0
    
    def credit_user_account(self, user_id: int, amount: float, reason: str) -> bool:
        """Add credits to user account and log transaction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current balance
                current_balance = self.get_user_credits_balance(user_id)
                new_balance = current_balance + amount
                
                # Update user balance
                cursor.execute('''
                    UPDATE users 
                    SET credits_balance = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (new_balance, user_id))
                
                # Log transaction
                cursor.execute('''
                    INSERT INTO credits_ledger 
                    (user_id, transaction_type, amount, reason, balance_after)
                    VALUES (?, 'credit', ?, ?, ?)
                ''', (user_id, amount, reason, new_balance))
                
                conn.commit()
                logger.info(f"Credited {amount} credits to user {user_id}. New balance: {new_balance}")
                return True
                
        except Exception as e:
            logger.error(f"Error crediting user {user_id}: {e}")
            return False
    
    def debit_user_account(self, user_id: int, amount: float, reason: str) -> bool:
        """Deduct credits from user account and log transaction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current balance
                current_balance = self.get_user_credits_balance(user_id)
                
                if current_balance < amount:
                    logger.warning(f"Insufficient credits for user {user_id}. Balance: {current_balance}, Required: {amount}")
                    return False
                
                new_balance = current_balance - amount
                
                # Update user balance
                cursor.execute('''
                    UPDATE users 
                    SET credits_balance = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (new_balance, user_id))
                
                # Log transaction
                cursor.execute('''
                    INSERT INTO credits_ledger 
                    (user_id, transaction_type, amount, reason, balance_after)
                    VALUES (?, 'debit', ?, ?, ?)
                ''', (user_id, amount, reason, new_balance))
                
                conn.commit()
                logger.info(f"Debited {amount} credits from user {user_id}. New balance: {new_balance}")
                return True
                
        except Exception as e:
            logger.error(f"Error debiting user {user_id}: {e}")
            return False
    
    def has_claimed_signup_test(self, user_id: int) -> bool:
        """Check if user has already claimed signup bonus"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT signup_test_claimed FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return bool(result[0]) if result and result[0] is not None else False
        except Exception as e:
            logger.error(f"Error checking signup bonus for user {user_id}: {e}")
            return False
    
    def claim_signup_test(self, user_id: int) -> bool:
        """Claim signup bonus for user"""
        try:
            if self.has_claimed_signup_test(user_id):
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Mark bonus as claimed
                cursor.execute('''
                    UPDATE users 
                    SET signup_test_claimed = TRUE, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                
                # Credit the bonus amount
                return self.credit_user_account(user_id, 100.0, 'signup_test_claim')
                
        except Exception as e:
            logger.error(f"Error claiming signup bonus for user {user_id}: {e}")
            return False
    
    def generate_referral_code(self, user_id: int) -> str:
        """Generate and store referral code for user"""
        import random
        import string
        
        try:
            # Generate a unique referral code
            referral_code = f"YAD2_{user_id}_{random.randint(1000, 9999)}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET referral_code = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (referral_code, user_id))
                conn.commit()
                
            return referral_code
            
        except Exception as e:
            logger.error(f"Error generating referral code for user {user_id}: {e}")
            return ""
    
    def get_user_referral_code(self, user_id: int) -> str:
        """Get user's referral code, generate if doesn't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    return result[0]
                else:
                    # Generate new referral code
                    return self.generate_referral_code(user_id)
                    
        except Exception as e:
            logger.error(f"Error getting referral code for user {user_id}: {e}")
            return ""
    
    def get_referral_count(self, user_id: int) -> int:
        """Get number of users referred by this user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting referral count for user {user_id}: {e}")
            return 0
    
    def has_user_agreed_to_terms(self, user_id: int) -> bool:
        """Check if user has agreed to terms of service"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT terms_agreed FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error checking if user agreed to terms: {e}")
            return False
    
    def set_user_terms_agreement(self, user_id: int, agreed: bool):
        """Set user's terms of service agreement status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET terms_agreed = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (agreed, user_id))
                conn.commit()
                logger.info(f"Terms agreement set for user {user_id}: {agreed}")
        except Exception as e:
            logger.error(f"Error setting terms agreement: {e}")
    
    def get_last_daily_test_time(self, user_id: int) -> Optional[datetime]:
        """Get the last time user claimed daily bonus"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT last_daily_test_at FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    return datetime.fromisoformat(result[0])
                return None
        except Exception as e:
            logger.error(f"Error getting last daily bonus time for user {user_id}: {e}")
            return None
    
    def claim_daily_test(self, user_id: int, amount: float = 50.0) -> bool:
        """Claim daily bonus for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update last_daily_test_at
                cursor.execute('''
                    UPDATE users 
                    SET last_daily_test_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                
                # Credit the bonus amount
                return self.credit_user_account(user_id, amount, 'daily_test')
                
        except Exception as e:
            logger.error(f"Error claiming daily bonus for user {user_id}: {e}")
            return False
    
    def get_total_listings_scraped(self, user_id: int) -> int:
        """Get total number of listings scraped by user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT SUM(total_listings) FROM results WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            logger.error(f"Error getting total listings for user {user_id}: {e}")
            return 0
    
    def get_total_messages_sent(self, user_id: int) -> int:
        """Get total number of WhatsApp messages sent by user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT SUM(phone_numbers_count) FROM results WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            logger.error(f"Error getting total messages for user {user_id}: {e}")
            return 0
    
    # AI Conversation Methods
    
    def set_ai_enabled(self, user_id: int, enabled: bool) -> bool:
        """Enable or disable AI for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET ai_enabled = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (enabled, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting AI enabled for user {user_id}: {e}")
            return False
    
    def set_ai_prompt(self, user_id: int, prompt: str) -> bool:
        """Set AI prompt for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET ai_prompt = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (prompt, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting AI prompt for user {user_id}: {e}")
            return False
    
    def get_ai_settings(self, user_id: int) -> Optional[Dict]:
        """Get AI settings for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ai_enabled, ai_prompt, azure_api_key, azure_endpoint, azure_deployment
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting AI settings for user {user_id}: {e}")
            return None
    
    def save_ai_conversation(self, user_id: int, campaign_id: int, recipient_jid: str, message_history: str) -> bool:
        """Save or update AI conversation history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if conversation exists
                cursor.execute('''
                    SELECT id FROM ai_conversations 
                    WHERE user_id = ? AND campaign_id = ? AND recipient_jid = ?
                ''', (user_id, campaign_id, recipient_jid))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing conversation
                    cursor.execute('''
                        UPDATE ai_conversations 
                        SET message_history = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ? AND campaign_id = ? AND recipient_jid = ?
                    ''', (message_history, user_id, campaign_id, recipient_jid))
                else:
                    # Create new conversation
                    cursor.execute('''
                        INSERT INTO ai_conversations (user_id, campaign_id, recipient_jid, message_history)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, campaign_id, recipient_jid, message_history))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving AI conversation: {e}")
            return False
    
    def get_ai_conversation(self, user_id: int, campaign_id: int, recipient_jid: str) -> Optional[Dict]:
        """Get AI conversation history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM ai_conversations 
                    WHERE user_id = ? AND campaign_id = ? AND recipient_jid = ? AND is_active = TRUE
                ''', (user_id, campaign_id, recipient_jid))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting AI conversation: {e}")
            return None


    # ========== CRM Functions ==========
    
    def add_lead(self, user_id: int, phone: str, name: str = None, city: str = None,
                 address: str = None, floor: str = None, rooms: str = None, size: str = None,
                 price: str = None, published_at: str = None, lead_type: str = 'manual',
                 source: str = 'manual', notes: str = None) -> Optional[int]:
        """Add a new lead to CRM"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO leads (user_id, phone, name, city, address, floor, rooms, size, price,
                                      published_at, type, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, phone, name, city, address, floor, rooms, size, price, 
                      published_at, lead_type, source, notes))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding lead: {e}")
            return None
    
    def get_lead_by_phone(self, user_id: int, phone: str) -> Optional[Dict]:
        """Get lead by phone number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM leads 
                    WHERE user_id = ? AND phone = ? AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                ''', (user_id, phone))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting lead by phone: {e}")
            return None
    
    def get_lead(self, lead_id: int) -> Optional[Dict]:
        """Get lead by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting lead: {e}")
            return None
    
    def update_lead(self, lead_id: int, **kwargs) -> bool:
        """Update lead fields"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                fields = []
                values = []
                for key, value in kwargs.items():
                    if key in ['name', 'city', 'address', 'floor', 'rooms', 'price', 
                              'published_at', 'type', 'source', 'notes', 'status']:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    return False
                
                fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(lead_id)
                
                query = f"UPDATE leads SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            return False
    
    def get_leads(self, user_id: int, lead_type: str = None, search: str = None) -> List[Dict]:
        """Get all leads for user, optionally filtered by type and search"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM leads WHERE user_id = ? AND status = 'active'"
                params = [user_id]
                
                if lead_type:
                    query += " AND type = ?"
                    params.append(lead_type)
                
                if search:
                    query += " AND (phone LIKE ? OR city LIKE ? OR address LIKE ? OR name LIKE ?)"
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern] * 4)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return []
    
    def delete_lead(self, lead_id: int) -> bool:
        """Soft delete a lead"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE leads SET status = 'deleted', updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (lead_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting lead: {e}")
            return False
    
    def add_followup(self, lead_id: int, user_id: int, followup_date: str, 
                    frequency: str = 'once', notes: str = None) -> Optional[int]:
        """Add a followup task"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO followups (lead_id, user_id, followup_date, frequency, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (lead_id, user_id, followup_date, frequency, notes))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding followup: {e}")
            return None
    
    def get_followups(self, lead_id: int) -> List[Dict]:
        """Get all followups for a lead"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM followups 
                    WHERE lead_id = ? AND status != 'cancelled'
                    ORDER BY followup_date ASC
                ''', (lead_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting followups: {e}")
            return []
    
    def get_next_followup(self, lead_id: int) -> Optional[Dict]:
        """Get next pending followup for a lead"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM followups 
                    WHERE lead_id = ? AND status = 'pending'
                    ORDER BY followup_date ASC LIMIT 1
                ''', (lead_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting next followup: {e}")
            return None
    
    def update_followup(self, followup_id: int, status: str = None, notes: str = None) -> bool:
        """Update followup status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if status == 'completed':
                    cursor.execute('''
                        UPDATE followups 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (status, followup_id))
                elif status:
                    cursor.execute('''
                        UPDATE followups 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (status, followup_id))
                
                if notes:
                    cursor.execute('''
                        UPDATE followups 
                        SET notes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (notes, followup_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating followup: {e}")
            return False
    
    def get_pending_followups(self, user_id: int) -> List[Dict]:
        """Get all pending followups for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT f.*, l.phone, l.name, l.city, l.address 
                    FROM followups f
                    JOIN leads l ON f.lead_id = l.id
                    WHERE f.user_id = ? AND f.status = 'pending' AND l.status = 'active'
                    ORDER BY f.followup_date ASC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting pending followups: {e}")
            return []


def check_lead_exists_in_mysql(listing_url: str) -> bool:
    """
    Check if a lead with this listing URL already exists in MySQL CRM
    
    Args:
        listing_url: The URL of the listing to check
    
    Returns:
        True if exists, False otherwise
    """
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        query = "SELECT COUNT(*) FROM leads WHERE listingUrl = %s"
        cursor.execute(query, (listing_url,))
        count = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        return count > 0
        
    except Exception as e:
        logger.error(f"Error checking if lead exists: {e}")
        # If there's an error, return False to allow the scrape to continue
        return False


def save_lead_to_mysql(telegram_user_id: int, lead_data: Dict, scan_type: str, filter_type: str = 'all') -> bool:
    """
    Save lead to MySQL/TiDB database for CRM
    
    Args:
        telegram_user_id: Telegram user ID
        lead_data: Dictionary with lead info from CSV
        scan_type: 'rent' or 'sale'
        filter_type: 'today', 'all', or 'test'
    
    Returns:
        True if successful, False otherwise
    """
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        # Map filter_type: bonus -> all for CRM enum
        crm_filter_type = 'today' if filter_type == 'today' else 'all'
        
        # Debug logging
        logger.debug(f"Saving lead to MySQL: phone={lead_data.get('phone_number')}, scan_type={scan_type}, filter_type={filter_type}")
        
        # Use INSERT IGNORE to skip duplicates based on listingUrl
        # This prevents duplicate leads from being saved if the same listing is scraped again
        query = """
        INSERT IGNORE INTO leads 
        (userId, phoneNumber, contactName, location, rooms, size, floor, price, 
         leadType, filterType, scrapedAt, listingUrl, title, whatsappLink)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
        """
        
        values = (
            1,  # Always use CRM userId = 1 (not Telegram ID)
            lead_data.get('phone_number', lead_data.get('phone', '')),
            lead_data.get('owner_name', lead_data.get('name', lead_data.get('contact_name', ''))),
            lead_data.get('address', lead_data.get('location', '')),
            lead_data.get('rooms', ''),
            lead_data.get('size', ''),
            lead_data.get('floor', ''),
            lead_data.get('price', ''),
            scan_type,  # 'rent' or 'sale'
            crm_filter_type,  # 'today' or 'all'
            lead_data.get('listing_url', lead_data.get('url', '')),
            lead_data.get('title', ''),
            lead_data.get('whatsapp_link', '')
        )
        
        try:
            cursor.execute(query, values)
            affected_rows = cursor.rowcount
            connection.commit()
            
            if affected_rows > 0:
                logger.info(f"✅ Lead saved to MySQL: {lead_data.get('phone_number')} - {scan_type}/{filter_type}")
            else:
                logger.info(f"⏭️  Lead already exists (skipped): {lead_data.get('listing_url', 'no-url')}")
            
            return True
        except Exception as exec_error:
            logger.error(f"Error executing query: {exec_error}")
            logger.error(f"Query: {query}")
            logger.error(f"Values: {values}")
            return False
        finally:
            cursor.close()
            connection.close()
        
    except Exception as e:
        logger.error(f"Error saving lead to MySQL: {e}")
        return False


# Global database instance
db = BotDatabase()

