"""
CSV Exporter - Exports tracker data for MATLAB analysis
"""
import csv
import os
from datetime import datetime
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class TrackerSample:
    """A single sample of tracker data"""
    timestamp: float
    serial: str
    x: float
    y: float
    z: float
    rot_pitch: float
    rot_yaw: float
    rot_roll: float
    sigma_x: float
    sigma_y: float
    sigma_z: float


class CSVExporter:
    """Exports tracker data to CSV format"""
    
    def __init__(self):
        self._samples: List[TrackerSample] = []
    
    def add_sample(self, timestamp: float, serial: str, 
                   position: Tuple[float, float, float],
                   rotation: Tuple[float, float, float],
                   std_dev: Tuple[float, float, float]):
        """Add a sample to the export buffer"""
        sample = TrackerSample(
            timestamp=timestamp,
            serial=serial,
            x=position[0],
            y=position[1],
            z=position[2],
            rot_pitch=rotation[0],
            rot_yaw=rotation[1],
            rot_roll=rotation[2],
            sigma_x=std_dev[0],
            sigma_y=std_dev[1],
            sigma_z=std_dev[2]
        )
        self._samples.append(sample)
    
    def get_sample_count(self) -> int:
        """Get the number of samples in buffer"""
        return len(self._samples)
    
    def clear(self):
        """Clear the sample buffer"""
        self._samples.clear()
    
    def save(self, directory: str = None, filename: str = None) -> str:
        """
        Save samples to CSV file
        Returns the path to the saved file
        """
        if directory is None:
            directory = os.getcwd()
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tracker_jitter_{timestamp}.csv"
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", 
                "Device Serial", 
                "Pos X", "Pos Y", "Pos Z", 
                "Rot Pitch", "Rot Yaw", "Rot Roll",
                "Sigma X", "Sigma Y", "Sigma Z"
            ])
            # Data
            for sample in self._samples:
                writer.writerow([
                    f"{sample.timestamp:.6f}",
                    sample.serial,
                    f"{sample.x:.6f}",
                    f"{sample.y:.6f}",
                    f"{sample.z:.6f}",
                    f"{sample.rot_pitch:.6f}",
                    f"{sample.rot_yaw:.6f}",
                    f"{sample.rot_roll:.6f}",
                    f"{sample.sigma_x:.6f}",
                    f"{sample.sigma_y:.6f}",
                    f"{sample.sigma_z:.6f}"
                ])
        
        return filepath


if __name__ == "__main__":
    # Test the exporter
    import time
    
    exporter = CSVExporter()
    
    # Add some test samples
    base_time = time.time()
    for i in range(10):
        exporter.add_sample(
            timestamp=base_time + i * 0.01,
            serial="test_tracker",
            position=(1.0 + i * 0.001, 1.5, 0.5),
            std_dev=(0.001, 0.002, 0.0015)
        )
    
    filepath = exporter.save()
    print(f"Saved {exporter.get_sample_count()} samples to: {filepath}")
