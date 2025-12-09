"""
New scheduler module for Yad2bot using APScheduler
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db

logger = logging.getLogger(__name__)

class BotScheduler:
    """Scheduler for Yad2bot using APScheduler"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper_manager = None
        self.bot_instance = None
        logger.info("BotScheduler initialized with APScheduler")
    
    def set_scraper_manager(self, scraper_manager):
        """Set scraper manager instance"""
        self.scraper_manager = scraper_manager
        logger.info("Scraper manager set in scheduler")
    
    def set_bot_instance(self, bot):
        """Set bot instance"""
        self.bot_instance = bot
        logger.info("Bot instance set in scheduler")
    
    async def start(self):
        """Start the scheduler and load schedules from database"""
        try:
            self.scheduler.start()
            logger.info("✅ Scheduler started")
            
            # Load existing schedules from database
            await self.load_schedules_from_database()
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    async def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def load_schedules_from_database(self):
        """Load all active schedules from database and add them to scheduler"""
        try:
            schedules = db.get_all_active_schedules()
            logger.info(f"Loading {len(schedules)} schedules from database")
            
            for schedule in schedules:
                user_id = schedule['user_id']
                mode = schedule['mode']
                filter_type = schedule['filter_type']
                city = schedule.get('city', '')
                hour = schedule['hour']
                minute = schedule.get('minute', 0)
                
                # Add job to scheduler
                job_id = f"scrape_{user_id}_{mode}_{filter_type}"
                
                # Create cron trigger for daily execution
                trigger = CronTrigger(hour=hour, minute=minute, timezone='Asia/Jerusalem')
                
                self.scheduler.add_job(
                    self._run_scheduled_scrape,
                    trigger=trigger,
                    id=job_id,
                    args=[user_id, mode, filter_type, city],
                    replace_existing=True
                )
                
                logger.info(f"✅ Loaded schedule: {job_id} at {hour:02d}:{minute:02d}")
                
        except Exception as e:
            logger.error(f"Error loading schedules from database: {e}")
    
    async def _run_scheduled_scrape(self, user_id: int, mode: str, filter_type: str, city: str):
        """Run scheduled scrape - called by APScheduler"""
        try:
            logger.info(f"🤖 Running scheduled scrape for user {user_id}: {mode} {filter_type} in {city}")
            
            if not self.scraper_manager or not self.bot_instance:
                logger.error("Scraper manager or bot instance not set!")
                return
            
            # Send notification to user
            try:
                mode_text = "השכרה" if mode == "rent" else "מכירה"
                filter_text = "מהיום בלבד" if filter_type == "today" else "כללי"
                
                await self.bot_instance.send_message(
                    chat_id=user_id,
                    text=f"🤖 **סריקה מתוזמנת מתחילה...**\n\n"
                         f"📍 עיר: {city}\n"
                         f"🏠 סוג: {mode_text}\n"
                         f"📊 טווח: {filter_text}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
            
            # TODO: Run actual scrape
            # This will be connected to scraper_manager in next phase
            logger.info(f"Scheduled scrape completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in scheduled scrape: {e}")
    
    async def add_schedule(self, user_id: int, mode: str, filter_type: str, city: str, hour: int, minute: int = 0):
        """Add a new schedule"""
        try:
            # Save to database
            success = db.add_schedule(user_id, 'scraper', mode, filter_type, hour, minute)
            
            if not success:
                logger.error(f"Failed to save schedule to database for user {user_id}")
                return False
            
            # Update city in database (add city column if needed)
            try:
                import sqlite3
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE schedules 
                        SET city = ?
                        WHERE user_id = ? AND is_active = 1
                    ''', (city, user_id))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not update city in schedule: {e}")
            
            # Add job to scheduler
            job_id = f"scrape_{user_id}_{mode}_{filter_type}"
            
            # Remove existing job if exists
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Create cron trigger for daily execution
            trigger = CronTrigger(hour=hour, minute=minute, timezone='Asia/Jerusalem')
            
            self.scheduler.add_job(
                self._run_scheduled_scrape,
                trigger=trigger,
                id=job_id,
                args=[user_id, mode, filter_type, city],
                replace_existing=True
            )
            
            logger.info(f"✅ Schedule added: {job_id} at {hour:02d}:{minute:02d}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            return False
    
    async def cancel_user_schedules(self, user_id: int):
        """Cancel all schedules for a user"""
        try:
            # Get user's schedules before canceling
            schedules = db.get_user_schedules(user_id)
            
            # Cancel in database
            success = db.cancel_user_schedules(user_id)
            
            if not success:
                return False
            
            # Remove jobs from scheduler
            for schedule in schedules:
                mode = schedule['mode']
                filter_type = schedule['filter_type']
                job_id = f"scrape_{user_id}_{mode}_{filter_type}"
                
                try:
                    self.scheduler.remove_job(job_id)
                    logger.info(f"✅ Removed job: {job_id}")
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error canceling schedules: {e}")
            return False
    
    def get_user_schedule_info(self, user_id: int) -> dict:
        """Get user's schedule information"""
        try:
            schedules = db.get_user_schedules(user_id)
            if schedules:
                return schedules[0]  # Return first active schedule
            return None
        except Exception as e:
            logger.error(f"Error getting user schedule: {e}")
            return None

# Global scheduler instance
scheduler = BotScheduler()
