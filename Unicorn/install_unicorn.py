import os
import site
import shutil
import sys

def install_unicorn_api():
    # Use user site-packages instead of system site-packages
    user_site = site.getusersitepackages()
    print(f"Python user site-packages directory: {user_site}")
    
    # Create the directory if it doesn't exist
    os.makedirs(user_site, exist_ok=True)
    
    # Define source paths
    api_path = os.path.join(
        "Unicorn-Hybrid-Black-Windows-APIs-UnicornWindowsAPIs12400Beta2621 (1)",
        "Unicorn-Hybrid-Black-Windows-APIs-UnicornWindowsAPIs12400Beta2621",
        "python-api"
    )
    
    lib_path = os.path.join(api_path, "Lib")
    print(f"Looking for Unicorn API files in: {os.path.abspath(lib_path)}")
    
    # Check if lib_path exists
    if not os.path.exists(lib_path):
        print(f"Error: Directory {lib_path} does not exist")
        # Look for alternatives
        print("Searching for alternative paths...")
        base_dir = "Unicorn-Hybrid-Black-Windows-APIs-UnicornWindowsAPIs12400Beta2621 (1)"
        if os.path.exists(base_dir):
            print(f"Base directory {base_dir} exists")
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file in ["Unicorn.dll", "UnicornPy.pyd"]:
                        print(f"Found {file} in {root}")
        else:
            print(f"Base directory {base_dir} does not exist")
            
        return False
    
    # Files to copy
    unicorn_dll = os.path.join(lib_path, "Unicorn.dll")
    unicorn_pyd = os.path.join(lib_path, "UnicornPy.pyd")
    
    # Check if files exist
    if not os.path.exists(unicorn_dll):
        print(f"Error: {unicorn_dll} not found")
        return False
    
    if not os.path.exists(unicorn_pyd):
        print(f"Error: {unicorn_pyd} not found")
        return False
    
    print(f"Found Unicorn API files in {lib_path}")
    
    # Copy files to user site-packages
    try:
        # Copy UnicornPy.pyd to site-packages
        shutil.copy2(unicorn_pyd, user_site)
        print(f"Copied {unicorn_pyd} to {user_site}")
        
        # Create unicorn.py in site-packages
        unicorn_py_content = """# Python wrapper for Unicorn API
import os
import sys
import platform
import ctypes
from ctypes import *

# Load the shared library
try:
    if platform.system() == 'Windows':
        _path = os.path.dirname(__file__)
        _unicorn = ctypes.cdll.LoadLibrary(os.path.join(_path, "Unicorn.dll"))
    else:
        _unicorn = cdll.LoadLibrary("libunicorn.so")
except Exception as e:
    print(f"Error: could not load the Unicorn shared library. {str(e)}")
    sys.exit(1)

# Import the UnicornPy module
try:
    import UnicornPy
except ImportError as e:
    print(f"Error: could not import UnicornPy module. {str(e)}")
    sys.exit(1)
"""
        
        with open(os.path.join(user_site, "unicorn.py"), "w") as f:
            f.write(unicorn_py_content)
        print(f"Created unicorn.py in {user_site}")
        
        # Copy Unicorn.dll to site-packages
        shutil.copy2(unicorn_dll, user_site)
        print(f"Copied {unicorn_dll} to {user_site}")
        
        # Add the user site to sys.path if not already there
        if user_site not in sys.path:
            sys.path.append(user_site)
            print(f"Added {user_site} to Python path")
        
        print("\nUnicorn API installation completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during installation: {str(e)}")
        return False

if __name__ == "__main__":
    print("Installing Unicorn Python API...")
    success = install_unicorn_api()
    
    if success:
        print("\nVerifying installation...")
        # Make sure user site-packages is in the path
        if site.getusersitepackages() not in sys.path:
            sys.path.append(site.getusersitepackages())
        
        try:
            import unicorn
            print("unicorn module imported successfully!")
            import UnicornPy
            print("UnicornPy module imported successfully!")
            print("\nUnicorn API is now ready to use!")
        except ImportError as e:
            print(f"Verification failed: {str(e)}")
            print("\nYou may need to add the following to the top of your scripts:")
            print("import sys")
            print(f"sys.path.append('{site.getusersitepackages()}')")
    else:
        print("\nInstallation failed. Please check the error messages above.") 