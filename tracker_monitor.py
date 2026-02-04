"""
OpenVR Tracker Monitor - Acquires tracker positions from SteamVR
"""
import openvr
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TrackerData:
    """Data container for a single tracker"""
    serial: str
    device_index: int
    position: np.ndarray  # [x, y, z]
    rotation: np.ndarray  # [pitch, yaw, roll] in degrees
    is_valid: bool
    device_class: int = 0


class TrackerMonitor:
    """Monitors SteamVR trackers and retrieves their positions"""
    
    def __init__(self):
        self.vr_system: Optional[openvr.IVRSystem] = None
        self.is_initialized = False
        self._tracker_indices: List[int] = []
        self._tracker_serials: Dict[int, str] = {}
    
    def initialize(self) -> bool:
        """Initialize OpenVR connection"""
        try:
            self.vr_system = openvr.init(openvr.VRApplication_Other)
            self.is_initialized = True
            self._discover_trackers()
            return True
        except openvr.OpenVRError as e:
            print(f"Failed to initialize OpenVR: {e}")
            return False
    
    def shutdown(self):
        """Shutdown OpenVR connection"""
        if self.is_initialized:
            openvr.shutdown()
            self.is_initialized = False
            self.vr_system = None
    
    def _discover_trackers(self):
        """Find all connected trackers and controllers"""
        self._tracker_indices.clear()
        self._tracker_serials.clear()
        
        if not self.vr_system:
            return
        
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            device_class = self.vr_system.getTrackedDeviceClass(i)
            # Include trackers, controllers, and base stations
            if device_class in (openvr.TrackedDeviceClass_GenericTracker, 
                               openvr.TrackedDeviceClass_Controller,
                               openvr.TrackedDeviceClass_TrackingReference):
                self._tracker_indices.append(i)
                serial = self._get_device_serial(i)
                # Add prefix to distinguish type
                if device_class == openvr.TrackedDeviceClass_Controller:
                    serial = f"[Controller] {serial}"
                elif device_class == openvr.TrackedDeviceClass_TrackingReference:
                    serial = f"[BaseStation] {serial}"
                else:
                    serial = f"[Tracker] {serial}"
                self._tracker_serials[i] = serial
    
    def _get_device_serial(self, device_index: int) -> str:
        """Get the serial number of a device"""
        if not self.vr_system:
            return f"Unknown_{device_index}"
        
        try:
            serial = self.vr_system.getStringTrackedDeviceProperty(
                device_index,
                openvr.Prop_SerialNumber_String
            )
            return serial
        except:
            return f"Unknown_{device_index}"
    
    def get_tracker_count(self) -> int:
        """Return the number of connected trackers"""
        return len(self._tracker_indices)
    
    def get_tracker_serials(self) -> Dict[int, str]:
        """Return mapping of device index to serial number"""
        return self._tracker_serials.copy()
    
    def refresh_trackers(self):
        """Refresh the list of connected trackers"""
        self._discover_trackers()
    
    def get_all_tracker_positions(self) -> List[TrackerData]:
        """Get positions of all connected trackers"""
        results = []
        
        if not self.is_initialized or not self.vr_system:
            return results
        
        # Get poses for all devices
        poses = self.vr_system.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding,
            0,  # Predicted seconds from now
            openvr.k_unMaxTrackedDeviceCount
        )
        
        for device_index in self._tracker_indices:
            pose = poses[device_index]
            is_valid = pose.bPoseIsValid
            
            if is_valid:
                # Extract position from 3x4 matrix
                matrix = pose.mDeviceToAbsoluteTracking
                position = np.array([
                    matrix[0][3],  # x
                    matrix[1][3],  # y
                    matrix[2][3],  # z
                ])
                
                # Extract rotation (Euler angles)
                # Yaw, Pitch, Roll conversion from 3x3 rotation matrix
                # R = [ [r00, r01, r02],
                #       [r10, r11, r12],
                #       [r20, r21, r22] ]
                r00 = matrix[0][0]
                r10 = matrix[1][0]
                r20 = matrix[2][0]
                r21 = matrix[2][1]
                r22 = matrix[2][2]
                
                # Calculation (assuming standard OpenGL-ish coordinates, Y-up)
                # Pitch (X-axis rotation)
                pitch = np.arctan2(r21, r22)
                # Yaw (Y-axis rotation)
                yaw = np.arcsin(-r20)
                # Roll (Z-axis rotation)
                roll = np.arctan2(r10, r00)
                
                rotation = np.degrees(np.array([pitch, yaw, roll]))
                
            else:
                position = np.array([0.0, 0.0, 0.0])
                rotation = np.array([0.0, 0.0, 0.0])
            
            results.append(TrackerData(
                serial=self._tracker_serials.get(device_index, f"Unknown_{device_index}"),
                device_index=device_index,
                position=position,
                rotation=rotation,
                is_valid=is_valid,
                device_class=self.vr_system.getTrackedDeviceClass(device_index)
            ))
        
        return results

    def poll_events(self) -> bool:
        """
        Poll OpenVR events to detect device changes.
        Returns True if device list changed.
        """
        if not self.vr_system:
            return False
            
        event = openvr.VREvent_t()
        has_changes = False
        
        # Process all pending events
        while self.vr_system.pollNextEvent(event):
            if event.eventType in (openvr.VREvent_TrackedDeviceActivated, 
                                 openvr.VREvent_TrackedDeviceDeactivated):
                has_changes = True
                
        if has_changes:
            self._discover_trackers()
            return True
            
        return False


if __name__ == "__main__":
    # Test the monitor
    monitor = TrackerMonitor()
    if monitor.initialize():
        print(f"Connected to SteamVR")
        print(f"Found {monitor.get_tracker_count()} tracker(s)")
        print(f"Serials: {monitor.get_tracker_serials()}")
        
        # Get one sample
        positions = monitor.get_all_tracker_positions()
        for tracker in positions:
            print(f"{tracker.serial}: {tracker.position} (valid: {tracker.is_valid})")
        
        monitor.shutdown()
    else:
        print("Failed to connect to SteamVR")
