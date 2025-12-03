"""
Blocking Detector - זיהוי אינדיקטורים לחסימה
מנתח תגובות שרת ומזהה סימנים לחסימה או הגבלות
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BlockingIndicator:
    """מחלקה לתיאור אינדיקטור חסימה"""
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: float  # 0.0-1.0
    reason: str
    suggested_action: str

class BlockingDetector:
    """
    מחלקה לזיהוי אינדיקטורים לחסימה
    מנתחת תגובות HTTP ומזהה דפוסים חשודים
    """
    
    def __init__(self):
        """אתחול הגלאי"""
        self.setup_patterns()
        logger.info("Blocking Detector initialized")
    
    def setup_patterns(self) -> None:
        """הגדרת דפוסים לזיהוי חסימות"""
        
        # קודי HTTP חשודים
        self.suspicious_status_codes = {
            429: ('high', 'Rate limit exceeded'),
            403: ('high', 'Access forbidden'),
            503: ('medium', 'Service unavailable'),
            502: ('medium', 'Bad gateway'),
            504: ('medium', 'Gateway timeout'),
            401: ('medium', 'Unauthorized access'),
            423: ('high', 'Resource locked'),
            509: ('critical', 'Bandwidth limit exceeded')
        }
        
        # דפוסי טקסט בתגובות (case-insensitive)
        self.blocking_patterns = [
            # Rate limiting
            (r'rate\s*limit', 'high', 'Rate limiting detected'),
            (r'too\s*many\s*requests', 'high', 'Too many requests'),
            (r'quota\s*exceeded', 'high', 'Quota exceeded'),
            (r'request\s*limit', 'high', 'Request limit reached'),
            
            # Blocking/Banning
            (r'blocked|banned|suspended', 'critical', 'Account blocked/banned'),
            (r'access\s*denied', 'high', 'Access denied'),
            (r'permission\s*denied', 'high', 'Permission denied'),
            (r'unauthorized', 'medium', 'Unauthorized request'),
            
            # Service issues
            (r'service\s*unavailable', 'medium', 'Service unavailable'),
            (r'temporarily\s*unavailable', 'medium', 'Temporary unavailability'),
            (r'server\s*error', 'low', 'Server error'),
            (r'maintenance', 'low', 'Server maintenance'),
            
            # WhatsApp specific
            (r'whatsapp.*error', 'medium', 'WhatsApp specific error'),
            (r'message.*failed', 'low', 'Message delivery failed'),
            (r'invalid.*phone', 'low', 'Invalid phone number'),
            
            # Network issues
            (r'timeout|timed\s*out', 'low', 'Network timeout'),
            (r'connection.*refused', 'medium', 'Connection refused'),
            (r'network.*error', 'low', 'Network error')
        ]
        
        # כותרות HTTP חשודות
        self.suspicious_headers = {
            'retry-after': ('high', 'Server requested retry delay'),
            'x-ratelimit-remaining': ('medium', 'Rate limit header present'),
            'x-rate-limit-remaining': ('medium', 'Rate limit header present'),
            'cf-ray': ('low', 'Cloudflare protection active')
        }
    
    def detect_blocking_indicators(self, 
                                 response_data: Dict[str, Any]) -> List[BlockingIndicator]:
        """
        מזהה אינדיקטורים לחסימה בתגובת השרת
        
        Args:
            response_data: נתוני התגובה (status_code, text, headers וכו')
            
        Returns:
            רשימת אינדיקטורים שנמצאו
        """
        indicators = []
        
        # בדיקת קוד סטטוס
        status_indicators = self._check_status_code(response_data)
        indicators.extend(status_indicators)
        
        # בדיקת תוכן התגובה
        content_indicators = self._check_response_content(response_data)
        indicators.extend(content_indicators)
        
        # בדיקת כותרות
        header_indicators = self._check_headers(response_data)
        indicators.extend(header_indicators)
        
        # בדיקת זמן תגובה
        timing_indicators = self._check_response_timing(response_data)
        indicators.extend(timing_indicators)
        
        if indicators:
            logger.warning(f"Detected {len(indicators)} blocking indicators")
            for indicator in indicators:
                logger.warning(f"  - {indicator.severity.upper()}: {indicator.reason}")
        
        return indicators
    
    def _check_status_code(self, response_data: Dict[str, Any]) -> List[BlockingIndicator]:
        """בדיקת קוד סטטוס HTTP"""
        indicators = []
        
        status_code = response_data.get('status_code')
        if not status_code:
            return indicators
        
        if status_code in self.suspicious_status_codes:
            severity, reason = self.suspicious_status_codes[status_code]
            confidence = 0.9 if severity == 'critical' else 0.8
            
            suggested_action = self._get_suggested_action(severity, reason)
            
            indicators.append(BlockingIndicator(
                severity=severity,
                confidence=confidence,
                reason=f"HTTP {status_code}: {reason}",
                suggested_action=suggested_action
            ))
        
        return indicators
    
    def _check_response_content(self, response_data: Dict[str, Any]) -> List[BlockingIndicator]:
        """בדיקת תוכן התגובה"""
        indicators = []
        
        # בדיקת טקסט התגובה
        response_text = response_data.get('text', '') or response_data.get('content', '')
        if not response_text:
            return indicators
        
        response_text = str(response_text).lower()
        
        for pattern, severity, reason in self.blocking_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                confidence = self._calculate_pattern_confidence(pattern, response_text)
                suggested_action = self._get_suggested_action(severity, reason)
                
                indicators.append(BlockingIndicator(
                    severity=severity,
                    confidence=confidence,
                    reason=reason,
                    suggested_action=suggested_action
                ))
        
        return indicators
    
    def _check_headers(self, response_data: Dict[str, Any]) -> List[BlockingIndicator]:
        """בדיקת כותרות HTTP"""
        indicators = []
        
        headers = response_data.get('headers', {})
        if not headers:
            return indicators
        
        # המרה לאותיות קטנות לבדיקה
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        for header_name, (severity, reason) in self.suspicious_headers.items():
            if header_name in headers_lower:
                confidence = 0.7
                suggested_action = self._get_suggested_action(severity, reason)
                
                # בדיקה מיוחדת לRetry-After
                if header_name == 'retry-after':
                    retry_value = headers_lower[header_name]
                    reason = f"Server requested retry after {retry_value} seconds"
                    confidence = 0.9
                
                indicators.append(BlockingIndicator(
                    severity=severity,
                    confidence=confidence,
                    reason=reason,
                    suggested_action=suggested_action
                ))
        
        return indicators
    
    def _check_response_timing(self, response_data: Dict[str, Any]) -> List[BlockingIndicator]:
        """בדיקת זמני תגובה חשודים"""
        indicators = []
        
        response_time = response_data.get('response_time')
        if not response_time:
            return indicators
        
        # תגובה איטית מדי (מעל 30 שניות)
        if response_time > 30:
            indicators.append(BlockingIndicator(
                severity='medium',
                confidence=0.6,
                reason=f"Very slow response time: {response_time:.2f}s",
                suggested_action="Consider increasing timeout and adding delays"
            ))
        
        # תגובה מהירה מדי (פחות מ-0.1 שניות) - יכול להעיד על חסימה מיידית
        elif response_time < 0.1:
            indicators.append(BlockingIndicator(
                severity='low',
                confidence=0.4,
                reason=f"Suspiciously fast response: {response_time:.3f}s",
                suggested_action="Monitor for other blocking indicators"
            ))
        
        return indicators
    
    def _calculate_pattern_confidence(self, pattern: str, text: str) -> float:
        """מחשב רמת ביטחון לדפוס שנמצא"""
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        
        # יותר התאמות = ביטחון גבוה יותר
        if matches >= 3:
            return 0.9
        elif matches == 2:
            return 0.8
        else:
            return 0.7
    
    def _get_suggested_action(self, severity: str, reason: str) -> str:
        """מחזיר פעולה מוצעת לפי חומרת הבעיה"""
        action_map = {
            'low': "Continue with increased delays",
            'medium': "Implement exponential backoff",
            'high': "Stop sending temporarily and retry later",
            'critical': "Stop all activity and investigate"
        }
        
        base_action = action_map.get(severity, "Monitor situation")
        
        # פעולות ספציפיות לפי סיבה
        if 'rate limit' in reason.lower():
            return f"{base_action} - Wait for rate limit reset"
        elif 'blocked' in reason.lower() or 'banned' in reason.lower():
            return f"{base_action} - Check account status"
        elif 'unavailable' in reason.lower():
            return f"{base_action} - Wait for service recovery"
        
        return base_action
    
    def get_overall_risk_level(self, indicators: List[BlockingIndicator]) -> Tuple[str, float]:
        """
        מחזיר רמת סיכון כללית על בסיס כל האינדיקטורים
        
        Args:
            indicators: רשימת אינדיקטורים
            
        Returns:
            (רמת סיכון, ציון ביטחון)
        """
        if not indicators:
            return ('none', 0.0)
        
        # חישוב ציון משוקלל
        severity_weights = {'low': 1, 'medium': 2, 'high': 4, 'critical': 8}
        total_score = 0
        max_severity = 'low'
        
        for indicator in indicators:
            weight = severity_weights[indicator.severity]
            score = weight * indicator.confidence
            total_score += score
            
            if severity_weights[indicator.severity] > severity_weights[max_severity]:
                max_severity = indicator.severity
        
        # קביעת רמת סיכון כללית
        if total_score >= 6 or max_severity == 'critical':
            risk_level = 'critical'
        elif total_score >= 4 or max_severity == 'high':
            risk_level = 'high'
        elif total_score >= 2 or max_severity == 'medium':
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        confidence = min(total_score / 10, 1.0)  # נרמול ל-0-1
        
        return (risk_level, confidence)

# פונקציה נוחה לשימוש מהיר
def detect_blocking_indicators(response_data: Dict[str, Any]) -> List[BlockingIndicator]:
    """
    פונקציה נוחה לזיהוי אינדיקטורים לחסימה
    
    Args:
        response_data: נתוני התגובה
        
    Returns:
        רשימת אינדיקטורים שנמצאו
    """
    detector = BlockingDetector()
    return detector.detect_blocking_indicators(response_data)

