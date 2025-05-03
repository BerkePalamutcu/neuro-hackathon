"""
This script sets up the required directory structure and starts the server.
"""
import os
import shutil
import subprocess
import sys

def setup_project():
    """Set up the project directory structure"""
    print("Setting up the Chess BCI project...")
    
    # Create directories
    os.makedirs("static", exist_ok=True)
    
    # Check if Python modules exist in the correct location
    required_files = [
        "main.py", 
        "chess_logic.py", 
        "bci_manager.py", 
        "websocket_manager.py", 
        "models.py"
    ]
    
    # Move the frontend file if needed
    if os.path.exists("frontend/index.html"):
        print("Moving index.html from frontend/ to static/")
        shutil.copy("frontend/index.html", "static/index.html")
    elif os.path.exists("index.html"):
        print("Moving index.html to static/")
        shutil.copy("index.html", "static/index.html")
    
    # Check if files in backend directory should be moved
    if not os.path.exists("chess_logic.py") and os.path.exists("backend/chess_logic.py"):
        print("Moving Python modules from backend/ to root")
        for file in required_files:
            if os.path.exists(f"backend/{file}"):
                shutil.copy(f"backend/{file}", file)
    
    # Check if there are any missing files still
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"Missing required files: {', '.join(missing_files)}")
        print("Please make sure all required files are in the project root directory.")
        return False
    
    # Check if index.html exists in static directory
    if not os.path.exists("static/index.html"):
        print("ERROR: index.html is missing from the static directory.")
        print("Please place your HTML file in the static directory as static/index.html")
        return False
    
    print("All required files found!")
    return True

def run_server():
    """Run the FastAPI server using uvicorn"""
    print("Starting the server...")
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    if setup_project():
        run_server()
    else:
        print("Setup failed. Cannot start the server.")