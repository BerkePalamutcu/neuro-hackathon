import tkinter as tk
from PIL import Image, ImageTk
import os
import threading
import time
import keyboard
import sys

# Print where Python is looking for modules
print("Python is looking for modules in these locations:")
for path in sys.path:
    print(f"  - {path}")

# Direction image filenames
direction_images = {
    1: "up.jpg",
    2: "down.jpg",
    3: "left.jpg",
    4: "right.jpg", 
    5: "up_left.jpg",
    6: "up_right.jpg",
    7: "down_left.jpg",
    8: "down_right.jpg"
}

# Direction names for display
direction_names = {
    1: "Up",
    2: "Down",
    3: "Left",
    4: "Right",
    5: "Up-Left",
    6: "Up-Right",
    7: "Down-Left",
    8: "Down-Right"
}

# Flash frequencies (flashes per second, as fractions for slower rates)
flash_frequencies = {
    1: 1.0,    # Up: 1 flash per second
    2: 0.5,    # Down: 1 flash per 2 seconds
    3: 0.33,   # Left: 1 flash per 3 seconds
    4: 0.25,   # Right: 1 flash per 4 seconds
    5: 0.2,    # Up-Left: 1 flash per 5 seconds
    6: 0.167,  # Up-Right: 1 flash per 6 seconds
    7: 0.143,  # Down-Left: 1 flash per 7 seconds
    8: 0.125,  # Down-Right: 1 flash per 8 seconds
}

class ImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Direction Image Viewer")
        
        # Set window dimensions
        self.window_width = 800
        self.window_height = 600
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        
        # Make it full screen if needed
        # self.root.attributes('-fullscreen', True)
        
        # Set up the frame
        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create label for displaying the image
        self.image_label = tk.Label(self.frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Create label for displaying the direction name
        self.direction_label = tk.Label(self.frame, text="Select a direction (1-8)", font=("Arial", 24))
        self.direction_label.pack(pady=20)
        
        # Create label for displaying the flash frequency
        self.frequency_label = tk.Label(self.frame, text="", font=("Arial", 16))
        self.frequency_label.pack(pady=5)
        
        # Current direction
        self.current_direction = None
        
        # Flash state
        self.flash_on = True
        self.flashing = False
        self.flash_thread = None
        
        # Storage for loaded images
        self.loaded_images = {}
        self.current_tk_image = None
        
        # Shared variable for communication with brain_control.py
        self.selected_direction_file = "selected_direction.txt"
        
        # Toggle button for flashing
        self.flash_button = tk.Button(self.frame, text="Start Flashing", command=self.toggle_flashing)
        self.flash_button.pack(pady=10)
        
        # Start monitoring thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_key_presses)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Start monitoring file changes
        self.file_monitor_thread = threading.Thread(target=self.monitor_file)
        self.file_monitor_thread.daemon = True
        self.file_monitor_thread.start()
        
        # Register cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)
    
    def load_image(self, direction_num):
        """Load and display an image for the given direction number."""
        try:
            if direction_num in direction_images:
                image_path = direction_images[direction_num]
                
                # Check if file exists
                if not os.path.exists(image_path):
                    self.direction_label.config(text=f"Error: Image file '{image_path}' not found")
                    # Display placeholder
                    self.image_label.config(bg="gray")
                    self.stop_flashing()
                    return
                
                # If we've already loaded this image, use the cached version
                if direction_num in self.loaded_images:
                    tk_image = self.loaded_images[direction_num]
                else:
                    # Load and resize image
                    image = Image.open(image_path)
                    
                    # Resize to fit window while maintaining aspect ratio
                    img_width, img_height = image.size
                    ratio = min(self.window_width / img_width, (self.window_height - 100) / img_height)
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Convert to Tkinter format
                    tk_image = ImageTk.PhotoImage(image)
                    self.loaded_images[direction_num] = tk_image
                
                # Update the label
                self.image_label.config(image=tk_image)
                self.current_tk_image = tk_image
                
                # Update direction label
                self.direction_label.config(text=f"Direction {direction_num}: {direction_names[direction_num]}")
                
                # Format the frequency display in a more readable way
                rate = flash_frequencies[direction_num]
                if rate == 1.0:
                    rate_text = "1 flash per second"
                else:
                    seconds = int(round(1.0 / rate))
                    rate_text = f"1 flash per {seconds} seconds"
                self.frequency_label.config(text=rate_text)
                
                # Update current direction and restart flashing if it was active
                was_flashing = self.flashing
                self.stop_flashing()
                self.current_direction = direction_num
                if was_flashing:
                    self.start_flashing()
            else:
                self.direction_label.config(text="Invalid direction number")
                self.stop_flashing()
        except Exception as e:
            self.direction_label.config(text=f"Error loading image: {str(e)}")
            self.stop_flashing()
    
    def toggle_flashing(self):
        """Toggle the flashing animation."""
        if self.flashing:
            self.stop_flashing()
            self.flash_button.config(text="Start Flashing")
        else:
            self.start_flashing()
    
    def start_flashing(self):
        """Start the flashing animation."""
        if self.current_direction is None:
            return
            
        if not self.flashing:
            self.flashing = True
            self.flash_on = True
            self.flash_thread = threading.Thread(target=self.flash_animation)
            self.flash_thread.daemon = True
            self.flash_thread.start()
    
    def stop_flashing(self):
        """Stop the flashing animation."""
        self.flashing = False
        if self.flash_thread:
            self.flash_thread = None
        
        # Ensure image is visible
        if self.current_direction and self.current_direction in self.loaded_images:
            self.image_label.config(image=self.loaded_images[self.current_direction])
    
    def flash_animation(self):
        """Flash the image by toggling visibility at slow rates, from 1/sec to 1/8sec."""
        if self.current_direction is None:
            return
            
        # Get flashes per second for this direction
        flashes_per_second = flash_frequencies[self.current_direction]
        
        # Calculate total cycle time (on + off)
        cycle_duration = 1.0 / flashes_per_second
        half_cycle = cycle_duration / 2  # Time for "on" and for "off" states
        
        # Track timing
        last_toggle_time = time.time()
        
        while self.flashing and self.running:
            current_time = time.time()
            elapsed = current_time - last_toggle_time
            
            # Check if it's time to toggle the image
            if elapsed >= half_cycle:
                # Toggle the image state
                if self.flash_on:
                    # Show image
                    self.root.after(0, lambda: self.image_label.config(image=self.current_tk_image))
                else:
                    # Hide image (show blank)
                    self.root.after(0, lambda: self.image_label.config(image=''))
                    
                self.flash_on = not self.flash_on
                last_toggle_time = current_time
                
            # Sleep for a reasonable time to save CPU
            # For very slow rates, we can use longer sleeps
            if half_cycle > 0.5:
                sleep_time = 0.1  # 100ms sleep for slower rates (>2 sec cycle)
            else:
                sleep_time = 0.05  # 50ms sleep for faster rates
                
            time.sleep(sleep_time)
    
    def monitor_key_presses(self):
        """Monitor key presses 1-8 to change the image."""
        while self.running:
            for i in range(1, 9):
                if keyboard.is_pressed(str(i)):
                    # Update the selected direction file
                    self.update_direction_file(i)
                    # Load the corresponding image
                    self.root.after(0, lambda d=i: self.load_image(d))
                    time.sleep(0.3)  # Prevent multiple triggers
            
            # Toggle flashing with 'f' key
            if keyboard.is_pressed('f'):
                self.root.after(0, self.toggle_flashing)
                time.sleep(0.3)  # Prevent multiple triggers
                
            time.sleep(0.1)
    
    def update_direction_file(self, direction):
        """Update the shared file with the selected direction."""
        try:
            with open(self.selected_direction_file, 'w') as f:
                f.write(str(direction))
        except Exception as e:
            print(f"Error writing to file: {str(e)}")
    
    def monitor_file(self):
        """Monitor the shared file for changes from brain_control.py."""
        last_modified = 0
        while self.running:
            try:
                if os.path.exists(self.selected_direction_file):
                    current_modified = os.path.getmtime(self.selected_direction_file)
                    if current_modified > last_modified:
                        last_modified = current_modified
                        with open(self.selected_direction_file, 'r') as f:
                            direction_str = f.read().strip()
                            if direction_str.isdigit():
                                direction = int(direction_str)
                                if 1 <= direction <= 8:
                                    self.root.after(0, lambda d=direction: self.load_image(d))
            except Exception as e:
                print(f"Error reading file: {str(e)}")
            time.sleep(0.5)
    
    def cleanup(self):
        """Clean up resources before closing."""
        self.running = False
        self.stop_flashing()
        if os.path.exists(self.selected_direction_file):
            try:
                os.remove(self.selected_direction_file)
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ImageViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main() 