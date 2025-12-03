"""
Sent Messages Tracking Module
Prevents duplicate message sending to the same phone numbers
"""

import sqlite3
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class SentMessagesTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def is_phone_sent(self, user_id: int, phone: str) -> bool:
        """
        Check if a message was already sent to this phone number
        
        Args:
            user_id: Telegram user ID
            phone: Phone number (will be normalized)
            
        Returns:
            True if message was already sent, False otherwise
        """
        try:
            # Normalize phone number (remove all non-digits)
            normalized_phone = ''.join(filter(str.isdigit, phone))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT COUNT(*) FROM sent_messages WHERE user_id = ? AND phone = ?',
                (user_id, normalized_phone)
            )
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking if phone was sent: {e}")
            return False
    
    def mark_phone_sent(self, user_id: int, phone: str, message: str = None, campaign_id: int = 0) -> bool:
        """
        Mark a phone number as sent
        
        Args:
            user_id: Telegram user ID
            phone: Phone number (will be normalized)
            message: Optional message content
            campaign_id: Optional campaign ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize phone number
            normalized_phone = ''.join(filter(str.isdigit, phone))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                '''INSERT OR REPLACE INTO sent_messages 
                   (user_id, phone, message, campaign_id, sent_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                (user_id, normalized_phone, message, campaign_id)
            )
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking phone as sent: {e}")
            return False
    
    def filter_unsent_phones(self, user_id: int, phone_numbers: List[str]) -> List[str]:
        """
        Filter out phone numbers that were already sent
        
        Args:
            user_id: Telegram user ID
            phone_numbers: List of phone numbers
            
        Returns:
            List of phone numbers that haven't been sent yet
        """
        try:
            unsent = []
            for phone in phone_numbers:
                if not self.is_phone_sent(user_id, phone):
                    unsent.append(phone)
            
            return unsent
            
        except Exception as e:
            logger.error(f"Error filtering unsent phones: {e}")
            return phone_numbers  # Return all if error
    
    def get_sent_count(self, user_id: int) -> int:
        """
        Get total count of sent messages for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of unique phone numbers sent to
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT COUNT(*) FROM sent_messages WHERE user_id = ?',
                (user_id,)
            )
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting sent count: {e}")
            return 0
    
    def clear_sent_history(self, user_id: int) -> bool:
        """
        Clear all sent message history for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM sent_messages WHERE user_id = ?',
                (user_id,)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared sent history for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing sent history: {e}")
            return False
    
    def get_sent_phones(self, user_id: int, limit: int = 100) -> List[dict]:
        """
        Get list of sent phone numbers for a user
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of records to return
            
        Returns:
            List of dicts with phone, sent_at, message
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                '''SELECT phone, sent_at, message 
                   FROM sent_messages 
                   WHERE user_id = ? 
                   ORDER BY sent_at DESC 
                   LIMIT ?''',
                (user_id, limit)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'phone': row[0],
                    'sent_at': row[1],
                    'message': row[2]
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting sent phones: {e}")
            return []
