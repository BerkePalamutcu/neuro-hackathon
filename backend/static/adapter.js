// Chess Backend Adapter
// This script acts as a compatibility layer between the new frontend and the existing backend

// Wait for the page to load before initializing our adapter
window.addEventListener('load', () => {
  console.log('Chess Backend Adapter loaded');
  
  // Intercept the original DOMContentLoaded event to ensure our adapter runs first
  const originalDOMContentLoaded = document.createEvent('Event');
  originalDOMContentLoaded.initEvent('chessDOMContentLoaded', true, true);
  
  // Replace the original chess game initialization with our adapter
  const originalInit = document.body.innerHTML;
  document.body.innerHTML = '';
  
  // Create adapter container
  const adapterContainer = document.createElement('div');
  adapterContainer.id = 'adapter-container';
  adapterContainer.style.width = '100%';
  adapterContainer.style.height = '100vh';
  adapterContainer.style.display = 'flex';
  adapterContainer.style.flexDirection = 'column';
  adapterContainer.style.alignItems = 'center';
  adapterContainer.style.justifyContent = 'center';
  document.body.appendChild(adapterContainer);
  
  // Add title
  const title = document.createElement('h1');
  title.textContent = 'Chess BCI Game';
  title.style.marginBottom = '20px';
  adapterContainer.appendChild(title);
  
  // Create API connection status
  const connectionStatus = document.createElement('div');
  connectionStatus.id = 'connection-status';
  connectionStatus.className = 'disconnected';
  connectionStatus.textContent = 'Connecting to server...';
  connectionStatus.style.position = 'fixed';
  connectionStatus.style.top = '10px';
  connectionStatus.style.right = '10px';
  connectionStatus.style.padding = '5px 10px';
  connectionStatus.style.borderRadius = '4px';
  connectionStatus.style.backgroundColor = '#f44336';
  connectionStatus.style.color = 'white';
  connectionStatus.style.fontSize = '14px';
  document.body.appendChild(connectionStatus);
  
  // Initialize WebSocket connection
  let socket = null;
  let gameState = null;
  
  function initWebSocket() {
    const WS_URL = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;
    socket = new WebSocket(`${WS_URL}/ws`);
    
    socket.onopen = () => {
      console.log('WebSocket connection established');
      connectionStatus.textContent = 'Connected';
      connectionStatus.style.backgroundColor = '#4CAF50';
      
      // Fetch initial game state
      fetchGameState();
    };
    
    socket.onclose = () => {
      console.log('WebSocket connection closed');
      connectionStatus.textContent = 'Disconnected';
      connectionStatus.style.backgroundColor = '#f44336';
      
      // Try to reconnect after a delay
      setTimeout(initWebSocket, 5000);
    };
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      
      if (data.type === 'game_state') {
        gameState = data.state;
        updateChessUI();
      }
    };
  }
  
  // Fetch game state from the server
  function fetchGameState() {
    fetch('/game_state')
      .then(response => response.json())
      .then(data => {
        gameState = data;
        updateChessUI();
      })
      .catch(error => {
        console.error('Error fetching game state:', error);
      });
  }
  
  // Update the chess UI based on the game state
  function updateChessUI() {
    if (!gameState) return;
    
    // Convert backend board format to frontend format
    const board = [];
    
    for (let row = 0; row < 8; row++) {
      const boardRow = [];
      for (let col = 0; col < 8; col++) {
        const piece = gameState.board[row][col];
        if (piece) {
          // Convert from backend piece format to frontend format
          const color = piece.color === 'white' ? 'w' : 'b';
          let type = '';
          
          switch (piece.type) {
            case 'pawn': type = 'P'; break;
            case 'rook': type = 'R'; break;
            case 'knight': type = 'N'; break;
            case 'bishop': type = 'B'; break;
            case 'queen': type = 'Q'; break;
            case 'king': type = 'K'; break;
          }
          
          boardRow.push(color + type);
        } else {
          boardRow.push('empty');
        }
      }
      board.push(boardRow);
    }
    
    // Update the board in the window context
    window.board = board;
    window.currentPlayer = gameState.currentPlayer === 'white' ? 'w' : 'b';
    
    // Trigger a board update in the frontend
    if (window.renderBoard) {
      window.renderBoard();
      window.updateTurnDisplay();
    }
  }
  
  // Override the getValidMoves function to use the backend API
  window.getValidMovesFromBackend = function(row, col) {
    return fetch(`/valid_moves?row=${row}&col=${col}`)
      .then(response => response.json())
      .then(data => {
        return data.moves;
      })
      .catch(error => {
        console.error('Error getting valid moves:', error);
        return [];
      });
  };
  
  // Override the movePiece function to use the backend API
  window.movePieceToBackend = function(fromRow, fromCol, toRow, toCol, promotion = null) {
    const moveData = {
      from_row: fromRow,
      from_col: fromCol,
      to_row: toRow,
      to_col: toCol,
      promotion: promotion
    };
    
    return fetch('/move', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(moveData)
    })
      .then(response => response.json())
      .then(data => {
        return data.success;
      })
      .catch(error => {
        console.error('Error making move:', error);
        return false;
      });
  };
  
  // Override the newGame function to use the backend API
  window.newGameBackend = function() {
    return fetch('/new_game', {
      method: 'POST'
    })
      .then(response => response.json())
      .then(data => {
        return data.success;
      })
      .catch(error => {
        console.error('Error starting new game:', error);
        return false;
      });
  };
  
  // Initialize the adapter
  initWebSocket();
  
  // Now load the original script
  const script = document.createElement('script');
  script.textContent = `
    // Monkey patch the original functions to use our backend
    document.addEventListener('DOMContentLoaded', () => {
      const originalGetValidMoves = window.getValidMoves;
      window.getValidMoves = function(row, col) {
        return window.getValidMovesFromBackend(row, col).then(moves => {
          window.validMoves = moves;
          return moves;
        });
      };
      
      const originalMovePiece = window.movePiece;
      window.movePiece = function(fromRow, fromCol, toRow, toCol, promotion = null) {
        window.movePieceToBackend(fromRow, fromCol, toRow, toCol, promotion).then(success => {
          if (success) {
            // The backend will update the game state via WebSocket
          }
        });
      };
      
      const originalNewGame = window.newGame;
      window.newGame = function() {
        window.newGameBackend().then(success => {
          if (success) {
            // The backend will update the game state via WebSocket
          }
        });
      };
    });
    
    ${originalInit}
  `;
  document.body.appendChild(script);
  
  // Dispatch the original DOMContentLoaded event
  document.dispatchEvent(originalDOMContentLoaded);
});
