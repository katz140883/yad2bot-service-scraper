"""
Basic scheduler module for Yad2bot
"""
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class BotScheduler:
    """Basic scheduler for Yad2bot"""
    
    def __init__(self, job_queue=None):
        self.scheduled_tasks = {}
        self.job_queue = job_queue
        logger.info("BotScheduler initialized")
    
    async def start(self):
        """Start the scheduler"""
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        logger.info("Scheduler stopped")
    
    def schedule_task(self, task_id: str, hour: int, minute: int, callback):
        """Schedule a task"""
        self.scheduled_tasks[task_id] = {
            'hour': hour,
            'minute': minute,
            'callback': callback
        }
        logger.info(f"Task {task_id} scheduled for {hour:02d}:{minute:02d}")
    
    def remove_task(self, task_id: str):
        """Remove a scheduled task"""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            logger.info(f"Task {task_id} removed")


    
    def load_schedules_from_database(self):
        """Load schedules from database"""
        logger.info("Loading schedules from database")
    
    def add_schedule(self, user_id: int, hour: int, minute: int, search_params: dict):
        """Add a new schedule"""
        schedule_id = f"{user_id}_{hour}_{minute}"
        self.scheduled_tasks[schedule_id] = {
            'user_id': user_id,
            'hour': hour,
            'minute': minute,
            'search_params': search_params
        }
        logger.info(f"Schedule added for user {user_id} at {hour:02d}:{minute:02d}")
    
    def remove_schedule(self, user_id: int):
        """Remove schedule for user"""
        to_remove = [k for k in self.scheduled_tasks.keys() if k.startswith(f"{user_id}_")]
        for key in to_remove:
            del self.scheduled_tasks[key]
        logger.info(f"Schedules removed for user {user_id}")
    
    def get_user_schedule(self, user_id: int):
        """Get schedule for user"""
        for key, schedule in self.scheduled_tasks.items():
            if schedule['user_id'] == user_id:
                return schedule
        return None

