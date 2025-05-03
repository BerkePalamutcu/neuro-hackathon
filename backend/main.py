from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Tuple
import json
from enum import Enum

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

# Game state
class ChessGame:
    def __init__(self):
        self.board = self.init_board()
        self.current_player = "white"
        self.castling_rights = {
            "white": {"king_side": True, "queen_side": True},
            "black": {"king_side": True, "queen_side": True}
        }
        self.en_passant_target = None
        self.half_move_clock = 0
        self.full_move_number = 1
        self.check = False
        self.checkmate = False
        self.stalemate = False
        self.king_positions = {
            "white": (0, 4),
            "black": (7, 4)
        }
        self.move_history = []

    def init_board(self):
        # Initialize an 8x8 chess board
        board = [[None for _ in range(8)] for _ in range(8)]
        
        # Set up pawns
        for col in range(8):
            board[1][col] = {"type": "pawn", "color": "white", "has_moved": False}
            board[6][col] = {"type": "pawn", "color": "black", "has_moved": False}
        
        # Set up rooks
        board[0][0] = {"type": "rook", "color": "white", "has_moved": False}
        board[0][7] = {"type": "rook", "color": "white", "has_moved": False}
        board[7][0] = {"type": "rook", "color": "black", "has_moved": False}
        board[7][7] = {"type": "rook", "color": "black", "has_moved": False}
        
        # Set up knights
        board[0][1] = {"type": "knight", "color": "white"}
        board[0][6] = {"type": "knight", "color": "white"}
        board[7][1] = {"type": "knight", "color": "black"}
        board[7][6] = {"type": "knight", "color": "black"}
        
        # Set up bishops
        board[0][2] = {"type": "bishop", "color": "white"}
        board[0][5] = {"type": "bishop", "color": "white"}
        board[7][2] = {"type": "bishop", "color": "black"}
        board[7][5] = {"type": "bishop", "color": "black"}
        
        # Set up queens
        board[0][3] = {"type": "queen", "color": "white"}
        board[7][3] = {"type": "queen", "color": "black"}
        
        # Set up kings
        board[0][4] = {"type": "king", "color": "white", "has_moved": False}
        board[7][4] = {"type": "king", "color": "black", "has_moved": False}
        
        return board

    def get_state(self):
        return {
            "board": self.board,
            "currentPlayer": self.current_player,
            "castlingRights": self.castling_rights,
            "check": self.check,
            "checkmate": self.checkmate,
            "stalemate": self.stalemate
        }
    
    def is_in_bounds(self, row, col):
        return 0 <= row < 8 and 0 <= col < 8
    
    def get_piece(self, row, col):
        if not self.is_in_bounds(row, col):
            return None
        return self.board[row][col]
    
    def get_valid_moves(self, row, col):
        piece = self.get_piece(row, col)
        if piece is None or piece["color"] != self.current_player:
            return []
        
        moves = []
        
        if piece["type"] == "pawn":
            moves.extend(self.get_pawn_moves(row, col, piece))
        elif piece["type"] == "rook":
            moves.extend(self.get_rook_moves(row, col, piece))
        elif piece["type"] == "knight":
            moves.extend(self.get_knight_moves(row, col, piece))
        elif piece["type"] == "bishop":
            moves.extend(self.get_bishop_moves(row, col, piece))
        elif piece["type"] == "queen":
            moves.extend(self.get_queen_moves(row, col, piece))
        elif piece["type"] == "king":
            moves.extend(self.get_king_moves(row, col, piece))
        
        # Filter out moves that would put or leave the king in check
        legal_moves = []
        for move in moves:
            if not self.would_be_in_check(row, col, move["row"], move["col"]):
                legal_moves.append(move)
        
        return legal_moves
    
    def get_pawn_moves(self, row, col, piece):
        moves = []
        direction = 1 if piece["color"] == "white" else -1
        
        # Forward move
        new_row = row + direction
        if self.is_in_bounds(new_row, col) and self.board[new_row][col] is None:
            moves.append({"row": new_row, "col": col})
            
            # Double move from starting position
            if ((piece["color"] == "white" and row == 1) or 
                (piece["color"] == "black" and row == 6)) and self.board[new_row + direction][col] is None:
                moves.append({"row": new_row + direction, "col": col})
        
        # Captures
        for offset in [-1, 1]:
            new_col = col + offset
            if self.is_in_bounds(new_row, new_col):
                target = self.board[new_row][new_col]
                if target is not None and target["color"] != piece["color"]:
                    moves.append({"row": new_row, "col": new_col})
                
                # En passant
                if self.en_passant_target == (new_row, new_col):
                    moves.append({"row": new_row, "col": new_col, "en_passant": True})
        
        return moves
    
    def get_rook_moves(self, row, col, piece):
        return self.get_sliding_moves(row, col, piece, [(0, 1), (1, 0), (0, -1), (-1, 0)])
    
    def get_bishop_moves(self, row, col, piece):
        return self.get_sliding_moves(row, col, piece, [(1, 1), (1, -1), (-1, -1), (-1, 1)])
    
    def get_queen_moves(self, row, col, piece):
        return self.get_sliding_moves(row, col, piece, [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, -1), (-1, 1)])
    
    def get_sliding_moves(self, row, col, piece, directions):
        moves = []
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + i * dr, col + i * dc
                
                if not self.is_in_bounds(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if target is None:
                    moves.append({"row": new_row, "col": new_col})
                elif target["color"] != piece["color"]:
                    moves.append({"row": new_row, "col": new_col})
                    break
                else:
                    break
        
        return moves
    
    def get_knight_moves(self, row, col, piece):
        moves = []
        offsets = [(2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1)]
        
        for dr, dc in offsets:
            new_row, new_col = row + dr, col + dc
            
            if not self.is_in_bounds(new_row, new_col):
                continue
            
            target = self.board[new_row][new_col]
            if target is None or target["color"] != piece["color"]:
                moves.append({"row": new_row, "col": new_col})
        
        return moves
    
    def get_king_moves(self, row, col, piece):
        moves = []
        offsets = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
        
        for dr, dc in offsets:
            new_row, new_col = row + dr, col + dc
            
            if not self.is_in_bounds(new_row, new_col):
                continue
            
            target = self.board[new_row][new_col]
            if target is None or target["color"] != piece["color"]:
                moves.append({"row": new_row, "col": new_col})
        
        # Castling
        if not piece.get("has_moved", True) and not self.check:
            side = piece["color"]
            
            # Kingside castling
            if self.castling_rights[side]["king_side"]:
                if (self.board[row][col + 1] is None and 
                    self.board[row][col + 2] is None and 
                    self.board[row][col + 3] is not None and 
                    self.board[row][col + 3]["type"] == "rook" and 
                    not self.board[row][col + 3].get("has_moved", True)):
                    
                    # Check if the king passes through check
                    if (not self.is_square_attacked(row, col, self.opposite_color(side)) and 
                        not self.is_square_attacked(row, col + 1, self.opposite_color(side)) and 
                        not self.is_square_attacked(row, col + 2, self.opposite_color(side))):
                        
                        moves.append({"row": row, "col": col + 2, "castling": "king_side"})
            
            # Queenside castling
            if self.castling_rights[side]["queen_side"]:
                if (self.board[row][col - 1] is None and 
                    self.board[row][col - 2] is None and 
                    self.board[row][col - 3] is None and 
                    self.board[row][col - 4] is not None and 
                    self.board[row][col - 4]["type"] == "rook" and 
                    not self.board[row][col - 4].get("has_moved", True)):
                    
                    # Check if the king passes through check
                    if (not self.is_square_attacked(row, col, self.opposite_color(side)) and 
                        not self.is_square_attacked(row, col - 1, self.opposite_color(side)) and 
                        not self.is_square_attacked(row, col - 2, self.opposite_color(side))):
                        
                        moves.append({"row": row, "col": col - 2, "castling": "queen_side"})
        
        return moves
    
    def opposite_color(self, color):
        return "black" if color == "white" else "white"
    
    def is_square_attacked(self, row, col, by_color):
        # Check if a square is attacked by any piece of the given color
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is not None and piece["color"] == by_color:
                    # For efficiency, we can check based on piece type
                    if piece["type"] == "pawn":
                        direction = -1 if by_color == "white" else 1
                        if ((r + direction) == row and (c - 1 == col or c + 1 == col)):
                            return True
                    else:
                        # For other pieces, check if the move is valid
                        # We can reuse our move generation functions
                        if piece["type"] == "knight":
                            moves = self.get_knight_moves(r, c, piece)
                        elif piece["type"] == "bishop":
                            moves = self.get_bishop_moves(r, c, piece)
                        elif piece["type"] == "rook":
                            moves = self.get_rook_moves(r, c, piece)
                        elif piece["type"] == "queen":
                            moves = self.get_queen_moves(r, c, piece)
                        elif piece["type"] == "king":
                            moves = [(r + dr, c + dc) for dr, dc in [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
                                    if 0 <= r + dr < 8 and 0 <= c + dc < 8]
                            moves = [{"row": r, "col": c} for r, c in moves]
                        else:
                            continue
                        
                        for move in moves:
                            if move["row"] == row and move["col"] == col:
                                return True
        
        return False
    
    def would_be_in_check(self, from_row, from_col, to_row, to_col):
        # Make a temporary move and check if the king would be in check
        piece = self.board[from_row][from_col]
        target = self.board[to_row][to_col]
        
        # Temporarily make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        
        # Get king position
        king_row, king_col = self.king_positions[piece["color"]]
        if piece["type"] == "king":
            king_row, king_col = to_row, to_col
        
        # Check if the king is attacked
        in_check = self.is_square_attacked(king_row, king_col, self.opposite_color(piece["color"]))
        
        # Undo the move
        self.board[from_row][from_col] = piece
        self.board[to_row][to_col] = target
        
        return in_check
    
    def make_move(self, from_row, from_col, to_row, to_col, promotion=None):
        piece = self.board[from_row][from_col]
        if piece is None or piece["color"] != self.current_player:
            return False, "No piece at the from position or not your turn"
        
        # Get valid moves for the piece
        valid_moves = self.get_valid_moves(from_row, from_col)
        
        # Check if the move is valid
        move = next((m for m in valid_moves if m["row"] == to_row and m["col"] == to_col), None)
        if move is None:
            return False, "Invalid move"
        
        # Handle castling
        castling = move.get("castling")
        if castling:
            rook_col = from_col + 3 if castling == "king_side" else from_col - 4
            new_rook_col = from_col + 1 if castling == "king_side" else from_col - 1
            
            # Move the rook
            self.board[to_row][new_rook_col] = self.board[to_row][rook_col]
            self.board[to_row][rook_col] = None
            self.board[to_row][new_rook_col]["has_moved"] = True
        
        # Handle en passant capture
        if move.get("en_passant"):
            capture_row = from_row
            capture_col = to_col
            self.board[capture_row][capture_col] = None
        
        # Move the piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        
        # Update has_moved for kings and rooks
        if piece["type"] in ["king", "rook", "pawn"]:
            piece["has_moved"] = True
        
        # Handle pawn promotion
        if piece["type"] == "pawn" and (to_row == 7 and piece["color"] == "white" or to_row == 0 and piece["color"] == "black"):
            if promotion not in ["queen", "rook", "bishop", "knight"]:
                promotion = "queen"  # Default promotion
            
            piece["type"] = promotion
        
        # Update king position if it was moved
        if piece["type"] == "king":
            self.king_positions[piece["color"]] = (to_row, to_col)
        
        # Update castling rights
        if piece["type"] == "king":
            self.castling_rights[piece["color"]]["king_side"] = False
            self.castling_rights[piece["color"]]["queen_side"] = False
        
        if piece["type"] == "rook":
            if from_col == 0:  # Queenside rook
                self.castling_rights[piece["color"]]["queen_side"] = False
            elif from_col == 7:  # Kingside rook
                self.castling_rights[piece["color"]]["king_side"] = False
        
        # Set en passant target
        if piece["type"] == "pawn" and abs(to_row - from_row) == 2:
            self.en_passant_target = (from_row + (1 if piece["color"] == "white" else -1), from_col)
        else:
            self.en_passant_target = None
        
        # Update move counters
        if piece["type"] == "pawn" or self.board[to_row][to_col] is not None:
            self.half_move_clock = 0
        else:
            self.half_move_clock += 1
        
        if piece["color"] == "black":
            self.full_move_number += 1
        
        # Record the move
        self.move_history.append({
            "from": (from_row, from_col),
            "to": (to_row, to_col),
            "piece": piece,
            "promotion": promotion,
            "castling": castling,
            "en_passant": move.get("en_passant"),
            "capture": self.board[to_row][to_col] is not None
        })
        
        # Switch player
        self.current_player = self.opposite_color(self.current_player)
        
        # Check for check, checkmate, or stalemate
        self.update_game_status()
        
        return True, "Move successful"
    
    def update_game_status(self):
        king_row, king_col = self.king_positions[self.current_player]
        
        # Check if the current player's king is in check
        self.check = self.is_square_attacked(king_row, king_col, self.opposite_color(self.current_player))
        
        # Check if the current player has any legal moves
        has_legal_moves = False
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece is not None and piece["color"] == self.current_player:
                    if self.get_valid_moves(row, col):
                        has_legal_moves = True
                        break
            if has_legal_moves:
                break
        
        # If no legal moves, it's either checkmate or stalemate
        if not has_legal_moves:
            if self.check:
                self.checkmate = True
            else:
                self.stalemate = True

game = ChessGame()

# API Models
class MoveRequest(BaseModel):
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    promotion: Optional[str] = None

# Routes
@app.get("/game_state")
async def get_game_state():
    return game.get_state()

@app.get("/valid_moves")
async def get_valid_moves(row: int, col: int):
    return {"moves": game.get_valid_moves(row, col)}

@app.post("/move")
async def make_move(move: MoveRequest):
    success, message = game.make_move(move.from_row, move.from_col, move.to_row, move.to_col, move.promotion)
    
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
    global game
    game = ChessGame()
    
    # Broadcast the new game state to all connected clients
    await manager.broadcast({
        "type": "game_state",
        "state": game.get_state()
    })
    
    return {"success": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send the current game state when a client connects
        await websocket.send_text(json.dumps({
            "type": "game_state",
            "state": game.get_state()
        }))
        
        while True:
            # We're just keeping the connection open to receive broadcasts
            # All game logic is handled through REST endpoints
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
