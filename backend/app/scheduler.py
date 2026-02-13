"""
Background scheduler for due-date reminder notifications.

Uses APScheduler to run a periodic job every 30 minutes that checks for
tasks with due dates within the next 12 hours and creates in-app notifications.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import select

from app.database import async_session_maker
from app.models import Todo, Notification

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_due_date_reminders():
    """Find tasks due within 12 hours and create notifications for them."""
    now = datetime.utcnow()
    reminder_window = now + timedelta(hours=12)

    async with async_session_maker() as session:
        try:
            # Find pending tasks with due dates within 12 hours that haven't been notified
            query = select(Todo).where(
                Todo.due_date.isnot(None),
                Todo.due_date <= reminder_window,
                Todo.due_date > now,
                Todo.status == "pending",
                Todo.notified == False,  # noqa: E712
            )
            result = await session.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                return

            logger.info(f"Found {len(tasks)} tasks due within 12 hours")

            for task in tasks:
                # Calculate hours remaining
                time_remaining = task.due_date - now
                hours_left = time_remaining.total_seconds() / 3600

                if hours_left < 1:
                    time_str = f"{int(time_remaining.total_seconds() / 60)} minutes"
                else:
                    time_str = f"{hours_left:.1f} hours"

                message = (
                    f"Reminder: '{task.title}' is due in {time_str} "
                    f"(due: {task.due_date.strftime('%Y-%m-%d %H:%M')})"
                )

                notification = Notification(
                    user_id=task.user_id,
                    task_id=task.id,
                    message=message,
                )
                session.add(notification)

                # Mark as notified so we don't create duplicate reminders
                task.notified = True

            await session.commit()
            logger.info(f"Created {len(tasks)} reminder notification(s)")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error checking due date reminders: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_due_date_reminders,
        "interval",
        minutes=30,
        id="due_date_reminders",
        replace_existing=True,
    )
    # Also run immediately on startup
    scheduler.add_job(
        check_due_date_reminders,
        "date",
        run_date=datetime.utcnow(),
        id="due_date_reminders_startup",
    )
    scheduler.start()
    logger.info("Background scheduler started (checking due dates every 30 min)")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
