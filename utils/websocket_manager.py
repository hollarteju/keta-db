from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
   
    def __init__(self):

        # user_id -> websocket set
        self.user_channels: Dict[str, Set[WebSocket]] = defaultdict(set)

        # market -> websocket set
        self.market_channels: Dict[str, Set[WebSocket]] = defaultdict(set)

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
        market: str,
        websocket: WebSocket,
    ):

        await websocket.accept()

        self.market_channels[market].add(websocket)

        print(
            f"📈 Connected to market {market}"
        )

    def disconnect_market(
        self,
        market: str,
        websocket: WebSocket,
    ):

        if market not in self.market_channels:
            return

        self.market_channels[market].discard(websocket)

        if not self.market_channels[market]:
            del self.market_channels[market]

        print(
            f"📉 Left market {market}"
        )

    async def broadcast_market(
        self,
        market: str,
        payload: dict,
    ):

        if market not in self.market_channels:
            return

        dead_connections = []

        for ws in self.market_channels[market]:

            try:
                await ws.send_json(payload)

            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect_market(
                market,
                ws,
            )


manager = ConnectionManager()