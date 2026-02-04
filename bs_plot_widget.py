
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSizePolicy
from PyQt5.QtCore import Qt
from collections import deque
import pyqtgraph as pg
import numpy as np

BS_COLORS = [
    (200, 200, 50),   # Yellowish
    (50, 200, 200),   # Cyanish
    (200, 50, 200),   # Magentaish
    (150, 150, 150)   # Greyish
]

class BaseStationPlotWidget(QWidget):
    """Widget to detect and display Base Station movement (drift)"""
    
    def __init__(self, serial: str, color=(255, 255, 255), parent=None):
        super().__init__(parent)
        self.serial = serial
        self.color = color
        self.window_size = 30
        self.max_samples = 3000
        
        # Allow expanding horizontally
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(100)
        
        self.start_time = None
        self.initial_position = None
        self.drift_threshold = 0.005 # 5mm alarm threshold (adjustable?)
        
        # Data buffers
        self.time_data = deque(maxlen=self.max_samples)
        self.drift_data = deque(maxlen=self.max_samples)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 15)
        layout.setSpacing(5)
        
        # Header layout
        header_layout = QHBoxLayout()
        
        # Icon/Serial
        self.label = QLabel(f"📡 {self.serial}")
        self.label.setStyleSheet(f"color: rgb{self.color}; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.label)
        
        header_layout.addStretch()
        
        # Status Label
        self.status_label = QLabel("STATUS: CALIBRATING...")
        self.status_label.setStyleSheet("color: yellow; font-weight: bold; font-size: 12px; background-color: #333; padding: 4px; border-radius: 4px;")
        header_layout.addWidget(self.status_label)
        
        # Stats label (Drift Max)
        self.stats_label = QLabel("Drift: 0.00 mm")
        self.stats_label.setStyleSheet("color: #aaa; font-family: monospace; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Plot (Drift Only)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Drift', units='mm')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.setTitle("Displacement from Initial Position")
        self.plot_widget.setMinimumHeight(150)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        
        # Threshold line
        self.thresh_line = pg.InfiniteLine(pos=self.drift_threshold * 1000, angle=0, pen=pg.mkPen('r', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.thresh_line)
        
        # Curve
        self.drift_curve = self.plot_widget.plot(pen=pg.mkPen(color=(255, 100, 100), width=2), fillLevel=0, brush=(255, 100, 100, 50))
        
        layout.addWidget(self.plot_widget)

    def add_sample(self, timestamp: float, position: np.ndarray):
        if self.initial_position is None:
            self.initial_position = position
            self.status_label.setText("STATUS: STABLE")
            self.status_label.setStyleSheet("color: white; font-weight: bold; background-color: #2e7d32; padding: 4px; border-radius: 4px;")
        
        if self.start_time is None:
            self.start_time = timestamp
        
        relative_time = timestamp - self.start_time
        
        # Calculate drift (distance from initial position)
        distance = np.linalg.norm(position - self.initial_position)
        
        # Convert to mm for display/plot
        distance_mm = distance * 1000.0
        
        self.time_data.append(relative_time)
        self.drift_data.append(distance_mm)
        
        # Update Status
        if distance > self.drift_threshold:
            self.status_label.setText("⚠️ MOVEMENT DETECTED ⚠️")
            self.status_label.setStyleSheet("color: white; font-weight: bold; background-color: #c62828; padding: 4px; border-radius: 4px;")
        else:
            # Revert to stable if it returns? Or start latching? 
            # Ideally if it returns it's fine, if it stays displaced it's fine (new pos), 
            # but usually we want to know if it moved *at all*.
            # Let's keep it Red if currently displaced.
            if self.status_label.text() != "STATUS: STABLE":
                pass # E.g. user might want to reset?
                # For now simplify: Realtime Status
                # "Stable" if < threshold, "Moved" if > threshold
            pass # Keep logic simple for now

    
    def update_plot(self):
        if len(self.time_data) < 2:
            return
            
        time_array = np.array(self.time_data)
        drift_array = np.array(self.drift_data)
        
        self.drift_curve.setData(time_array, drift_array)
        
        # Update text
        current_drift = self.drift_data[-1] if self.drift_data else 0
        max_drift = np.max(drift_array)
        self.stats_label.setText(f"Curr: {current_drift:.2f}mm  Max: {max_drift:.2f}mm")
        
    def update_stats(self, sigma_x, sigma_y, sigma_z):
        # We overload this or ignore it.
        # Actually standard deviation is still useful info.
        # Let's append it to stats label?
        # Or simplistic view: User cares about MOVEMENT.
        pass

    def clear_data(self):
        """Reset data and drift baseline"""
        self.time_data.clear()
        self.drift_data.clear()
        self.start_time = None
        self.initial_position = None
        
        self.drift_curve.setData([], [])
        self.stats_label.setText("Drift: 0.00 mm")
        self.status_label.setText("STATUS: CALIBRATING...")
        self.status_label.setStyleSheet("color: yellow; font-weight: bold; font-size: 12px; background-color: #333; padding: 4px; border-radius: 4px;")
