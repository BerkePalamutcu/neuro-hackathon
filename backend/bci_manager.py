import numpy as np
import asyncio
import time
from typing import Dict, Optional, List, Callable, Any

# This is a mock of the Unicorn Python API for development/hackathon purposes
# In a real implementation, you would use the actual Unicorn API
class MockUnicornAPI:
    def __init__(self):
        self.connected = False
        self.data = None
        self.channels = 8
        self.sample_rate = 250
        
    def connect(self):
        """Mock connection to Unicorn device"""
        self.connected = True
        print("Mock Unicorn device connected")
        return True
        
    def disconnect(self):
        """Mock disconnection from Unicorn device"""
        self.connected = False
        print("Mock Unicorn device disconnected")
        
    def get_data(self, samples):
        """Generate mock EEG data"""
        # Create random data for demo purposes
        # In a real implementation, this would get actual EEG data
        data = np.random.normal(0, 10, (self.channels, samples))
        
        # Add some structured noise to simulate brain activity in different bands
        t = np.arange(samples) / self.sample_rate
        
        # Alpha waves (8-13 Hz) - stronger when relaxed
        alpha = np.sin(2 * np.pi * 10 * t) * 5
        
        # Beta waves (13-30 Hz) - stronger when focused/concentrating
        beta = np.sin(2 * np.pi * 20 * t) * 7
        
        # Apply to channels
        for i in range(self.channels):
            data[i] += alpha * (1 if i % 2 == 0 else 0.5)
            data[i] += beta * (0.5 if i % 2 == 0 else 1)
        
        return data

# For the real implementation, uncomment this and comment out MockUnicornAPI
# try:
#     from unicorn.python_api import UnicornAPI as UnicornBlackAPI
# except ImportError:
#     print("Warning: Unicorn API not found, using mock implementation")
#     UnicornBlackAPI = MockUnicornAPI

# For the hackathon, we'll use the mock API
UnicornBlackAPI = MockUnicornAPI

class BCIManager:
    """
    Manages the brain-computer interface connection and signal processing.
    """
    def __init__(self):
        self.unicorn = UnicornBlackAPI()
        self.connected = False
        self.focus_threshold = 0.65
        self.selection_threshold = 0.75
        self.last_bandpowers = None
        self.focus_history = []
        self.max_history = 10
        
    def connect(self) -> bool:
        """Connect to the Unicorn Hybrid Black device"""
        try:
            success = self.unicorn.connect()
            self.connected = success
            return success
        except Exception as e:
            print(f"Failed to connect to Unicorn device: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from the Unicorn device"""
        if self.connected:
            self.unicorn.disconnect()
            self.connected = False
            return True
        return False
    
    def get_bandpowers(self) -> Optional[Dict[str, float]]:
        """
        Get the current bandpower values from the device.
        Returns a dictionary with delta, theta, alpha, beta, gamma bands.
        """
        if not self.connected:
            return None
            
        # Get raw EEG data from the device
        # 1 second of data at 250 Hz sampling rate
        try:
            eeg_data = self.unicorn.get_data(250)  
            
            # Calculate band powers using FFT (simplified for hackathon)
            bandpowers = {
                'delta': float(np.mean(self._extract_band(eeg_data, 1, 4))),
                'theta': float(np.mean(self._extract_band(eeg_data, 4, 8))),
                'alpha': float(np.mean(self._extract_band(eeg_data, 8, 13))),
                'beta': float(np.mean(self._extract_band(eeg_data, 13, 30))),
                'gamma': float(np.mean(self._extract_band(eeg_data, 30, 50)))
            }
            
            self.last_bandpowers = bandpowers
            return bandpowers
        except Exception as e:
            print(f"Error getting bandpowers: {e}")
            return None
    
    def _extract_band(self, data: np.ndarray, low_freq: float, high_freq: float) -> np.ndarray:
        """
        Extract frequency band from EEG data using FFT.
        This is a simplified version for the hackathon.
        
        Args:
            data: Raw EEG data, shape (channels, samples)
            low_freq: Lower frequency bound
            high_freq: Upper frequency bound
            
        Returns:
            Band power for each channel
        """
        # In a real implementation, you would use proper signal processing
        # with windowing, overlapping, etc.
        
        # For the hackathon, simulate frequency content
        channels, samples = data.shape
        freqs = np.fft.rfftfreq(samples, 1.0/self.unicorn.sample_rate)
        
        # FFT for each channel
        ffts = np.abs(np.fft.rfft(data, axis=1))**2
        
        # Extract the specified band
        band_mask = (freqs >= low_freq) & (freqs <= high_freq)
        
        # Mean power in the band for each channel
        band_powers = np.mean(ffts[:, band_mask], axis=1)
        
        return band_powers
    
    def get_focus_level(self) -> float:
        """
        Calculate focus level based on EEG data.
        Returns a value between 0 and 1.
        """
        if not self.last_bandpowers:
            self.get_bandpowers()
            
        if not self.last_bandpowers:
            return 0.0
        
        # Calculate focus level based on beta/theta ratio
        # High beta and low theta indicates focus/concentration
        bp = self.last_bandpowers
        focus = bp['beta'] / (bp['theta'] + 0.01)  # Avoid division by zero
        
        # Normalize to 0-1 range with sigmoid function
        normalized_focus = 1.0 / (1.0 + np.exp(-0.5 * (focus - 5.0)))
        
        # Add to history for smoothing
        self.focus_history.append(normalized_focus)
        if len(self.focus_history) > self.max_history:
            self.focus_history.pop(0)
        
        # Return smoothed value
        smoothed_focus = float(np.mean(self.focus_history))
        return smoothed_focus
    
    def is_focused(self) -> bool:
        """Check if the user is currently focused based on EEG data"""
        focus_level = self.get_focus_level()
        return focus_level >= self.focus_threshold
    
    def is_making_selection(self) -> bool:
        """
        Check if the user is making a selection action.
        This could be a strong focus spike or a specific pattern.
        """
        focus_level = self.get_focus_level()
        
        # For selection, we want a higher threshold
        return focus_level >= self.selection_threshold
        
    async def continuous_monitoring(self, callback: Callable[[Dict[str, Any]], Any]):
        """
        Continuously monitor BCI data and call the callback 
        when important events happen.
        """
        while self.connected:
            bandpowers = self.get_bandpowers()
            focus_level = self.get_focus_level()
            is_focused = self.is_focused()
            is_selecting = self.is_making_selection()
            
            await callback({
                'bandpowers': bandpowers,
                'focus_level': focus_level,
                'is_focused': is_focused,
                'is_selecting': is_selecting
            })
            
            await asyncio.sleep(0.2)  # 5 updates per second