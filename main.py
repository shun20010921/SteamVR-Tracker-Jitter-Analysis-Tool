"""
SteamVR Tracker Jitter Analysis Tool
Real-time visualization and analysis of tracker position jitter

Usage: python main.py
"""
import sys
import time
import numpy as np
import openvr
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QMessageBox, QFileDialog,
    QFrame, QSplitter, QCheckBox, QListWidget, QListWidgetItem,
    QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QColor

from tracker_monitor import TrackerMonitor
from stats_calculator import StatsCalculator
from plot_widget import TrackerPlotWidget, get_tracker_color
from bs_plot_widget import BaseStationPlotWidget
from csv_exporter import CSVExporter

WINDOW_TITLE = "SteamVR Tracker Jitter Analysis Tool"
WINDOW_SIZE = (1000, 800)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(*WINDOW_SIZE)
        
        # Components
        self.tracker_monitor = TrackerMonitor()
        self.stats_calculator = StatsCalculator(window_size=100)
        self.csv_exporter = CSVExporter()
        
        # State
        self.is_measuring = False
        self.tracker_widgets: dict[str, TrackerPlotWidget] = {}
        self.bs_widgets = {} # Store BS widgets separately
        self.sample_rate = 90  # Hz (SteamVR typically runs at 90Hz)
        self.plot_update_interval = 3  # Update plots every N frames (30Hz)
        self.plot_update_counter = 0
        self.device_list_items = {} # Map serial -> QListWidgetItem
        
        # Timer for data acquisition
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._on_timer_tick)
        
        self._setup_ui()
        self._apply_dark_theme()
    
    def _setup_ui(self):
        """Setup the UI components"""
        # Main layout container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Top Control Bar ---
        control_layout = QHBoxLayout()
        
        # Connect Button
        self.connect_btn = QPushButton("Connect to SteamVR")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.connect_btn.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #555; color: #aaa; }
        """)
        control_layout.addWidget(self.connect_btn)
        
        # Status Label
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #aaa; margin-left: 10px;")
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        # Measurement Controls
        self.start_btn = QPushButton("Start Measurement")
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #F44336; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #D32F2F; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addSpacing(20)
        
        # Save Button
        self.save_btn = QPushButton("Save CSV")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setEnabled(False) # Enabled after stop if data exists
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #FF9800; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        control_layout.addWidget(self.save_btn)
        
        control_layout.addSpacing(10)

        self.clear_btn = QPushButton("Clear Data")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setStyleSheet("""
            QPushButton { background-color: #607D8B; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #546E7A; }
        """)
        control_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(control_layout)
        
        # --- Splitter (Sidebar + Main Content) ---
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel (Device List)
        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 5px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        list_header = QLabel("Detected Devices")
        list_header.setStyleSheet("font-weight: bold; padding: 5px; color: #ddd;")
        left_layout.addWidget(list_header)
        
        self.device_list_widget = QListWidget()
        self.device_list_widget.setStyleSheet("QListWidget { background-color: #252525; border: 1px solid #444; color: #fff; } QListWidget::item { padding: 5px; } QListWidget::item:hover { background-color: #333; }")
        # Connect signal to handler
        self.device_list_widget.itemChanged.connect(self._on_device_list_changed)
        left_layout.addWidget(self.device_list_widget)
        
        self.tracker_count_label = QLabel("Devices: 0")
        self.tracker_count_label.setStyleSheet("color: #888; padding: 5px;")
        left_layout.addWidget(self.tracker_count_label)
        
        splitter.addWidget(left_panel)
        
        # Right Panel (Scroll Area for Graphs)
        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background-color: #121212; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setAlignment(Qt.AlignTop)
        self.plots_layout.setSpacing(20)
        
        self.no_tracker_label = QLabel("Ready to Connect.\nClick 'Connect to SteamVR' to start discovery.")
        self.no_tracker_label.setAlignment(Qt.AlignCenter)
        self.no_tracker_label.setStyleSheet("color: #666; font-size: 18px; margin-top: 50px;")
        self.plots_layout.addWidget(self.no_tracker_label)
        
        # Layout for Trackers
        self.trackers_layout = QGridLayout()
        self.trackers_layout.setSpacing(10)
        self.trackers_layout.setColumnStretch(0, 1)
        self.trackers_layout.setColumnStretch(1, 1)
        self.plots_layout.addLayout(self.trackers_layout)
        
        # BS Section Header
        self.bs_header = QLabel("Base Station Monitor")
        self.bs_header.setStyleSheet("color: #888; font-weight: bold; font-size: 16px; margin-top: 20px; border-bottom: 1px solid #444;")
        self.bs_header.hide() # Hide initially
        self.plots_layout.addWidget(self.bs_header)
        
        # Layout for Base Stations
        self.bs_layout = QGridLayout()
        self.bs_layout.setSpacing(10)
        self.bs_layout.setColumnStretch(0, 1)
        self.bs_layout.setColumnStretch(1, 1)
        self.plots_layout.addLayout(self.bs_layout)
        
        self.scroll_area.setWidget(self.plots_container)
        right_layout.addWidget(self.scroll_area)
        
        # Sample Count
        self.sample_count_label = QLabel("Samples: 0")
        self.sample_count_label.setAlignment(Qt.AlignRight)
        self.sample_count_label.setStyleSheet("color: #888; margin-top: 5px; margin-right: 10px;")
        right_layout.addWidget(self.sample_count_label)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 4) # Main content larger
        splitter.setSizes([250, 750]) # Set initial exact sizes
        
        main_layout.addWidget(splitter)
    
    def _apply_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px 16px;
                color: #fff;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #555;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #555;
                border-color: #333;
            }
            QScrollArea {
                background-color: #121212;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #444;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555;
            }
        """)
    
    def _on_connect_clicked(self):
        """Handle connect button click"""
        if self.tracker_monitor.is_initialized:
            # Disconnect
            self.tracker_monitor.shutdown()
            self._update_connection_status(False)
            self.connect_btn.setText("Connect to SteamVR")
        else:
            # Connect
            if self.tracker_monitor.initialize():
                self._update_connection_status(True)
                self.connect_btn.setText("Disconnect")
                self._update_tracker_widgets(clear_all=True)
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Failed",
                    "Failed to connect to SteamVR.\n"
                    "Please make sure SteamVR is running."
                )
    
    def _update_connection_status(self, connected: bool):
        """Update UI based on connection status"""
        if connected:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: #55ff55; margin-left: 10px;")
            self.start_btn.setEnabled(True)
        else:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: #aaa; margin-left: 10px;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def _on_device_list_changed(self, item):
        """Handle toggle of device in list"""
        # Repopulate using the new state
        self._update_tracker_widgets(clear_all=False)

    def _update_tracker_widgets(self, clear_all=False):
        """Update plot widgets for tracked devices dynamically"""
        if clear_all:
            for widget in self.tracker_widgets.values():
                widget.deleteLater()
            self.tracker_widgets.clear()
            for widget in self.bs_widgets.values():
                widget.deleteLater()
            self.bs_widgets.clear()
            self.device_list_widget.clear()
            self.device_list_items.clear()
        
        # Get tracker list
        tracker_serials = self.tracker_monitor.get_tracker_serials()
        
        visible_widgets = []
        bs_widgets_list = []
        
        # 1. Update/Create Widgets and List Items
        for device_idx, serial in tracker_serials.items():
            is_bs = "[BaseStation]" in serial
            
            # --- Base Station Handling ---
            if is_bs:
                if serial not in self.bs_widgets:
                    # Add new BS widget
                    bs_idx = len(self.bs_widgets)
                    color = (200, 200, 200)
                    if bs_idx == 0: color = (200, 200, 50)
                    elif bs_idx == 1: color = (50, 200, 200)
                    elif bs_idx == 2: color = (200, 50, 200)
                    
                    widget = BaseStationPlotWidget(serial, color)
                    self.bs_widgets[serial] = widget
                
                bs_widgets_list.append(self.bs_widgets[serial])
                continue

            # --- Tracker/Controller Handling ---
            
            # Ensure List Item Exists
            if serial not in self.device_list_items:
                item = QListWidgetItem(serial)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.device_list_widget.addItem(item)
                self.device_list_items[serial] = item
            
            item = self.device_list_items[serial]
            should_show = (item.checkState() == Qt.Checked)

            if serial not in self.tracker_widgets:
                # Add new widget
                color_idx = len(self.tracker_widgets)
                color = get_tracker_color(color_idx)
                widget = TrackerPlotWidget(serial, color)
                # Enable state is now handled by set_enabled, driven by list check state
                self.tracker_widgets[serial] = widget
            
            widget = self.tracker_widgets[serial]
            
            # Update Enabled State from List Item
            widget.set_enabled(should_show)
            
            # We show widgets if they are enabled.
            # (or we could show them but grayed out? User said "ON/OFF" there, implying visibility toggle)
            # "Grid Packing" implies hidden if disabled.
            if should_show:
                visible_widgets.append(widget)
        
        # Sort widgets (Enabled ones) by serial
        visible_widgets.sort(key=lambda w: w.serial)
        
        # 2. Start Repopulating Layouts
        # Clear existing items from layouts (detach widgets)
        def clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None) # Detach
        
        clear_layout(self.bs_layout)
        clear_layout(self.trackers_layout)
        
        # Repopulate BS Grid
        for i, widget in enumerate(bs_widgets_list):
            self.bs_layout.addWidget(widget, i // 2, i % 2)
            widget.show()
            
        # Repopulate Tracker Grid
        for i, widget in enumerate(visible_widgets):
            self.trackers_layout.addWidget(widget, i // 2, i % 2)
            widget.show()
            
        # 3. Update Status Labels
        if visible_widgets:
            self.no_tracker_label.hide()
        elif not bs_widgets_list and not visible_widgets:
             self.no_tracker_label.setText(
                "No visible devices.\n"
                "Enable devices in the list to view."
            )
             self.no_tracker_label.show()
        
        # BS Header Visibility
        if bs_widgets_list:
            self.bs_header.show()
        else:
            self.bs_header.hide()
            
        self.tracker_count_label.setText(f"Devices: {len(visible_widgets)}")
    
    def _on_start_clicked(self):
        """Start measurement"""
        self.is_measuring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)
        
        # Clear previous data
        self.stats_calculator.clear()
        for widget in self.tracker_widgets.values():
            widget.clear_data()
        for widget in self.bs_widgets.values():
            widget.clear_data()
        
        # Start timer (approximately 90 Hz)
        self.update_timer.start(int(1000 / self.sample_rate))
    
    def _on_stop_clicked(self):
        """Stop measurement"""
        self.is_measuring = False
        self.update_timer.stop()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.save_btn.setEnabled(self.csv_exporter.get_sample_count() > 0)
        self.connect_btn.setEnabled(True)
    
    def _on_save_clicked(self):
        """Save data to CSV"""
        if self.csv_exporter.get_sample_count() == 0:
            QMessageBox.information(self, "No Data", "No data to save.")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV",
            f"tracker_jitter_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            saved_path = self.csv_exporter.save(filename=filepath)
            QMessageBox.information(
                self, 
                "Saved",
                f"Data saved to:\n{saved_path}\n\n"
                f"Total samples: {self.csv_exporter.get_sample_count()}"
            )
    
    def _on_clear_clicked(self):
        """Clear all data"""
        self.stats_calculator.clear()
        self.csv_exporter.clear()
        for widget in self.tracker_widgets.values():
            widget.clear_data()
        for widget in self.bs_widgets.values():
             widget.clear_data()
        self.sample_count_label.setText("Samples: 0")
        self.save_btn.setEnabled(False)
    
    def _on_timer_tick(self):
        """Update function called by timer"""
        if not self.tracker_monitor.is_initialized:
            return
            
        # Check for new devices/events
        if self.tracker_monitor.poll_events():
            self._update_tracker_widgets(clear_all=False)
            
        # Get current timestamp
        current_time = time.time()
        
        # Get tracker positions
        tracker_data = self.tracker_monitor.get_all_tracker_positions()
        
        # Separate BS and other devices
        base_stations = []
        trackable_devices = []
        
        for data in tracker_data:
            if not data.is_valid:
                continue
            
            # Identify device type by string prefix (simple way since we added it in tracker_monitor)
            # Better way: use device_class from TrackerData
            if data.device_class == openvr.TrackedDeviceClass_TrackingReference:
                base_stations.append(data)
            else:
                trackable_devices.append(data)
        
        # Process Base Stations (Monitor their position)
        for data in base_stations:
            serial = data.serial
            # Check validity? Assuming BS position is always valid if connected, but good to check.
            if not data.is_valid:
                continue
                
            position = data.position
             # Add to stats calculator
            self.stats_calculator.add_sample(serial, position)
            
            if serial in self.bs_widgets:
                widget = self.bs_widgets[serial]
                widget.add_sample(current_time, position)
                
                # Throttle plot updates
                if self.plot_update_counter % self.plot_update_interval == 0:
                    widget.update_plot()
                    std_dev = self.stats_calculator.get_std_dev(serial)
                    widget.update_stats(std_dev[0], std_dev[1], std_dev[2])

        # Process trackable devices
        for data in trackable_devices:
            serial = data.serial
            
            # Record frame statistics for loss rate
            self.stats_calculator.record_frame(serial, data.is_valid)
            
            # Update loss rate in UI (do this even if invalid)
            # Throttle loss rate updates too, but maybe less aggressively? 
            # Consistent throttling is fine.
            if serial in self.tracker_widgets:
                widget = self.tracker_widgets[serial]
                if self.plot_update_counter % self.plot_update_interval == 0:
                    loss_rate = self.stats_calculator.get_loss_rate(serial)
                    widget.update_loss_rate(loss_rate)

            if not data.is_valid:
                continue
            
            position = data.position
            rotation = data.rotation
            
            # Add to stats calculator
            self.stats_calculator.add_sample(serial, position)
            
            # Get current stats
            std_dev = self.stats_calculator.get_std_dev(serial)
            
            # Add to CSV exporter (ALWAYS save, regardless of visibility)
            self.csv_exporter.add_sample(
                timestamp=current_time,
                serial=serial,
                position=(position[0], position[1], position[2]),
                rotation=(rotation[0], rotation[1], rotation[2]),
                std_dev=std_dev
            )
            
            # Check if tracker is enabled in UI
            if serial in self.tracker_widgets:
                widget = self.tracker_widgets[serial]
                
                # Skip plot update if disabled or filter hidden
                if not widget.isVisible() or not widget.is_enabled:
                    continue
                
                # Always add sample to internal buffer
                widget.add_sample(current_time, position, rotation)
                
                # Throttle plot refresh
                if self.plot_update_counter % self.plot_update_interval == 0:
                    widget.update_plot()
                    widget.update_stats(std_dev[0], std_dev[1], std_dev[2])
        
        self.plot_update_counter += 1
        
        # Update sample count (also can be throttled)
        if self.plot_update_counter % self.sample_rate == 0: # 1Hz
             self.sample_count_label.setText(f"Samples: {self.csv_exporter.get_sample_count()}")
    
    def closeEvent(self, event):
        """Handle window close"""
        self.update_timer.stop()
        if self.tracker_monitor.is_initialized:
            self.tracker_monitor.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
