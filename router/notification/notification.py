from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from database import get_db
from models import Notification, NotificationStatus, User
from utils.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get("/")
async def get_user_notifications(
    status: NotificationStatus | None = Query(
        None,
        description="Filter by notification status"
    ),
    notification_type: str | None = Query(
        None,
        description="Filter by notification type"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Base query
    query = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    # Optional status filter
    if status:
        query = query.where(Notification.status == status)

    # Optional type filter
    if notification_type:
        query = query.where(
            Notification.type == notification_type
        )

    result = await db.execute(query)

    notifications = result.scalars().all()

    # Unread count
    unread_result = await db.execute(
        select(func.count(Notification.id))
        .where(
            Notification.user_id == user.id,
            Notification.status == NotificationStatus.UNREAD
        )
    )

    unread_count = unread_result.scalar_one()

    return {
        "notifications": [
            {
                "id": notification.id,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "status": notification.status.value,
                "title": notification.title,
                "message": notification.message,
                "short_message": notification.short_message,
                "action_url": notification.action_url,
                "action_label": notification.action_label,
                "reference_id": notification.reference_id,
                "reference_type": notification.reference_type,
                "extra_data": notification.extra_data,
                "read_at": (
                    notification.read_at.isoformat()
                    if notification.read_at
                    else None
                ),
                "created_at": (
                    notification.created_at.isoformat()
                    if notification.created_at
                    else None
                ),
            }
            for notification in notifications
        ],
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
    )

    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    # Already read
    if notification.status == NotificationStatus.READ:
        return {
            "message": "Notification already marked as read",
            "notification": {
                "id": notification.id,
                "status": notification.status.value,
                "read_at": (
                    notification.read_at.isoformat()
                    if notification.read_at
                    else None
                ),
            }
        }

    notification.status = NotificationStatus.READ
    notification.read_at = datetime.utcnow()

    db.add(notification)

    await db.commit()
    await db.refresh(notification)

    return {
        "message": "Notification marked as read",
        "notification": {
            "id": notification.id,
            "status": notification.status.value,
            "read_at": (
                notification.read_at.isoformat()
                if notification.read_at
                else None
            ),
        }
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.status != NotificationStatus.ARCHIVED
        )
    )

    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    notification.status = NotificationStatus.ARCHIVED
    notification.archived_at = datetime.utcnow()

    db.add(notification)

    await db.commit()

    return {
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }


@router.patch("/read-all")
async def mark_all_notifications_as_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.status == NotificationStatus.UNREAD
        )
    )

    notifications = result.scalars().all()

    now = datetime.utcnow()

    for notification in notifications:
        notification.status = NotificationStatus.READ
        notification.read_at = now

    await db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": len(notifications)
    }
