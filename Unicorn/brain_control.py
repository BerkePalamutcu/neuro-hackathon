import numpy as np
import time
import keyboard
from pynput import keyboard as kb
import os
import sys
import threading
import cv2
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.animation import FuncAnimation
import random

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
    print(f"Added current directory to Python path: {current_dir}")

# Always try to use hardware mode first
USE_SIMULATION = False

# Try to import the Unicorn module (our custom wrapper)
try:
    from unicorn import Unicorn
    print("Unicorn library found - using hardware mode")
except ImportError as e:
    print(f"ERROR: Unicorn library not found: {e}")
    print("Do you want to fall back to simulation mode? (y/n)")
    response = input().lower()
    if response == 'y':
        USE_SIMULATION = True
    else:
        print("Exiting...")
        sys.exit(1)

# Create a simulation class if needed
if USE_SIMULATION:
    # Create a simple simulation mode for testing
    class Unicorn:
        def __init__(self, notch_frequency=50.0):
            self.notch_frequency = notch_frequency
            self.running = False
            print(f"[SIMULATION] Created Unicorn simulator with notch filter at {notch_frequency} Hz")
            
        def start(self):
            self.running = True
            print("[SIMULATION] Started data acquisition (simulated)")
            
        def stop(self):
            self.running = False
            print("[SIMULATION] Stopped data acquisition (simulated)")
            
        def get_serial_number(self):
            return "SIMULATOR-12345"
            
        def get_data(self, seconds):
            import numpy as np
            # Generate random noise (8 channels, 250Hz sample rate)
            num_samples = int(250 * seconds)
            data = np.zeros((8, num_samples))
            
            for channel in range(8):
                # Create random data
                data[channel, :] = 2 + 0.5 * np.random.randn(num_samples)
                
            return data
    
    print("[SIMULATION] Using simulation mode with random data for testing")

# Direction mapping
# 1: Up
# 2: Down
# 3: Left
# 4: Right
# 5: Up-Left (diagonal)
# 6: Up-Right (diagonal)
# 7: Down-Left (diagonal)
# 8: Down-Right (diagonal)

# Initialize variables
current_direction = None
# Change from min/max ranges to target values with tolerance
brainwave_ranges = {
    1: {'target': 0, 'tolerance': 500},  # Up
    2: {'target': 0, 'tolerance': 500},  # Down
    3: {'target': 0, 'tolerance': 500},  # Left
    4: {'target': 0, 'tolerance': 500},  # Right
    5: {'target': 0, 'tolerance': 500},  # Up-Left
    6: {'target': 0, 'tolerance': 500},  # Up-Right
    7: {'target': 0, 'tolerance': 500},  # Down-Left
    8: {'target': 0, 'tolerance': 500},  # Down-Right
}

calibration_mode = True
recording_data = False
recorded_values = []
last_detection = None
detection_cooldown = 0
keyboard_control = False

# Shared file for communication with image viewer
SELECTED_DIRECTION_FILE = "selected_direction.txt"

# Direction names for display
DIRECTION_NAMES = {
    1: "Up",
    2: "Down",
    3: "Left",
    4: "Right",
    5: "Up-Left",
    6: "Up-Right",
    7: "Down-Left",
    8: "Down-Right"
}

# Add a dictionary to store rolling average data
max_window_size = 300  # About 1 minute at 5fps (never reset samples unless explicitly requested)
min_samples_required = 300  # Wait for 1 minute worth of data before guessing
rolling_values = {1: []}  # Only need one rolling window
detection_frame_rate = 1  # Frames per second for detection display
frame_timer = 0
collection_start_time = None  # To track when we started collecting data

def update_image_viewer(direction):
    """Update the image viewer by writing to the shared file."""
    try:
        with open(SELECTED_DIRECTION_FILE, 'w') as f:
            f.write(str(direction))
    except Exception as e:
        print(f"Error writing to direction file: {str(e)}")

def on_key_press(key):
    global current_direction, calibration_mode, recording_data, recorded_values, detection_frame_rate
    
    try:
        # Get the key character or name
        key_char = None
        try:
            key_char = key.char  # For regular keys
        except AttributeError:
            # For special keys
            if key == kb.Key.space:
                key_char = ' '
            else:
                # Other special key, ignore
                return
        
        # Only print for meaningful keys (not debugging every key press)
        if key_char in "12345678cslrf ":
            print(f"Key pressed: {key_char}")
        
        # Check if a number key 1-8 was pressed
        if key_char in "12345678":
            direction = int(key_char)
            # Clear the rolling data when changing directions
            if not calibration_mode:
                reset_rolling_data()
            current_direction = direction
            print(f"\nSelected direction: {DIRECTION_NAMES[direction]}")
            # Update the image viewer
            update_image_viewer(direction)
            return
            
        # Reset data gathering with 'r' key
        elif key_char == 'r':
            reset_rolling_data()
            return
            
        # Start/stop recording brainwave data with spacebar
        if key_char == ' ':
            if current_direction is None:
                print("\nPlease select a direction (1-8) first")
                return
                
            recording_data = not recording_data
            if recording_data:
                recorded_values = []
                print(f"\n▶ RECORDING brainwave values for {DIRECTION_NAMES[current_direction]}... Focus on the displayed image")
                print("Press SPACE again to stop recording")
            else:
                print(f"Values recorded: {len(recorded_values)}")
                if recorded_values:
                    # Calculate average and standard deviation
                    avg_val = np.mean(recorded_values)
                    std_val = np.std(recorded_values)
                    
                    # Set tolerance to 2x standard deviation or minimum of 500
                    tolerance = max(std_val * 2, 500.0)
                    
                    # Update calibration data
                    brainwave_ranges[current_direction]['target'] = avg_val
                    brainwave_ranges[current_direction]['tolerance'] = tolerance
                    
                    print(f"\n✓ Set target for {DIRECTION_NAMES[current_direction]}: {avg_val:.2f} (±{tolerance:.2f})")
                    
                    # Show calibration status
                    print("\nCalibration Status:")
                    for dir_num, dir_name in DIRECTION_NAMES.items():
                        data = brainwave_ranges[dir_num]
                        if data['target'] == 0:
                            status = "❌ Not calibrated"
                        else:
                            status = f"✓ Calibrated: Target {data['target']:.2f} (±{data['tolerance']:.2f})"
                        print(f"  {dir_num}: {dir_name.ljust(10)} - {status}")
                else:
                    print("\nNo data recorded")
                    
        # Toggle calibration mode
        elif key_char == 'c':
            calibration_mode = not calibration_mode
            if calibration_mode:
                print("\n🔧 ENTERED CALIBRATION MODE 🔧")
                print("1. Use keys 1-8 to select a direction")
                print("2. Press SPACE to start recording")
                print("3. Focus on the image while recording")
                print("4. Press SPACE again to stop recording")
                print("5. Repeat for all directions")
                print("6. Press 's' to save calibration")
                print("7. Press 'c' again to exit calibration mode")
            else:
                print("\n🚀 ENTERED DETECTION MODE 🚀")
                print("===================================")
                print("Focus on a direction and the system will attempt to detect it")
                print("The system will show what direction is detected")
                print("Press 'c' to return to calibration mode")
                print("===================================")
                # Check if we have any calibrated directions
                calibrated = False
                for dir_num in brainwave_ranges:
                    if brainwave_ranges[dir_num]['target'] != 0:
                        calibrated = True
                        break
                if not calibrated:
                    print("\n⚠️ WARNING: No directions are calibrated yet! ⚠️")
                    print("Please calibrate at least one direction first.")
                
        # Save calibration data
        elif key_char == 's':
            save_calibration()
            
        # Load calibration data
        elif key_char == 'l':
            try:
                load_calibration()
                # Important: Print confirmation after successful load
                print("Calibration data loaded successfully!")
            except Exception as e:
                print(f"Error loading calibration: {e}")
            
        # Change frame rate with 'f' key
        elif key_char == 'f':
            cycle_frame_rate()
            return
            
    except Exception as e:
        print(f"Key press error: {e}")
        # For debugging
        print(f"Key type: {type(key)}, Key: {key}")

def save_calibration():
    """Save calibration data to file with improved error handling"""
    try:
        import json
        import numpy as np
        
        # Create a copy of brainwave_ranges with Python native types
        # Convert any numpy types to Python native types to ensure JSON serialization works
        serializable_ranges = {}
        for direction, range_data in brainwave_ranges.items():
            # Handle potential numpy types and ensure they're converted to Python floats
            target = range_data['target']
            tolerance = range_data['tolerance']
            
            # Convert numpy types to Python native types
            if isinstance(target, (np.number, np.ndarray)):
                target = float(target)
            if isinstance(tolerance, (np.number, np.ndarray)):
                tolerance = float(tolerance)
                
            serializable_ranges[direction] = {
                'target': target,
                'tolerance': tolerance
            }
        
        # Save with indentation for readability
        with open('brain_calibration.json', 'w') as f:
            json.dump(serializable_ranges, f, indent=2)
            
        print("\n💾 Calibration data saved to brain_calibration.json")
        
        # Show what was saved
        print("\nSaved values:")
        for dir_num, dir_name in DIRECTION_NAMES.items():
            if dir_num in serializable_ranges:
                data = serializable_ranges[dir_num]
                if data['target'] == 0:
                    status = "❌ Not calibrated"
                else:
                    status = f"✓ Calibrated: Target {data['target']:.2f} (±{data['tolerance']:.2f})"
                print(f"  {dir_num}: {dir_name.ljust(10)} - {status}")
                
    except Exception as e:
        print(f"\n❌ Error saving calibration data: {str(e)}")
        # For debugging
        import traceback
        traceback.print_exc()

def load_calibration(silent=False):
    global brainwave_ranges
    import json
    try:
        with open('brain_calibration.json', 'r') as f:
            loaded_data = json.load(f)
            
        # Convert string keys to integers
        brainwave_ranges = {int(k): v for k, v in loaded_data.items()}
            
        if not silent:
            print("\n📂 Calibration data loaded from brain_calibration.json")
            
            # Show calibration status
            print("\nCalibration Status:")
            for dir_num, dir_name in DIRECTION_NAMES.items():
                if dir_num in brainwave_ranges:
                    data = brainwave_ranges[dir_num]
                    if data['target'] == 0:
                        status = "❌ Not calibrated"
                    else:
                        status = f"✓ Calibrated: Target {data['target']:.2f} (±{data['tolerance']:.2f})"
                    print(f"  {dir_num}: {dir_name.ljust(10)} - {status}")
                else:
                    print(f"  {dir_num}: {dir_name.ljust(10)} - ❌ Not found in calibration data")
    except FileNotFoundError:
        if not silent:
            print("\n❌ No calibration file found")
        raise
    except Exception as e:
        if not silent:
            print(f"\n❌ Error loading calibration data: {str(e)}")
        raise

def detect_direction(data, channel_of_interest=1):
    """
    Detect brain wave direction based on rolling average of calibrated values
    Uses a more sophisticated comparison with smoothed signals
    Waits until we have 1 minute worth of data
    """
    global brainwave_ranges, last_detection, detection_cooldown, rolling_values
    
    # Skip detection if on cooldown
    if detection_cooldown > 0:
        detection_cooldown -= 1
        return None
    
    try:
        # Get the signal from the channel of interest
        signal = np.mean(data[channel_of_interest, :])
        
        # Make sure the signal is a valid number
        if not np.isfinite(signal):
            return None
            
        # Wait until we have enough data points (about 1 minute worth)
        if len(rolling_values[1]) < min_samples_required:
            return None
            
        # Calculate the actual average using all collected samples
        avg_signal = np.mean(rolling_values[1])
        
        # Calculate standard deviation to determine signal stability
        std_signal = np.std(rolling_values[1])
        
        # Debug - print values occasionally
        if random.random() < 0.05:  # About 5% of function calls
            print(f"\nDebug - Current: {signal:.2f}, Avg: {avg_signal:.2f}, StdDev: {std_signal:.2f}, Samples: {len(rolling_values[1])}")
            
        # Calculate how well the average signal matches each direction
        matches = {}
        for direction, values in brainwave_ranges.items():
            # Check that we have valid values
            if 'target' not in values or 'tolerance' not in values:
                continue
                
            target = float(values["target"])
            tolerance = float(values["tolerance"])
            
            # Skip if tolerance is zero or invalid
            if tolerance <= 0:
                continue
                
            # Calculate the normalized distance from average signal to target
            distance = abs(avg_signal - target) / tolerance
            matches[direction] = distance
        
        # If no valid matches were found, return None
        if not matches:
            return None
            
        # Get the direction with the smallest distance (best match)
        best_match = min(matches.items(), key=lambda x: x[1])
        direction_id = best_match[0]
        match_score = best_match[1]
        
        # Only accept the match if it's close enough (distance less than 1.0 means 
        # it's within the tolerance range) and different from the last detection
        if match_score < 1.0 and direction_id != last_detection:
            last_detection = direction_id
            detection_cooldown = 30  # About 3 seconds cooldown
            return direction_id
        
        # Reset last detection if no match for a while
        if detection_cooldown == 0:
            last_detection = None
            
        return None
        
    except Exception as e:
        print(f"\nError in detect_direction: {e}")
        return None

def reset_rolling_data():
    """Reset the rolling window data to start fresh"""
    global rolling_values, collection_start_time
    rolling_values = {1: []}
    collection_start_time = time.time()  # Start the timer
    print("\n🔄 Reset data buffer - starting fresh data collection")
    print(f"Will make guesses after collecting {min_samples_required} samples (about 1 minute)...")

def main():
    # Initialize Unicorn device
    unicorn = None
    try:
        # Use actual Unicorn hardware with 50Hz notch filter
        unicorn = Unicorn(notch_frequency=50.0)
        print(f"Connected to device with serial number: {unicorn.get_serial_number()}")
        
        # Start acquisition
        unicorn.start()
        
        # Load the user's calibration values
        global brainwave_ranges, calibration_mode, frame_timer, collection_start_time
        frame_timer = 0  # Initialize frame timer
        collection_start_time = time.time()  # Initialize collection start time
        
        # Try to load calibration data from file first
        try:
            import json
            import os
            
            if os.path.exists('brain_calibration.json'):
                with open('brain_calibration.json', 'r') as f:
                    loaded_ranges = json.load(f)
                    # Convert string keys back to integers
                    brainwave_ranges = {int(k): v for k, v in loaded_ranges.items()}
                    print("Loaded calibration data from brain_calibration.json")
            else:
                # User's actual calibration data from previous tests
                brainwave_ranges = {
                    1: {"target": -115.16266632080078, "tolerance": 5167.9677734375},  # Up
                    2: {"target": -156.12684631347656, "tolerance": 5212.36083984375},  # Down
                    3: {"target": -106.15089416503906, "tolerance": 5174.42822265625},  # Left
                    4: {"target": -51.48378372192383, "tolerance": 5216.78466796875},   # Right
                    5: {"target": -99.9202651977539, "tolerance": 5230.6650390625},     # Up-Left
                    6: {"target": -81.35531616210938, "tolerance": 5232.67578125},      # Up-Right
                    7: {"target": -132.3319549560547, "tolerance": 5223.4482421875},    # Down-Left
                    8: {"target": -125.76422882080078, "tolerance": 5115.744140625}     # Down-Right
                }
                print("Using default calibration values")
        except Exception as e:
            print(f"Error loading calibration data: {e}")
            print("Using default calibration values")
            
            # Fallback to default values
            brainwave_ranges = {
                1: {"target": -115.16266632080078, "tolerance": 5167.9677734375},  # Up
                2: {"target": -156.12684631347656, "tolerance": 5212.36083984375},  # Down
                3: {"target": -106.15089416503906, "tolerance": 5174.42822265625},  # Left
                4: {"target": -51.48378372192383, "tolerance": 5216.78466796875},   # Right
                5: {"target": -99.9202651977539, "tolerance": 5230.6650390625},     # Up-Left
                6: {"target": -81.35531616210938, "tolerance": 5232.67578125},      # Up-Right
                7: {"target": -132.3319549560547, "tolerance": 5223.4482421875},    # Down-Left
                8: {"target": -125.76422882080078, "tolerance": 5115.744140625}     # Down-Right
            }
        
        # Auto-save calibration data to file
        with open('brain_calibration.json', 'w') as f:
            json.dump(brainwave_ranges, f)
        print("Current calibration data saved to brain_calibration.json")
        
        calibration_mode = False  # Start in detection mode
        print("Starting in DETECTION MODE.")
        
        # Listen for key presses in a non-blocking way
        listener = kb.Listener(on_press=on_key_press)
        listener.start()
        
        print("\n=== Brainwave Control System ===")
        print("Press 1-8 to select direction:")
        print("  1: Up")
        print("  2: Down")
        print("  3: Left")
        print("  4: Right")
        print("  5: Up-Left diagonal")
        print("  6: Up-Right diagonal")
        print("  7: Down-Left diagonal")
        print("  8: Down-Right diagonal")
        print("Press SPACE to start/stop recording brainwave values")
        print("Press 'c' to toggle between calibration and detection modes")
        print("Press 's' to save calibration data")
        print("Press 'l' to load calibration data")
        print("Press 'f' to change frame rate (1, 2, 4, or 8 fps)")
        print("Press 'r' to reset data gathering")
        print("Press Ctrl+C to exit")
        
        # Initial mode message based on current mode
        if calibration_mode:
            print("\n🔧 CALIBRATION MODE ACTIVE 🔧")
            print("Select a direction (1-8) and press SPACE to start recording")
        else:
            print("\n🚀 DETECTION MODE ACTIVE 🚀")
            print("Focus on a direction and the system will attempt to detect it")
            print("Press 'c' to switch to calibration mode if needed")
            print(f"Current display rate: {detection_frame_rate} frame(s) per second. Press 'f' to change.")
            print(f"Collecting data continuously for {min_samples_required} samples (about 1 minute) before making detection")
            print("Press 'r' to reset data gathering if needed")
            
            # Reset data gathering when switching to detection mode
            reset_rolling_data()
        
        # Frame rate cycle: 1 → 2 → 4 → 8 → 1...
        def cycle_frame_rate():
            global detection_frame_rate
            if detection_frame_rate == 1:
                detection_frame_rate = 2
            elif detection_frame_rate == 2:
                detection_frame_rate = 4
            elif detection_frame_rate == 4:
                detection_frame_rate = 8
            else:
                detection_frame_rate = 1
            print(f"\nDetection display rate changed to {detection_frame_rate} frame(s) per second")
            
            # Reset frame timer to avoid delays after changing rate
            global frame_timer
            frame_timer = 0
        
        # Main loop for detection
        try:
            frame_count = 0
            last_space_state = False
            current_space_state = False  # Initialize here
            while True:
                # Get data from Unicorn device
                try:
                    data = unicorn.get_data(0.2)  # Get 0.2 seconds worth of data
                    
                    # Direct keyboard event checking as backup
                    # Check for spacebar directly using the keyboard module
                    try:
                        current_space_state = keyboard.is_pressed('space')
                    except Exception as e:
                        print(f"Error checking keyboard: {e}")
                        current_space_state = False
                    
                    if current_space_state and not last_space_state and calibration_mode:
                        # Space key just pressed and in calibration mode
                        if current_direction is not None:
                            global recording_data, recorded_values
                            recording_data = not recording_data
                            if recording_data:
                                recorded_values = []
                                print(f"\n▶ RECORDING brainwave values for {DIRECTION_NAMES[current_direction]}... Focus on the displayed image")
                                print("Press SPACE again to stop recording")
                            else:
                                print(f"Values recorded: {len(recorded_values)}")
                                if recorded_values:
                                    # Calculate average and standard deviation
                                    avg_val = np.mean(recorded_values)
                                    std_val = np.std(recorded_values)
                                    
                                    # Set tolerance to 2x standard deviation or minimum of 500
                                    tolerance = max(std_val * 2, 500.0)
                                    
                                    # Update calibration data
                                    brainwave_ranges[current_direction]['target'] = avg_val
                                    brainwave_ranges[current_direction]['tolerance'] = tolerance
                                    
                                    print(f"\n✓ Set target for {DIRECTION_NAMES[current_direction]}: {avg_val:.2f} (±{tolerance:.2f})")
                                    
                                    # Show calibration status
                                    print("\nCalibration Status:")
                                    for dir_num, dir_name in DIRECTION_NAMES.items():
                                        data = brainwave_ranges[dir_num]
                                        if data['target'] == 0:
                                            status = "❌ Not calibrated"
                                        else:
                                            status = f"✓ Calibrated: Target {data['target']:.2f} (±{data['tolerance']:.2f})"
                                        print(f"  {dir_num}: {dir_name.ljust(10)} - {status}")
                                else:
                                    print("\nNo data recorded")
                except Exception as e:
                    print(f"Error getting data from Unicorn: {e}")
                last_space_state = current_space_state
                
                if data is not None:
                    try:
                        # Use channel 3 (C3, left motor cortex) for demonstration
                        channel = 2  # Using 0-based indexing, so channel 3 is at index 2
                        
                        # Extract the value from the appropriate channel
                        if isinstance(data, np.ndarray) and data.size > 0:
                            if len(data.shape) > 1 and data.shape[0] > channel:
                                value = np.mean(data[channel, :])
                            else:
                                print("Warning: Data shape is not as expected. Using first element.")
                                value = data.flat[0] if data.size > 0 else 0
                        else:
                            print("Warning: Data is not a non-empty numpy array")
                            value = 0
                        
                        # In calibration mode with recording active
                        if calibration_mode and recording_data and current_direction is not None:
                            # Print the first few values to see what's being captured
                            if len(recorded_values) < 3:
                                print(f"Captured value: {value:.4f}")
                            
                            recorded_values.append(value)
                            # Show recording progress indicator less frequently
                            if frame_count % 15 == 0:  # Update every 15 frames instead of 5
                                print(".", end="", flush=True)
                        
                        # In detection mode
                        elif not calibration_mode:
                            # Update frame timer for controlling display frequency
                            frame_timer += 1
                            
                            # Update the rolling window with the current value
                            # This must happen every frame regardless of display rate
                            rolling_values[1].append(value)
                            # DON'T truncate to max_window_size - let it grow
                            
                            # Calculate time between updates based on detection_frame_rate
                            # Ensure update_interval is at least 1
                            update_interval = max(1, int(10 / detection_frame_rate))  # Base rate of 10fps with sleep of 0.1s
                            
                            # Display current value and update UI only at the specified frame rate
                            if frame_timer % update_interval == 0:
                                print(f"\r", end="")  # Clear the current line
                                
                                # Check if we have enough data for detection
                                if len(rolling_values[1]) < min_samples_required:
                                    # Show data gathering progress
                                    buffer_fill = len(rolling_values[1]) / min_samples_required * 100
                                    progress_bar = "█" * int(buffer_fill / 10) + "░" * (10 - int(buffer_fill / 10))
                                    
                                    # Calculate time elapsed and remaining
                                    elapsed_time = time.time() - collection_start_time
                                    elapsed_seconds = int(elapsed_time)
                                    
                                    # Calculate remaining time based on current rate
                                    if elapsed_time > 0:
                                        samples_per_second = len(rolling_values[1]) / elapsed_time
                                        if samples_per_second > 0:
                                            seconds_remaining = int((min_samples_required - len(rolling_values[1])) / samples_per_second)
                                        else:
                                            seconds_remaining = "unknown"
                                    else:
                                        seconds_remaining = "calculating..."
                                    
                                    print(f"Gathering data: {progress_bar} {buffer_fill:.0f}% ({len(rolling_values[1])}/{min_samples_required}) - {elapsed_seconds}s elapsed, ~{seconds_remaining}s remaining", end="")
                                else:
                                    # Get current signal and rolling average
                                    if len(rolling_values[1]) > 0:
                                        avg_value = np.mean(rolling_values[1])
                                        std_value = np.std(rolling_values[1])
                                        elapsed_time = int(time.time() - collection_start_time)
                                        print(f"Current: {value:.2f}, Avg: {avg_value:.2f}, StdDev: {std_value:.2f}, Samples: {len(rolling_values[1])} ({elapsed_time}s)", end="")
                                    else:
                                        avg_value = value
                                        print(f"Current value: {value:.2f}", end="")
                                    
                                    # Check if we have any calibrated directions before comparing
                                    has_calibration = False
                                    for dir_num, dir_data in brainwave_ranges.items():
                                        if dir_data['target'] != 0:  # Has calibration
                                            has_calibration = True
                                            break
                                    
                                    if not has_calibration:
                                        print("  [No calibrated directions available - please calibrate first]", end="")
                                    else:
                                        # Find the closest target among calibrated directions
                                        closest_dir = None
                                        best_match = float('inf')
                                        
                                        # Calculate actual rolling average
                                        if len(rolling_values[1]) > 0:
                                            # Print all values in the rolling window for debugging
                                            if frame_count % 50 == 0:  # Don't print too often
                                                print(f"\nRolling window values: {rolling_values[1]}")
                                            
                                            # Calculate the actual rolling average
                                            avg_value = np.mean(rolling_values[1])
                                        else:
                                            avg_value = value
                                        
                                        for dir_num, dir_data in brainwave_ranges.items():
                                            if dir_data['target'] == 0:  # Skip uncalibrated
                                                continue
                                                
                                            target = float(dir_data['target'])
                                            # Use the current rolling average for all direction comparisons
                                            distance = abs(avg_value - target)
                                            if distance < best_match:
                                                best_match = distance
                                                closest_dir = dir_num
                                        
                                        if closest_dir:
                                            tolerance = float(brainwave_ranges[closest_dir]['tolerance'])
                                            relative_distance = best_match / tolerance
                                            if relative_distance <= 1.0:
                                                confidence = int((1.0 - relative_distance) * 100)
                                                print(f"  [Closest to {DIRECTION_NAMES[closest_dir]}, confidence: {confidence}%]")
                                            else:
                                                print(f"  [Closest to {DIRECTION_NAMES[closest_dir]}, but outside tolerance]")
                                
                                # Only try detection at the specified frame rate and when we have enough data
                                if len(rolling_values[1]) >= min_samples_required:
                                    try:
                                        # Detect direction using specified channel
                                        detected = detect_direction(data, channel_of_interest=channel)
                                        if detected:
                                            # Update image viewer
                                            update_image_viewer(detected)
                                            
                                            # Print detection details
                                            target = brainwave_ranges[detected]['target']
                                            tolerance = brainwave_ranges[detected]['tolerance']
                                            
                                            # Use rolling average for confidence calculation
                                            avg_signal = np.mean(rolling_values[1])
                                            std_signal = np.std(rolling_values[1])
                                                
                                            distance = abs(avg_signal - target)
                                            relative_distance = distance / tolerance
                                            confidence = int((1.0 - relative_distance) * 100)
                                            confidence_bar = "█" * (confidence // 10)
                                            
                                            print(f"\n🎯 DETECTED: {DIRECTION_NAMES[detected].upper()}")
                                            print(f"Current value: {value:.2f}")
                                            print(f"Average: {avg_signal:.2f} (from {len(rolling_values[1])} samples over {int(time.time() - collection_start_time)}s)")
                                            print(f"Signal stability: StdDev = {std_signal:.2f}")
                                            print(f"Target: {target:.2f} (±{tolerance:.2f})")
                                            print(f"Distance from target: {distance:.2f} units ({relative_distance:.2f}x tolerance)")
                                            print(f"Confidence: {confidence}% {confidence_bar}")
                                            print("-------------------------")
                                    except Exception as e:
                                        print(f"Error in direction detection: {e}")
                    except Exception as e:
                        print(f"Error processing data: {e}")
                
                # Small delay to prevent CPU overload
                # Adjust sleep time based on frame rate to maintain consistent update frequency
                if detection_frame_rate <= 2:
                    time.sleep(0.2)  # 5fps base rate for 1-2fps display
                else:
                    time.sleep(0.1)  # 10fps base rate for 4-8fps display
                
                frame_count += 1
                
                # Restart frame timer to prevent overflow
                if frame_timer > 1000:
                    frame_timer = 0
                
        except KeyboardInterrupt:
            print("\nExiting...")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if USE_SIMULATION:
            print("Error occurred in simulation mode")
        else:
            print("Error occurred in hardware mode")
            print("You may need to restart your Unicorn device")
    
    finally:
        # Clean up
        if unicorn and unicorn.running:
            print("Stopping data acquisition...")
            try:
                unicorn.stop()
                print("Device stopped")
            except:
                print("Error stopping device")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc() 