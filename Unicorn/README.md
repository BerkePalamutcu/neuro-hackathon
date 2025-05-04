# Brainwave Control System

This Python application allows you to control arrow movements by measuring brainwave activities using the Unicorn Black Suite headset.

## Requirements

- Python 3.7+
- Unicorn Black Suite headset
- Unicorn Python API license

## Installation

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Ensure your Unicorn Black Suite headset is connected and the drivers are installed.

3. Place your directional images in the same directory with these filenames:
   - up.jpg
   - down.jpg
   - left.jpg
   - right.jpg
   - up_left.jpg
   - up_right.jpg
   - down_left.jpg
   - down_right.jpg

## Usage

### Main Control Application

Run the application:
```
python brain_control.py
```

#### Controls

- Press keys 1-8 to select which arrow/direction you want to calibrate:
  - 1: Up
  - 2: Down
  - 3: Left
  - 4: Right
  - 5: Up-Left diagonal
  - 6: Up-Right diagonal
  - 7: Down-Left diagonal
  - 8: Down-Right diagonal

- Press Space to start/stop recording brainwave values for the selected direction
- Press 'c' to toggle between calibration and detection modes
- Press 's' to save calibration
- Press 'l' to load calibration
- Press Ctrl+C to exit

### Image Viewer

Run the image viewer:
```
python image_viewer.py
```

This tool displays the directional images with flashing animations:
- Each direction has its own unique flash frequency:
  - Up (1): 7.5 Hz
  - Down (2): 3.0 Hz
  - Left (3): 5.0 Hz
  - Right (4): 6.0 Hz
  - Up-Left (5): 4.0 Hz
  - Up-Right (6): 8.0 Hz
  - Down-Left (7): 2.5 Hz
  - Down-Right (8): 4.5 Hz

#### Image Viewer Controls
- Press keys 1-8 to display different directional images
- Press 'f' or click the "Start Flashing" button to toggle flashing animation
- The brain_control.py application will automatically update the displayed image

### Visualization Tool

Run the visualization tool:
```
python visualize_brain_activity.py
```

This tool shows:
- Real-time brainwave activity scaled to the 1-5 range
- Calibrated ranges for each direction
- Current detection status

It's useful to run this on a second monitor while calibrating with the main application.

### Calibration Process

1. Start in calibration mode (default on startup)
2. Launch the image viewer with `python image_viewer.py`
3. Press a number key (1-8) in the brain_control app to select the direction you want to calibrate
4. Press 'f' in the image viewer to start the flashing animation
5. Press Space in the brain_control app to start recording brainwave values while focusing on the flashing image
6. Press Space again to stop recording and set the range for that direction
7. Repeat for all directions
8. Press 's' to save your calibration
9. Press 'c' to switch to detection mode and test

The system scales brainwave readings to the range 1-5 as specified and uses a 50Hz notch filter. 