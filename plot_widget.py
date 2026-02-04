"""
Plot Widget - Real-time plotting with pyqtgraph
"""
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from collections import deque
from typing import Dict, Tuple


# Color palette for different trackers
TRACKER_COLORS = [
    (66, 133, 244),    # Blue
    (234, 67, 53),     # Red
    (251, 188, 5),     # Yellow
    (52, 168, 83),     # Green
    (155, 89, 182),    # Purple
    (230, 126, 34),    # Orange
    (26, 188, 156),    # Teal
    (241, 196, 15),    # Gold
]


class TrackerPlotWidget(QWidget):
    """Widget displaying real-time plots for a single tracker"""
    
    def __init__(self, serial: str, color: Tuple[int, int, int], 
                 max_samples: int = 500, parent=None):
        super().__init__(parent)
        self.serial = serial
        self.color = color
        self.max_samples = max_samples
        
        # Allow expanding horizontally, minimum height
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(100) # Allow shrinking
        
        # Data buffers
        self.time_data = deque(maxlen=max_samples)
        self.x_data = deque(maxlen=max_samples)
        self.y_data = deque(maxlen=max_samples)
        self.z_data = deque(maxlen=max_samples)
        
        self.rx_data = deque(maxlen=max_samples)
        self.ry_data = deque(maxlen=max_samples)
        self.rz_data = deque(maxlen=max_samples)
        
        self.start_time = None
        self.is_enabled = False  # Default to hidden
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 15)
        layout.setSpacing(5)
        
        # Header layout
        header_layout = QHBoxLayout()
        
        # Tracker label with color indicator
        self.label = QLabel(f"● {self.serial}")
        self.label.setStyleSheet(f"color: rgb{self.color}; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.label)
        
        # Loss rate label
        self.loss_label = QLabel("Loss: 0.0%")
        self.loss_label.setStyleSheet("color: #ffaa00; font-weight: bold; margin-left: 10px;")
        header_layout.addWidget(self.loss_label)
        
        header_layout.addStretch()
        
        # Stats labels
        self.stats_label = QLabel("σx: --  σy: --  σz: --")
        self.stats_label.setStyleSheet("color: #aaa; font-family: monospace; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # --- Dual Axis Plot (Position & Rotation) ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.setMinimumHeight(300)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        
        # Left Axis (Position)
        self.plot_widget.setLabel('left', 'Position', units='m')
        
        # Rotation ViewBox (Right Axis)
        self.rot_view = pg.ViewBox()
        self.plot_widget.scene().addItem(self.rot_view)
        self.plot_widget.getAxis('right').linkToView(self.rot_view)
        self.rot_view.setXLink(self.plot_widget)
        self.plot_widget.setLabel('right', 'Rotation', units='deg')
        self.plot_widget.showAxis('right')
        # Enable auto-range for Y-axis of rotation
        self.rot_view.enableAutoRange(axis=pg.ViewBox.YAxis)
        # Disable interactivity
        self.rot_view.setMouseEnabled(x=False, y=False)
        # Ensure it's rendered on top of grid if needed, though usually curves handle Z
        self.rot_view.setZValue(10) 
        
        # Connect resize signal
        self.plot_widget.getViewBox().sigResized.connect(self._update_views)
        
        # Curves - Position (Solid lines)
        pen_width = 2
        self.x_curve = self.plot_widget.plot(pen=pg.mkPen(color=(255, 100, 100), width=pen_width), name='X')
        self.y_curve = self.plot_widget.plot(pen=pg.mkPen(color=(100, 255, 100), width=pen_width), name='Y')
        self.z_curve = self.plot_widget.plot(pen=pg.mkPen(color=(100, 100, 255), width=pen_width), name='Z')
        
        # Curves - Rotation (Dashed lines, on Right Axis/ViewBox)
        # Note: addItem to rot_view, not plot_widget directly
        dash_pen = Qt.DashLine
        self.rx_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 50, 50), width=1, style=dash_pen), name='Pitch')
        self.ry_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(50, 255, 50), width=1, style=dash_pen), name='Yaw')
        self.rz_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(50, 50, 255), width=1, style=dash_pen), name='Roll')
        
        self.rot_view.addItem(self.rx_curve)
        self.rot_view.addItem(self.ry_curve)
        self.rot_view.addItem(self.rz_curve)
        
        # Manually add RPY to legend
        self.legend.addItem(self.rx_curve, 'Pitch')
        self.legend.addItem(self.ry_curve, 'Yaw')
        self.legend.addItem(self.rz_curve, 'Roll')

        layout.addWidget(self.plot_widget)
    
    def _update_views(self):
        """Sync rotation view geometry with main view"""
        self.rot_view.setGeometry(self.plot_widget.getViewBox().sceneBoundingRect())
        self.rot_view.linkedViewChanged(self.plot_widget.getViewBox(), self.rot_view.XAxis) 
    
    def resizeEvent(self, event):
        """Handle resize to force view update"""
        super().resizeEvent(event)
        self._update_views()

    def add_sample(self, timestamp: float, position: np.ndarray, rotation: np.ndarray = None):
        """Add a new sample to the plot"""
        if self.start_time is None:
            self.start_time = timestamp
        
        relative_time = timestamp - self.start_time
        
        self.time_data.append(relative_time)
        self.x_data.append(position[0])
        self.y_data.append(position[1])
        self.z_data.append(position[2])
        
        if rotation is not None:
            self.rx_data.append(rotation[0])
            self.ry_data.append(rotation[1])
            self.rz_data.append(rotation[2])
        else:
            self.rx_data.append(0)
            self.ry_data.append(0)
            self.rz_data.append(0)
    
    def update_plot(self):
        """Update the plot display"""
        if len(self.time_data) < 2:
            return
        
        time_array = np.array(self.time_data)
        self.x_curve.setData(time_array, np.array(self.x_data))
        self.y_curve.setData(time_array, np.array(self.y_data))
        self.z_curve.setData(time_array, np.array(self.z_data))
        
        self.rx_curve.setData(time_array, np.array(self.rx_data))
        self.ry_curve.setData(time_array, np.array(self.ry_data))
        self.rz_curve.setData(time_array, np.array(self.rz_data))
    
    def update_stats(self, sigma_x: float, sigma_y: float, sigma_z: float):
        """Update the statistics display"""
        current_text = self.stats_label.text()
        extra_info = ""
        if "  |  " in current_text:
            extra_info = "  |  " + current_text.split("  |  ")[1]
            
        self.stats_label.setText(
            f"σx: {sigma_x:.5f}  σy: {sigma_y:.5f}  σz: {sigma_z:.5f}{extra_info}"
        )
    
    def clear_data(self):
        """Clear all data"""
        self.time_data.clear()
        self.x_data.clear()
        self.y_data.clear()
        self.z_data.clear()
        self.rx_data.clear()
        self.ry_data.clear()
        self.rz_data.clear()
        self.start_time = None
        
        self.x_curve.setData([], [])
        self.y_curve.setData([], [])
        self.z_curve.setData([], [])
        self.rx_curve.setData([], [])
        self.ry_curve.setData([], [])
        self.rz_curve.setData([], [])
        
        self.stats_label.setText("σx: --  σy: --  σz: --")
    
    def set_enabled(self, enabled: bool):
        """Set the enabled state of the widget"""
        self.is_enabled = enabled
        if self.is_enabled:
            self.label.setStyleSheet(f"color: rgb{self.color}; font-weight: bold; font-size: 14px;")
        else:
            self.label.setStyleSheet(f"color: #555; font-weight: bold; font-size: 14px;")

    def update_loss_rate(self, loss_rate: float):
        """Update loss rate display"""
        self.loss_label.setText(f"Loss: {loss_rate*100:.1f}%")
        if loss_rate > 0.01: # Highlight if > 1%
             self.loss_label.setStyleSheet("color: #ff5555; font-weight: bold; margin-left: 10px;")
        else:
             self.loss_label.setStyleSheet("color: #ffaa00; font-weight: bold; margin-left: 10px;")


def get_tracker_color(index: int) -> Tuple[int, int, int]:
    """Get a color for a tracker by index"""
    return TRACKER_COLORS[index % len(TRACKER_COLORS)]
