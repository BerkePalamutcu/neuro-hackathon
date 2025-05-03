from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class MoveRequest(BaseModel):
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    promotion: Optional[str] = None

class BCIStatusResponse(BaseModel):
    connected: bool
    bandpowers: Optional[Dict[str, float]] = None
    focus_level: Optional[float] = None

class ValidMovesResponse(BaseModel):
    moves: List[Dict[str, Any]]

class MoveResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class GameStateResponse(BaseModel):
    board: List[List[Optional[Dict[str, Any]]]]
    currentPlayer: str
    castlingRights: Dict[str, Dict[str, bool]]
    check: bool
    checkmate: bool
    stalemate: bool