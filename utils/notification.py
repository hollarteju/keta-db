from sqlalchemy.ext.asyncio import AsyncSession
from models import Notification, NotificationType, NotificationPriority, NotificationStatus, Transaction


async def create_notification(
    db: AsyncSession,
    *,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    reference_id: str | None = None,
    reference_type: str | None = None,
    action_url: str | None = None,
    action_label: str | None = None,
    extra_data: dict | None = None,
):
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        priority=priority,
        status=NotificationStatus.UNREAD,
        title=title,
        message=message,
        short_message=message[:255],
        reference_id=reference_id,
        reference_type=reference_type,
        action_url=action_url,
        action_label=action_label,
        extra_data=extra_data,
    )

    db.add(notification)

    return notification