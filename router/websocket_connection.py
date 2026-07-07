from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from utils.websocket_manager import manager

router = APIRouter( 
    prefix="/api/v1",
    tags=["websocket"])


@router.websocket("/ws/user/{user_id}")
async def user_socket(
    websocket: WebSocket,
    user_id: str,
):
    await manager.connect_user(
        user_id=user_id,
        websocket=websocket,
    )

    

    try:
        while True:
            # Keep socket alive
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_user(
            user_id=user_id,
            websocket=websocket,
        )




@router.websocket("/ws/market")
async def market_socket(websocket: WebSocket):

    await manager.connect_market(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_market(websocket)