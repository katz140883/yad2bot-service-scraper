#!/usr/bin/env python3
import os
import logging
import signal
import sys
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot_handlers import BotHandlers

load_dotenv('yad2bot.env')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_service_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set telegram to DEBUG level to see all errors
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('telegram.ext').setLevel(logging.DEBUG)

BOT_TOKEN = os.getenv('BOT_TOKEN')

handlers = None

async def start_command(update, context):
    await handlers.start_command(update, context)

async def handle_message(update, context):
    pass

def main():
    global handlers
    
    logger.info(f"Starting Scraper Service Bot")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    handlers = BotHandlers()
    handlers.bot = application.bot
    handlers.scraper_manager.set_bot_instance(application.bot)
    logger.info("✅ Bot instance set")
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handlers.button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Handlers registered")
    
    # Save PID
    with open('scraper_service_bot.pid', 'w') as f:
        f.write(str(os.getpid()))
    logger.info(f"PID file created")
    
    logger.info("🚀 Starting bot polling...")
    
    # Run the bot polling with error handling
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in bot polling: {e}", exc_info=True)
        # Try to restart
        logger.info("Attempting to restart bot...")
        import time
        time.sleep(5)
        os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == '__main__':
    main()
