from fastapi import WebSocket
from typing import List, Dict, Any
import json

class ConnectionManager:
    """
    WebSocket connection manager for real-time communication.
    Handles both game state updates and BCI data streaming.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Send a message to all connected clients"""
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))
            
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client"""
        await websocket.send_text(json.dumps(message))