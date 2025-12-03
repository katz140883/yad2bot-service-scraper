#!/usr/bin/env python3
"""
Authentication handler for Scraper Service Bot
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

load_dotenv('yad2bot.env')
logger = logging.getLogger(__name__)

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'fuckfadi123')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with password authentication"""
    user_id = update.effective_user.id
    
    # Check if user is already authenticated
    if context.user_data.get('authenticated'):
        await show_main_menu(update, context)
        return
    
    # Show password prompt
    await update.message.reply_text(
        "🔐 <b>ברוך הבא!</b>\n\n"
        "אנא הזן את הסיסמה כדי להמשיך:",
        parse_mode='HTML'
    )
    context.user_data['waiting_for_password'] = True

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle password input"""
    user_id = update.effective_user.id
    
    # If not waiting for password, ignore
    if not context.user_data.get('waiting_for_password'):
        return
    
    password = update.message.text.strip()
    
    if password == ADMIN_PASSWORD:
        context.user_data['authenticated'] = True
        context.user_data['waiting_for_password'] = False
        
        await update.message.reply_text(
            "✅ <b>ברוך הבא אדמין! 👋</b>\n\n"
            "אתה מחובר בהצלחה.",
            parse_mode='HTML'
        )
        
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ סיסמה שגויה. נסה שוב."
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu after authentication"""
    keyboard = [
        [InlineKeyboardButton("📊 תוצאות", callback_data='show_results')],
        [InlineKeyboardButton("⚙️ הגדרות", callback_data='settings')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            "<b>🏡 ברוך הבא אדמין</b>\n\n"
            "בחר פעולה:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        # If it's a callback query
        await update.callback_query.edit_message_text(
            "<b>🏡 ברוך הבא אדמין</b>\n\n"
            "בחר פעולה:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def check_authentication(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is authenticated"""
    if not context.user_data.get('authenticated'):
        await update.callback_query.answer("❌ אתה לא מחובר. בואו נתחיל מחדש עם /start", show_alert=True)
        return False
    return True
