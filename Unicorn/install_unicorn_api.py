import os
import sys
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

def main():
    print("=== Unicorn API Installation Helper ===")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    # Print Python path
    print("\nPython is looking for modules in these locations:")
    for path in sys.path:
        print(f"  - {path}")
    
    # Check if unicorn module is already available
    try:
        import unicorn
        print("\nUnicorn module is already installed at:")
        print(f"  {unicorn.__file__}")
        print(f"Version: {getattr(unicorn, '__version__', 'Unknown')}")
        
        # Ask if user wants to continue anyway
        print("\nDo you want to continue with installation anyway? (y/n)")
        if input().lower() != 'y':
            print("Exiting...")
            return
    except ImportError as e:
        print(f"\nUnicorn module not found: {e}")
    
    # Ask user for the source code location
    print("\nOptions to install Unicorn API:")
    print("1. Extract from installer (if you have the MSI)")
    print("2. Download from GitHub")
    print("3. Specify a local folder with the API")
    
    choice = input("Choose an option (1-3): ")
    
    if choice == '1':
        install_from_msi()
    elif choice == '2':
        install_from_github()
    elif choice == '3':
        folder = input("Enter the path to the folder containing the Unicorn Python API: ")
        install_from_folder(folder)
    else:
        print("Invalid choice. Exiting...")
        return
    
    # Verify installation
    print("\nVerifying installation...")
    try:
        import unicorn
        print("SUCCESS! Unicorn module is now installed at:")
        print(f"  {unicorn.__file__}")
        print(f"Version: {getattr(unicorn, '__version__', 'Unknown')}")
    except ImportError as e:
        print(f"ERROR: Installation failed. Unicorn module still not found: {e}")
        print("You may need to manually install the API.")

def install_from_msi():
    print("\nInstalling from MSI...")
    
    # Ask for MSI location
    msi_path = input("Enter the path to the UnicornHybridBlackAPIs_x64.msi file: ")
    
    if not os.path.exists(msi_path):
        print(f"Error: File {msi_path} not found")
        return
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Extracting MSI to {temp_dir}...")
        
        # Extract MSI using msiexec
        cmd = f'msiexec /a "{msi_path}" /qb TARGETDIR="{temp_dir}"'
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError:
            print("Error: Failed to extract MSI")
            return
        
        # Look for Python API in the extracted files
        python_api_path = find_python_api(temp_dir)
        
        if python_api_path:
            print(f"Found Python API at: {python_api_path}")
            # Install the API
            install_from_folder(python_api_path)
        else:
            print("Error: Python API not found in the extracted MSI")

def install_from_github():
    print("\nInstalling from GitHub...")
    
    # Import required modules
    try:
        import requests
        from io import BytesIO
        import zipfile
    except ImportError:
        print("Error: Required modules not found. Please install them with:")
        print("pip install requests")
        return
    
    # GitHub repository URL
    repo_url = "https://github.com/unicorn-bi/Unicorn-Hybrid-Black-Windows-APIs"
    zip_url = f"{repo_url}/archive/refs/heads/main.zip"
    
    print(f"Downloading from {zip_url}...")
    
    try:
        # Download the repository
        response = requests.get(zip_url)
        response.raise_for_status()
        
        # Extract the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                zip_file.extractall(temp_dir)
            
            # Find the Python API
            extracted_folder = os.path.join(temp_dir, "Unicorn-Hybrid-Black-Windows-APIs-main")
            python_api_path = os.path.join(extracted_folder, "python-api")
            
            if os.path.exists(python_api_path):
                print(f"Found Python API at: {python_api_path}")
                # Install the API
                install_from_folder(python_api_path)
            else:
                print("Error: Python API not found in the GitHub repository")
    except Exception as e:
        print(f"Error: Failed to download or extract the GitHub repository: {e}")

def install_from_folder(folder_path):
    print(f"\nInstalling from folder: {folder_path}")
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} not found")
        return
    
    # Check if there's a setup.py file
    setup_py = os.path.join(folder_path, "setup.py")
    if os.path.exists(setup_py):
        print("Found setup.py, installing with pip...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", folder_path], check=True)
            print("Installation completed successfully!")
            return
        except subprocess.CalledProcessError:
            print("Error: Failed to install with pip")
    
    # Check for wheel files
    wheel_files = list(Path(folder_path).glob("*.whl"))
    if wheel_files:
        print(f"Found wheel file: {wheel_files[0]}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", str(wheel_files[0])], check=True)
            print("Installation completed successfully!")
            return
        except subprocess.CalledProcessError:
            print("Error: Failed to install wheel file")
    
    # Check for Python module files
    py_files = list(Path(folder_path).glob("*.py"))
    pyd_files = list(Path(folder_path).glob("_unicorn.pyd"))
    
    if py_files or pyd_files:
        print("Found Python files, installing manually...")
        
        # Determine the site-packages directory
        site_packages = None
        for path in sys.path:
            if "site-packages" in path:
                site_packages = path
                break
        
        if not site_packages:
            print("Error: Could not find site-packages directory")
            return
        
        # Create unicorn directory in site-packages
        unicorn_dir = os.path.join(site_packages, "unicorn")
        os.makedirs(unicorn_dir, exist_ok=True)
        
        # Copy Python files
        for file in py_files + pyd_files:
            shutil.copy(file, unicorn_dir)
        
        # Create __init__.py if it doesn't exist
        init_py = os.path.join(unicorn_dir, "__init__.py")
        if not os.path.exists(init_py):
            with open(init_py, "w") as f:
                f.write("# Unicorn Python API\n")
        
        print(f"Files copied to {unicorn_dir}")
        print("Installation completed manually!")
    else:
        print("Error: No Python files found in the folder")

def find_python_api(root_dir):
    """Find the Python API directory in the extracted MSI."""
    for root, dirs, files in os.walk(root_dir):
        # Look for typical Python API files
        if any(f == "unicorn.py" for f in files) or any(f == "_unicorn.pyd" for f in files):
            return root
        
        # Look for a directory with "python" in the name
        for dir_name in dirs:
            if "python" in dir_name.lower():
                python_dir = os.path.join(root, dir_name)
                if os.path.exists(python_dir):
                    return python_dir
    
    return None

if __name__ == "__main__":
    main() 