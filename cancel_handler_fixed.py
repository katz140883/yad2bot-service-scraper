#!/usr/bin/env python3
"""
Fixed Cancel Handler - Works with the new final scraper manager
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_cancel_scrape_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel scrape button with the new scraper manager."""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        logger.info(f"[CancelHandler] Cancel scrape requested by user {user_id}")
        
        # Import the final scraper manager
        from scraper_manager_final import final_scraper_manager
        
        # Cancel the scraping
        cancelled = final_scraper_manager.cancel_current_scraping(user_id)
        
        if cancelled:
            logger.info(f"[CancelHandler] Successfully cancelled scraping for user {user_id}")
            
            # Update message to show cancellation
            cancel_text = "❌ הסריקה בוטלה בהצלחה" 
            try:
                await query.message.edit_text(cancel_text)
                logger.info(f"[CancelHandler] Cancel message updated for user {user_id}")
            except Exception as e:
                logger.error(f"[CancelHandler] Error updating cancel message: {e}")
        else:
            logger.info(f"[CancelHandler] No active scraping found for user {user_id}")
            
            # Update message to show no active scraping
            no_active_text = "ℹ️ אין סריקה פעילה לביטול"
            try:
                await query.message.edit_text(no_active_text)
                logger.info(f"[CancelHandler] No active scraping message updated for user {user_id}")
            except Exception as e:
                logger.error(f"[CancelHandler] Error updating no active message: {e}")
        
    except Exception as e:
        logger.error(f"[CancelHandler] Error in cancel handler: {e}")
        
        # Try to send error message
        try:
            await update.callback_query.message.edit_text("❌ שגיאה בביטול הסריקה")
        except:
            pass
