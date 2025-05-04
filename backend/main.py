from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import os
from typing import Dict, Any

# Direct imports (no relative imports)
from models import MoveRequest, BCIStatusResponse
from chess_logic import ChessGame
from websocket_manager import ConnectionManager
from bci_manager import BCIManager

# Create application
app = FastAPI(title="Chess BCI Game")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create instances of our manager classes
manager = ConnectionManager()
bci_manager = BCIManager()
game = ChessGame()

# Ensure the static directory exists
os.makedirs("static", exist_ok=True)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes
@app.get("/")
async def get_index():
    """Serve the main frontend page"""
    # Serve our wrapper that will load the original index.html via JavaScript
    return FileResponse("static/wrapper.html")

@app.get("/original")
async def get_original_index():
    """Serve the original index.html for debugging"""
    return FileResponse("static/index.html")

@app.get("/game_state")
async def get_game_state():
    """Get the current game state"""
    return game.get_state()

@app.get("/valid_moves")
async def get_valid_moves(row: int, col: int):
    """Get valid moves for a piece at the specified position"""
    return {"moves": game.get_valid_moves(row, col)}

@app.post("/move")
async def make_move(move: MoveRequest):
    """Make a move on the board"""
    success, message = game.make_move(
        move.from_row, 
        move.from_col, 
        move.to_row, 
        move.to_col, 
        move.promotion
    )
    
    if success:
        # Broadcast the updated game state to all connected clients
        await manager.broadcast({
            "type": "game_state",
            "state": game.get_state()
        })
        
        return {"success": True}
    else:
        return {"success": False, "message": message}

@app.post("/new_game")
async def new_game():
    """Start a new game"""
    global game
    game = ChessGame()
    
    # Broadcast the new game state to all connected clients
    await manager.broadcast({
        "type": "game_state",
        "state": game.get_state()
    })
    
    return {"success": True}

@app.post("/bci/connect")
async def connect_bci():
    """Connect to the BCI device"""
    success = bci_manager.connect()
    if success:
        # Start BCI monitoring in background
        asyncio.create_task(bci_monitoring())
    return {"success": success}

@app.post("/bci/disconnect")
async def disconnect_bci():
    """Disconnect from the BCI device"""
    success = bci_manager.disconnect()
    return {"success": success}

@app.get("/bci/status")
async def get_bci_status() -> BCIStatusResponse:
    """Get the current status of the BCI connection"""
    return BCIStatusResponse(
        connected=bci_manager.connected,
        bandpowers=bci_manager.get_bandpowers() if bci_manager.connected else None,
        focus_level=bci_manager.get_focus_level() if bci_manager.connected else None
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for game state updates"""
    await manager.connect(websocket)
    try:
        # Send the current game state when a client connects
        await websocket.send_text(json.dumps({
            "type": "game_state",
            "state": game.get_state()
        }))
        
        while True:
            # Keep the connection open to receive broadcasts
            # All game logic is handled through REST endpoints
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/bci_ws")
async def bci_websocket(websocket: WebSocket):
    """WebSocket endpoint for BCI data streaming"""
    await manager.connect(websocket)
    try:
        while bci_manager.connected:
            # Send BCI data to the client
            bandpowers = bci_manager.get_bandpowers()
            focus_level = bci_manager.get_focus_level()
            
            await websocket.send_text(json.dumps({
                "type": "bci_data",
                "data": {
                    "bandpowers": bandpowers,
                    "focus_level": focus_level,
                    "is_focused": bci_manager.is_focused(),
                    "is_selecting": bci_manager.is_making_selection()
                }
            }))
            
            await asyncio.sleep(0.2)  # 5 updates per second
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def bci_monitoring():
    """Background task to monitor BCI signals"""
    if not bci_manager.connected:
        return
    
    async def bci_callback(data: Dict[str, Any]):
        """Callback for BCI data updates"""
        # Broadcast BCI data to all connected clients
        await manager.broadcast({
            "type": "bci_data",
            "data": data
        })
    
    await bci_manager.continuous_monitoring(bci_callback)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on server startup"""
    print("Chess BCI Server is starting up...")
    
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on server shutdown"""
    print("Chess BCI Server is shutting down...")
    if bci_manager.connected:
        bci_manager.disconnect()

# Run the application directly if this file is executed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)