"""
WhatsApp Rate Limiter - מנגנון הגבלת קצב שליחת הודעות
מונע שליחת יתר ומקטין את הסיכון לחסימה
"""

import time
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WhatsAppRateLimiter:
    """
    מחלקה לניהול קצב שליחת הודעות WhatsApp
    מבטיחה שלא נחרוג מהמגבלות המוגדרות
    """
    
    def __init__(self, 
                 messages_per_minute: int = 8,
                 messages_per_hour: int = 100):
        """
        אתחול Rate Limiter
        
        Args:
            messages_per_minute: מספר הודעות מקסימלי לדקה
            messages_per_hour: מספר הודעות מקסימלי לשעה
        """
        self.messages_per_minute = messages_per_minute
        self.messages_per_hour = messages_per_hour
        
        # רשימות זמנים של הודעות שנשלחו
        self.minute_timestamps = deque()
        self.hour_timestamps = deque()
        
        logger.info(f"Rate Limiter initialized: {messages_per_minute}/min, {messages_per_hour}/hour")
    
    def can_send_message(self) -> bool:
        """
        בודק אם ניתן לשלוח הודעה כעת
        
        Returns:
            True אם ניתן לשלוח, False אחרת
        """
        current_time = time.time()
        
        # ניקוי timestamps ישנים
        self._cleanup_old_timestamps(current_time)
        
        # בדיקת מגבלות
        minute_ok = len(self.minute_timestamps) < self.messages_per_minute
        hour_ok = len(self.hour_timestamps) < self.messages_per_hour
        
        can_send = minute_ok and hour_ok
        
        if not can_send:
            logger.warning(f"Rate limit reached: minute={len(self.minute_timestamps)}/{self.messages_per_minute}, "
                         f"hour={len(self.hour_timestamps)}/{self.messages_per_hour}")
        
        return can_send
    
    def register_message_sent(self) -> None:
        """
        רושם שהודעה נשלחה
        """
        current_time = time.time()
        
        # הוספת timestamp לשתי הרשימות
        self.minute_timestamps.append(current_time)
        self.hour_timestamps.append(current_time)
        
        logger.debug(f"Message registered: minute={len(self.minute_timestamps)}, hour={len(self.hour_timestamps)}")
    
    def get_wait_time(self) -> Optional[float]:
        """
        מחזיר את זמן ההמתנה הנדרש עד שניתן יהיה לשלוח הודעה
        
        Returns:
            מספר שניות להמתנה, או None אם ניתן לשלוח מיד
        """
        if self.can_send_message():
            return None
        
        current_time = time.time()
        wait_times = []
        
        # בדיקת מגבלת דקה
        if len(self.minute_timestamps) >= self.messages_per_minute:
            oldest_minute = self.minute_timestamps[0]
            wait_time_minute = 60 - (current_time - oldest_minute)
            if wait_time_minute > 0:
                wait_times.append(wait_time_minute)
        
        # בדיקת מגבלת שעה
        if len(self.hour_timestamps) >= self.messages_per_hour:
            oldest_hour = self.hour_timestamps[0]
            wait_time_hour = 3600 - (current_time - oldest_hour)
            if wait_time_hour > 0:
                wait_times.append(wait_time_hour)
        
        return max(wait_times) if wait_times else None
    
    def _cleanup_old_timestamps(self, current_time: float) -> None:
        """
        מנקה timestamps ישנים שכבר לא רלוונטיים
        
        Args:
            current_time: הזמן הנוכחי
        """
        # ניקוי timestamps מעל דקה
        while (self.minute_timestamps and 
               current_time - self.minute_timestamps[0] > 60):
            self.minute_timestamps.popleft()
        
        # ניקוי timestamps מעל שעה
        while (self.hour_timestamps and 
               current_time - self.hour_timestamps[0] > 3600):
            self.hour_timestamps.popleft()
    
    def get_stats(self) -> dict:
        """
        מחזיר סטטיסטיקות נוכחיות
        
        Returns:
            מילון עם נתונים על השימוש הנוכחי
        """
        current_time = time.time()
        self._cleanup_old_timestamps(current_time)
        
        return {
            'messages_last_minute': len(self.minute_timestamps),
            'messages_last_hour': len(self.hour_timestamps),
            'minute_limit': self.messages_per_minute,
            'hour_limit': self.messages_per_hour,
            'can_send': self.can_send_message(),
            'wait_time': self.get_wait_time()
        }
    
    def reset(self) -> None:
        """
        מאפס את כל הנתונים (לשימוש בבדיקות)
        """
        self.minute_timestamps.clear()
        self.hour_timestamps.clear()
        logger.info("Rate limiter reset")

