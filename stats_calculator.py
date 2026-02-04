"""
Statistics Calculator - Computes real-time jitter statistics
"""
import numpy as np
from typing import Dict, Tuple
from collections import deque


class StatsCalculator:
    """Calculates rolling statistics for tracker positions"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        # Store position history per tracker: {serial: deque of [x, y, z]}
        self._history: Dict[str, deque] = {}
        # Tracking loss stats
        self._total_frames: Dict[str, int] = {}
        self._lost_frames: Dict[str, int] = {}
    
    def add_sample(self, serial: str, position: np.ndarray):
        """Add a new position sample for a tracker"""
        if serial not in self._history:
            self._history[serial] = deque(maxlen=self.window_size)
        
        self._history[serial].append(position.copy())
    
    def record_frame(self, serial: str, is_valid: bool):
        """Record a frame status (valid or lost)"""
        if serial not in self._total_frames:
            self._total_frames[serial] = 0
            self._lost_frames[serial] = 0
            
        self._total_frames[serial] += 1
        if not is_valid:
            self._lost_frames[serial] += 1
            
    def get_loss_rate(self, serial: str) -> float:
        """Get tracking loss rate (0.0 to 1.0)"""
        if serial not in self._total_frames or self._total_frames[serial] == 0:
            return 0.0
        return self._lost_frames[serial] / self._total_frames[serial]
    
    def get_std_dev(self, serial: str) -> Tuple[float, float, float]:
        """
        Get standard deviation for x, y, z axes
        Returns (σx, σy, σz)
        """
        if serial not in self._history or len(self._history[serial]) < 2:
            return (0.0, 0.0, 0.0)
        
        data = np.array(self._history[serial])
        std = np.std(data, axis=0)
        return (std[0], std[1], std[2])
    
    def get_distance_std(self, serial: str) -> float:
        """
        Get standard deviation of 3D distance from mean position
        """
        if serial not in self._history or len(self._history[serial]) < 2:
            return 0.0
        
        data = np.array(self._history[serial])
        mean_pos = np.mean(data, axis=0)
        distances = np.linalg.norm(data - mean_pos, axis=1)
        return float(np.std(distances))
    
    def get_sample_count(self, serial: str) -> int:
        """Get the number of samples stored for a tracker"""
        if serial not in self._history:
            return 0
        return len(self._history[serial])
    
    def clear(self, serial: str = None):
        """Clear history for a specific tracker or all trackers"""
        if serial:
            if serial in self._history:
                self._history[serial].clear()
            if serial in self._total_frames:
                self._total_frames[serial] = 0
                self._lost_frames[serial] = 0
        else:
            self._history.clear()
            self._total_frames.clear()
            self._lost_frames.clear()
    
    def get_all_serials(self) -> list:
        """Get list of all tracked serials"""
        return list(self._history.keys())


if __name__ == "__main__":
    # Test the calculator
    calc = StatsCalculator(window_size=10)
    
    # Simulate some jittery data
    for i in range(20):
        pos = np.array([1.0 + np.random.normal(0, 0.01),
                        1.5 + np.random.normal(0, 0.02),
                        0.5 + np.random.normal(0, 0.015)])
        calc.add_sample("test_tracker", pos)
    
    std = calc.get_std_dev("test_tracker")
    print(f"Standard deviation: σx={std[0]:.6f}, σy={std[1]:.6f}, σz={std[2]:.6f}")
    print(f"Distance std: {calc.get_distance_std('test_tracker'):.6f}")
    print(f"Sample count: {calc.get_sample_count('test_tracker')}")
