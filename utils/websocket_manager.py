from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
   
    def __init__(self):

        # user_id -> websocket set
        self.user_channels: Dict[str, Set[WebSocket]] = defaultdict(set)

        # market -> websocket set
        self.market_channels: Set[WebSocket] = set()

    ####################################################
    #
    # USER CHANNELS
    #
    ####################################################

    async def connect_user(
        self,
        user_id: str,
        websocket: WebSocket,
    ):
        await websocket.accept()

        self.user_channels[user_id].add(websocket)

        print(
            f"✅ User connected: {user_id}"
        )

    def disconnect_user(
        self,
        user_id: str,
        websocket: WebSocket,
    ):

        if user_id not in self.user_channels:
            return

        self.user_channels[user_id].discard(websocket)

        if not self.user_channels[user_id]:
            del self.user_channels[user_id]

        print(
            f"❌ User disconnected: {user_id}"
        )

    async def send_to_user(
        self,
        user_id: str,
        payload: dict,
    ):

        if user_id not in self.user_channels:
            return

        dead_connections = []

        for ws in self.user_channels[user_id]:

            try:
                await ws.send_json(payload)

            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect_user(
                user_id,
                ws,
            )

    ####################################################
    #
    # MARKET CHANNELS
    #
    ####################################################

    async def connect_market(
        self,
        websocket: WebSocket,
    ):

        await websocket.accept()

        self.market_channels.add(websocket)

        print(
        f"📈 Market connected | "
        f"id={id(websocket)} | "
        f"client={websocket.client} | "
        f"total={len(self.market_channels)}"
    )

    def disconnect_market(
        self,
        websocket: WebSocket,
    ):


        self.market_channels.discard(websocket)

      
        print(
            f"📉 Left market"
        )



    async def broadcast_market(
        self,
        payload: dict,
    ):

        dead_connections = []

        for ws in self.market_channels:
            print(
            f"➡ Sending to "
            f"id={id(ws)} | "
            f"client={ws.client}"
        )


            try:
                await ws.send_json(payload)

                print("✅ Sent successfully", payload)

            except Exception as e:
                print(f"❌ Send failed: {e}")
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect_market(ws)


manager = ConnectionManager()