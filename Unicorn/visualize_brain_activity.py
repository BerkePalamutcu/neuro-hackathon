import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import json
import time
import sys

# Try to import Unicorn API
try:
    from unicorn import Unicorn
    print("Unicorn library found - using hardware mode")
except ImportError:
    print("ERROR: Unicorn library not found. Please install the Unicorn Hybrid Black APIs.")
    print("Exiting...")
    sys.exit(1)

# Create figure for plotting
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
fig.suptitle('Brain Activity Visualization')

# Initialize variables
times = []
values = []
max_points = 100  # Number of points to display

# Initialize plot lines
line, = ax1.plot(times, values, label='Brain Activity (1-5 scale)')
scaled_value = 3  # Default starting value

# Load calibration data if available
try:
    with open('brain_calibration.json', 'r') as f:
        ranges = json.load(f)
    print("Calibration data loaded")
except FileNotFoundError:
    print("No calibration file found, using empty ranges")
    ranges = {
        1: {'min': 0, 'max': 0},  # Up
        2: {'min': 0, 'max': 0},  # Down
        3: {'min': 0, 'max': 0},  # Left
        4: {'min': 0, 'max': 0},  # Right
        5: {'min': 0, 'max': 0},  # Up-Left
        6: {'min': 0, 'max': 0},  # Up-Right
        7: {'min': 0, 'max': 0},  # Down-Left
        8: {'min': 0, 'max': 0},  # Down-Right
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

# Set up the axes
ax1.set_ylim(0.5, 5.5)
ax1.set_xlabel('Time')
ax1.set_ylabel('Brain Activity (1-5)')
ax1.set_title('Real-time Brain Activity')
ax1.legend()
ax1.grid(True)

# Set up the second plot for ranges
directions = list(ranges.keys())
mins = [ranges[d]['min'] for d in directions]
maxs = [ranges[d]['max'] for d in directions]
names = [direction_names[d] for d in directions]

# Create bars for ranges
bars = ax2.bar(names, np.zeros(len(directions)), alpha=0.7)
ax2.set_ylim(0.5, 5.5)
ax2.set_xlabel('Direction')
ax2.set_ylabel('Brain Activity Range')
ax2.set_title('Calibrated Direction Ranges')
ax2.grid(True)

# Add a horizontal line for current value
horiz_line = ax2.axhline(y=scaled_value, color='r', linestyle='-', label='Current Value')
ax2.legend()

def animate(i, unicorn):
    global scaled_value, times, values
    
    # Get data from the device (0.1 second of data)
    data = unicorn.get_data(0.1)
    
    # We'll use the average of the EEG channels (0-7) as our measure
    eeg_data = data[0:8, :]
    avg_eeg = np.mean(eeg_data)
    
    # Scale the value to 1-5 range
    scaled_value = 1 + 4 * (avg_eeg - np.min(eeg_data)) / (np.max(eeg_data) - np.min(eeg_data)) if np.max(eeg_data) > np.min(eeg_data) else 3
    
    # Add x and y to lists
    times.append(time.time())
    values.append(scaled_value)
    
    # Limit lists to set number of items
    times = times[-max_points:]
    values = values[-max_points:]
    
    # Update line with new values
    line.set_data(range(len(times)), values)
    
    # Adjust axes if needed
    if len(times) > 0:
        ax1.set_xlim(0, len(times))
    
    # Update horizontal line
    horiz_line.set_ydata(scaled_value)
    
    # Update range bars
    for i, d in enumerate(directions):
        # Draw min to max as bars
        bars[i].set_height(ranges[d]['max'] - ranges[d]['min'])
        bars[i].set_y(ranges[d]['min'])
    
    # Check if current value is in any range
    detected = None
    for d, r in ranges.items():
        if r['min'] <= scaled_value <= r['max']:
            detected = d
            break
    
    # Update title with current value and detected direction
    ax1.set_title(f'Real-time Brain Activity: {scaled_value:.2f}' + 
                 (f' - Detected: {direction_names[detected]}' if detected else ''))
    
    return line, bars, horiz_line

def main():
    # Initialize Unicorn device
    try:
        # Use hardware with notch filter at 50Hz as specified
        unicorn = Unicorn(notch_frequency=50.0)
        print(f"Connected to device with serial number: {unicorn.get_serial_number()}")
        
        # Start acquisition
        unicorn.start()
        
        # Set up animation
        ani = animation.FuncAnimation(
            fig, animate, fargs=(unicorn,), interval=100, blit=True)
        
        plt.tight_layout()
        plt.show()
        
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if 'unicorn' in locals():
            unicorn.stop()
            print("Device stopped")

if __name__ == "__main__":
    main() 