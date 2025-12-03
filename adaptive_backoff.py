"""
Adaptive Backoff - מנגנון התאמה אדפטיבית לכשלונות
מגדיל את זמן ההמתנה כאשר מתרחשות שגיאות ומאפס כאשר הכל עובד
"""

import time
import random
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class BackoffLevel(Enum):
    """רמות Backoff שונות"""
    NORMAL = 0      # רגיל - אין בעיות
    WARNING = 1     # אזהרה - כשלון ראשון
    MODERATE = 2    # בינוני - מספר כשלונות
    SEVERE = 3      # חמור - כשלונות רבים
    CRITICAL = 4    # קריטי - חסימה אפשרית

class AdaptiveBackoff:
    """
    מחלקה לניהול Backoff אדפטיבי
    מתאימה את זמן ההמתנה לפי מצב השרת והתגובות
    """
    
    def __init__(self, 
                 base_delay: float = 2.0,
                 max_delay: float = 300.0,
                 backoff_multiplier: float = 2.0,
                 success_threshold: int = 3):
        """
        אתחול Adaptive Backoff
        
        Args:
            base_delay: עיכוב בסיסי בשניות
            max_delay: עיכוב מקסימלי בשניות
            backoff_multiplier: מכפיל הגדלת העיכוב
            success_threshold: מספר הצלחות לאיפוס הרמה
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.success_threshold = success_threshold
        
        # מצב נוכחי
        self.current_level = BackoffLevel.NORMAL
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.total_failures = 0
        self.total_successes = 0
        
        # הגדרות רמות
        self.level_delays = {
            BackoffLevel.NORMAL: base_delay,
            BackoffLevel.WARNING: base_delay * 2,
            BackoffLevel.MODERATE: base_delay * 4,
            BackoffLevel.SEVERE: base_delay * 8,
            BackoffLevel.CRITICAL: base_delay * 16
        }
        
        logger.info(f"Adaptive Backoff initialized: base={base_delay}s, max={max_delay}s")
    
    def register_success(self) -> None:
        """
        רושם הצלחה בשליחת הודעה
        """
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.total_successes += 1
        
        # אם יש מספיק הצלחות רצופות, מורידים רמה
        if (self.consecutive_successes >= self.success_threshold and 
            self.current_level != BackoffLevel.NORMAL):
            self._decrease_level()
            self.consecutive_successes = 0
        
        logger.debug(f"Success registered: level={self.current_level.name}, "
                    f"consecutive_successes={self.consecutive_successes}")
    
    def register_failure(self, error_info: Optional[Dict[str, Any]] = None) -> None:
        """
        רושם כשלון בשליחת הודעה
        
        Args:
            error_info: מידע על השגיאה (קוד, הודעה וכו')
        """
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.total_failures += 1
        self.last_failure_time = time.time()
        
        # הגדלת רמת Backoff לפי מספר הכשלונות
        if self.consecutive_failures == 1:
            self._set_level(BackoffLevel.WARNING)
        elif self.consecutive_failures == 2:
            self._set_level(BackoffLevel.MODERATE)
        elif self.consecutive_failures >= 3:
            self._set_level(BackoffLevel.SEVERE)
        
        # אם יש אינדיקטור לחסימה, עוברים לרמה קריטית
        if error_info and self._is_blocking_error(error_info):
            self._set_level(BackoffLevel.CRITICAL)
        
        logger.warning(f"Failure registered: level={self.current_level.name}, "
                      f"consecutive_failures={self.consecutive_failures}, "
                      f"error_info={error_info}")
    
    def get_delay(self) -> float:
        """
        מחזיר את זמן העיכוב הנוכחי
        
        Returns:
            זמן עיכוב בשניות (עם רנדומיזציה)
        """
        base_delay = self.level_delays[self.current_level]
        
        # הוספת רנדומיזציה (±20%)
        randomized_delay = base_delay * random.uniform(0.8, 1.2)
        
        # הגבלה למקסימום
        final_delay = min(randomized_delay, self.max_delay)
        
        logger.debug(f"Calculated delay: {final_delay:.2f}s (level={self.current_level.name})")
        
        return final_delay
    
    def should_abort(self) -> bool:
        """
        בודק אם כדאי להפסיק את השליחה זמנית
        
        Returns:
            True אם כדאי להפסיק
        """
        # אם יש יותר מדי כשלונות רצופות
        if self.consecutive_failures >= 5:
            return True
        
        # אם אנחנו ברמה קריטית יותר מ-10 דקות
        if (self.current_level == BackoffLevel.CRITICAL and 
            self.last_failure_time and 
            time.time() - self.last_failure_time > 600):
            return True
        
        return False
    
    def _set_level(self, level: BackoffLevel) -> None:
        """
        מגדיר רמת Backoff חדשה
        
        Args:
            level: הרמה החדשה
        """
        if level != self.current_level:
            old_level = self.current_level
            self.current_level = level
            logger.info(f"Backoff level changed: {old_level.name} -> {level.name}")
    
    def _decrease_level(self) -> None:
        """
        מוריד רמת Backoff בדרגה אחת
        """
        current_value = self.current_level.value
        if current_value > 0:
            new_level = BackoffLevel(current_value - 1)
            self._set_level(new_level)
    
    def _is_blocking_error(self, error_info: Dict[str, Any]) -> bool:
        """
        בודק אם השגיאה מעידה על חסימה
        
        Args:
            error_info: מידע על השגיאה
            
        Returns:
            True אם זה נראה כמו חסימה
        """
        # קודי שגיאה שמעידים על חסימה
        blocking_codes = [429, 403, 503, 502, 504]
        
        # מילות מפתח בהודעות שגיאה
        blocking_keywords = [
            'rate limit', 'too many requests', 'blocked', 'banned',
            'temporarily unavailable', 'service unavailable',
            'quota exceeded', 'access denied'
        ]
        
        # בדיקת קוד שגיאה
        if 'status_code' in error_info:
            if error_info['status_code'] in blocking_codes:
                return True
        
        # בדיקת הודעת שגיאה
        if 'message' in error_info:
            message = str(error_info['message']).lower()
            for keyword in blocking_keywords:
                if keyword in message:
                    return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        מחזיר סטטיסטיקות נוכחיות
        
        Returns:
            מילון עם נתונים על המצב הנוכחי
        """
        return {
            'current_level': self.current_level.name,
            'current_delay': self.get_delay(),
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'total_failures': self.total_failures,
            'total_successes': self.total_successes,
            'success_rate': (self.total_successes / max(1, self.total_successes + self.total_failures)) * 100,
            'should_abort': self.should_abort(),
            'last_failure_time': self.last_failure_time
        }
    
    def reset(self) -> None:
        """
        מאפס את כל הנתונים
        """
        self.current_level = BackoffLevel.NORMAL
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.total_failures = 0
        self.total_successes = 0
        logger.info("Adaptive Backoff reset")

