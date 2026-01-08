"""
Telemetry Panel - pravý panel s telemetrií a grafy
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QTabWidget, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PyQt6.QtGui import QPainter
from loguru import logger
from collections import deque
import time

from ...config import Config


class BatteryWidget(QWidget):
    """Widget pro zobrazení baterie"""
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        
        # Procenta
        self.percentage_label = QLabel("85%")
        self.percentage_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #a6e3a1;")
        self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percentage_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(85)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #45475a;
                border-radius: 5px;
                background-color: #313244;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Detaily
        details_layout = QHBoxLayout()
        
        self.voltage_label = QLabel("12.0V")
        self.voltage_label.setStyleSheet("color: #bac2de;")
        details_layout.addWidget(self.voltage_label)
        
        details_layout.addStretch()
        
        self.current_label = QLabel("0.5A")
        self.current_label.setStyleSheet("color: #bac2de;")
        details_layout.addWidget(self.current_label)
        
        layout.addLayout(details_layout)
        
    def update_battery(self, percentage: float, voltage: float, current: float):
        """Aktualizuj data baterie"""
        self.percentage_label.setText(f"{int(percentage)}%")
        self.progress.setValue(int(percentage))
        self.voltage_label.setText(f"{voltage:.1f}V")
        self.current_label.setText(f"{current:.2f}A")
        
        # Změň barvu podle stavu
        if percentage < 20:
            color = "#f38ba8"  # červená
            self.percentage_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        elif percentage < 50:
            color = "#f9e2af"  # žlutá
            self.percentage_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        else:
            color = "#a6e3a1"  # zelená
            self.percentage_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")


class SpeedChartWidget(QWidget):
    """Widget s grafem rychlosti"""
    
    def __init__(self):
        super().__init__()
        
        self.data_linear = deque(maxlen=60)  # 60 sekund
        self.data_angular = deque(maxlen=60)
        self.timestamps = deque(maxlen=60)
        self.start_time = time.time()
        
        self._setup_chart()
        
    def _setup_chart(self):
        """Nastavení grafu"""
        layout = QVBoxLayout(self)
        
        # Vytvoř sérii
        self.series_linear = QLineSeries()
        self.series_linear.setName("Lineární")
        
        self.series_angular = QLineSeries()
        self.series_angular.setName("Angulární")
        
        # Vytvoř chart
        self.chart = QChart()
        self.chart.addSeries(self.series_linear)
        self.chart.addSeries(self.series_angular)
        self.chart.setTitle("Rychlost")
        self.chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        
        # Osy
        axis_x = QValueAxis()
        axis_x.setTitleText("Čas (s)")
        axis_x.setRange(0, 60)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("Rychlost (m/s)")
        axis_y.setRange(-1.0, 1.0)
        
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series_linear.attachAxis(axis_x)
        self.series_linear.attachAxis(axis_y)
        self.series_angular.attachAxis(axis_x)
        self.series_angular.attachAxis(axis_y)
        
        # Chart view
        chart_view = QChartView(self.chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        layout.addWidget(chart_view)
        
    def add_data_point(self, linear: float, angular: float):
        """Přidej datový bod"""
        elapsed = time.time() - self.start_time
        
        self.data_linear.append(linear)
        self.data_angular.append(angular)
        self.timestamps.append(elapsed)
        
        # Aktualizuj sérii
        self.series_linear.clear()
        self.series_angular.clear()
        
        for t, v in zip(self.timestamps, self.data_linear):
            self.series_linear.append(t, v)
            
        for t, v in zip(self.timestamps, self.data_angular):
            self.series_angular.append(t, v)


class SensorReadingsWidget(QWidget):
    """Widget pro senzory"""
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        
        # IMU
        imu_group = QGroupBox("IMU")
        imu_layout = QVBoxLayout(imu_group)
        
        self.pitch_label = QLabel("Pitch: 0.0°")
        self.roll_label = QLabel("Roll: 0.0°")
        self.yaw_label = QLabel("Yaw: 0.0°")
        
        imu_layout.addWidget(self.pitch_label)
        imu_layout.addWidget(self.roll_label)
        imu_layout.addWidget(self.yaw_label)
        
        layout.addWidget(imu_group)
        
        # Ultrazvukové senzory
        ultrasonic_group = QGroupBox("Vzdálenostní senzory")
        ultrasonic_layout = QVBoxLayout(ultrasonic_group)
        
        self.us_front_label = QLabel("Vpřed: 100 cm")
        self.us_left_label = QLabel("Vlevo: 100 cm")
        self.us_right_label = QLabel("Vpravo: 100 cm")
        self.us_back_label = QLabel("Vzadu: 100 cm")
        
        ultrasonic_layout.addWidget(self.us_front_label)
        ultrasonic_layout.addWidget(self.us_left_label)
        ultrasonic_layout.addWidget(self.us_right_label)
        ultrasonic_layout.addWidget(self.us_back_label)
        
        layout.addWidget(ultrasonic_group)
        
        # Teploty
        temp_group = QGroupBox("Teploty")
        temp_layout = QVBoxLayout(temp_group)
        
        self.cpu_temp_label = QLabel("CPU: 45°C")
        self.motor_temp_label = QLabel("Motor: 40°C")
        
        temp_layout.addWidget(self.cpu_temp_label)
        temp_layout.addWidget(self.motor_temp_label)
        
        layout.addWidget(temp_group)
        
        layout.addStretch()
        
    def update_sensors(self, telemetry):
        """Aktualizuj senzory"""
        self.pitch_label.setText(f"Pitch: {telemetry.get('pitch', 0):.2f}°")
        self.roll_label.setText(f"Roll: {telemetry.get('roll', 0):.2f}°")
        self.yaw_label.setText(f"Yaw: {telemetry.get('yaw', 0):.2f}°")
        
        self.us_front_label.setText(f"Vpřed: {telemetry.get('ultrasonic_front', 0):.0f} cm")
        self.us_left_label.setText(f"Vlevo: {telemetry.get('ultrasonic_left', 0):.0f} cm")
        self.us_right_label.setText(f"Vpravo: {telemetry.get('ultrasonic_right', 0):.0f} cm")
        self.us_back_label.setText(f"Vzadu: {telemetry.get('ultrasonic_back', 0):.0f} cm")
        
        self.cpu_temp_label.setText(f"CPU: {telemetry.get('cpu_temperature', 0):.0f}°C")
        self.motor_temp_label.setText(f"Motor: {telemetry.get('motor_temperature', 0):.0f}°C")


class TelemetryPanel(QWidget):
    """Hlavní telemetry panel"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        self._setup_ui()
        
        # Timer pro demo data
        self._demo_timer = QTimer()
        self._demo_timer.timeout.connect(self._update_demo_data)
        self._demo_timer.start(1000)  # 1 Hz pro telemetrii
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Nadpis
        title = QLabel("📊 Telemetrie")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Baterie
        battery_group = QGroupBox("🔋 Baterie")
        battery_layout = QVBoxLayout(battery_group)
        self.battery_widget = BatteryWidget()
        battery_layout.addWidget(self.battery_widget)
        layout.addWidget(battery_group)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Grafy
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        
        self.speed_chart = SpeedChartWidget()
        charts_layout.addWidget(self.speed_chart)
        
        self.tabs.addTab(charts_tab, "📈 Grafy")
        
        # Tab 2: Senzory
        sensors_tab = QWidget()
        sensors_layout = QVBoxLayout(sensors_tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.sensors_widget = SensorReadingsWidget()
        scroll.setWidget(self.sensors_widget)
        
        sensors_layout.addWidget(scroll)
        
        self.tabs.addTab(sensors_tab, "📡 Senzory")
        
        # Tab 3: Nastavení
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.addWidget(QLabel("Nastavení - TODO"))
        settings_layout.addStretch()
        
        self.tabs.addTab(settings_tab, "⚙️ Nastavení")
        
        layout.addWidget(self.tabs, 1)
        
    def _update_demo_data(self):
        """Aktualizuj demo data"""
        import random
        
        # Simulace dat
        linear = random.uniform(-0.3, 0.6)
        angular = random.uniform(-0.2, 0.2)
        
        self.speed_chart.add_data_point(linear, angular)
        
        # Simulace telemetrie
        demo_telemetry = {
            'pitch': random.uniform(-5, 5),
            'roll': random.uniform(-3, 3),
            'yaw': random.uniform(0, 360),
            'ultrasonic_front': random.uniform(50, 150),
            'ultrasonic_left': random.uniform(50, 150),
            'ultrasonic_right': random.uniform(50, 150),
            'ultrasonic_back': random.uniform(50, 150),
            'cpu_temperature': random.uniform(40, 60),
            'motor_temperature': random.uniform(35, 55),
        }
        
        self.sensors_widget.update_sensors(demo_telemetry)
