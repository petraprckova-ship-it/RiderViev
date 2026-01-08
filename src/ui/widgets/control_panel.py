"""
Control Panel - levý panel s ovládáním robota
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QGroupBox, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIntValidator
from loguru import logger

from ...config import Config, ProfileManager, RobotProfile
from pathlib import Path


class ConnectionWidget(QWidget):
    """Widget pro připojení k robotu"""
    
    connection_changed = pyqtSignal(bool)  # True = připojeno
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_connected = False
        
        # Profile manager
        profiles_path = Path.home() / ".person_tracker" / "profiles.json"
        self.profile_manager = ProfileManager(profiles_path)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        
        # Nadpis
        title = QLabel("🔌 Připojení")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Profil dropdown
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Profil:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("-- Nový profil --")
        
        # Načti profily
        for profile in self.profile_manager.profiles:
            self.profile_combo.addItem(profile.name)
            
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        
        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(self.profile_combo, 1)
        layout.addLayout(profile_layout)
        
        # IP adresa
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP adresa:")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.ip_input.setText("192.168.1.100")
        
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input, 1)
        layout.addLayout(ip_layout)
        
        # Port
        port_layout = QHBoxLayout()
        port_label = QLabel("Port SSH:")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("22")
        self.port_input.setText("22")
        self.port_input.setValidator(QIntValidator(1, 65535))
        
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input, 1)
        layout.addLayout(port_layout)
        
        # Status indikátor
        self.status_label = QLabel("⚫ Odpojeno")
        self.status_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Tlačítka
        button_layout = QHBoxLayout()
        
        self.connect_button = QPushButton("Připojit")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.connect_button.setStyleSheet("background-color: #89b4fa;")
        
        self.disconnect_button = QPushButton("Odpojit")
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.setStyleSheet("background-color: #f38ba8;")
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
    def _on_profile_changed(self, profile_name: str):
        """Handler pro změnu profilu"""
        if profile_name == "-- Nový profil --":
            self.ip_input.clear()
            self.port_input.setText("22")
            return
            
        profile = self.profile_manager.get_profile(profile_name)
        if profile:
            self.ip_input.setText(profile.ip)
            self.port_input.setText(str(profile.port))
            
    def on_connect_clicked(self):
        """Handler pro připojení"""
        ip = self.ip_input.text()
        port = self.port_input.text()
        
        if not ip:
            logger.warning("IP adresa není zadána")
            return
            
        logger.info(f"Připojuji se k {ip}:{port}")
        
        # TODO: Skutečné připojení přes network client
        
        # Simulace připojení
        self.is_connected = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.status_label.setText("🟢 Připojeno")
        self.status_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        
        self.connection_changed.emit(True)
        
    def on_disconnect_clicked(self):
        """Handler pro odpojení"""
        logger.info("Odpojuji se od robota")
        
        # TODO: Skutečné odpojení
        
        self.is_connected = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.status_label.setText("⚫ Odpojeno")
        self.status_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
        
        self.connection_changed.emit(False)


class ModeSelector(QWidget):
    """Widget pro výběr režimu"""
    
    mode_changed = pyqtSignal(str)
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.current_mode = "stop"
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        
        # Nadpis
        title = QLabel("🎮 Režim")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Tlačítka režimů
        self.auto_button = QPushButton("🎯 Auto-sledování")
        self.auto_button.setCheckable(True)
        self.auto_button.clicked.connect(lambda: self.set_mode("auto"))
        self.auto_button.setMinimumHeight(50)
        layout.addWidget(self.auto_button)
        
        self.manual_button = QPushButton("⌨️ Manuální")
        self.manual_button.setCheckable(True)
        self.manual_button.clicked.connect(lambda: self.set_mode("manual"))
        self.manual_button.setMinimumHeight(50)
        layout.addWidget(self.manual_button)
        
        self.patrol_button = QPushButton("🔄 Hlídkování")
        self.patrol_button.setCheckable(True)
        self.patrol_button.clicked.connect(lambda: self.set_mode("patrol"))
        self.patrol_button.setMinimumHeight(50)
        layout.addWidget(self.patrol_button)
        
        self.stop_button = QPushButton("🛑 Stop")
        self.stop_button.setCheckable(True)
        self.stop_button.clicked.connect(lambda: self.set_mode("stop"))
        self.stop_button.setChecked(True)
        self.stop_button.setMinimumHeight(50)
        layout.addWidget(self.stop_button)
        
        layout.addStretch()
        
    def set_mode(self, mode: str):
        """Nastav režim"""
        # Odznač všechna tlačítka
        self.auto_button.setChecked(False)
        self.manual_button.setChecked(False)
        self.patrol_button.setChecked(False)
        self.stop_button.setChecked(False)
        
        # Zaškrtni vybrané
        if mode == "auto":
            self.auto_button.setChecked(True)
        elif mode == "manual":
            self.manual_button.setChecked(True)
        elif mode == "patrol":
            self.patrol_button.setChecked(True)
        else:
            self.stop_button.setChecked(True)
            
        self.current_mode = mode
        self.mode_changed.emit(mode)
        logger.info(f"Režim změněn na: {mode}")


class SpeedControl(QWidget):
    """Widget pro ovládání rychlosti"""
    
    speed_changed = pyqtSignal(float)  # 0.0 - 1.0
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.current_speed = 0.6  # 60%
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        
        # Nadpis
        title = QLabel("⚡ Rychlost")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Rychlost jako procenta
        self.speed_label = QLabel(f"{int(self.current_speed * 100)}%")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.speed_label)
        
        # Slider
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(int(self.current_speed * 100))
        self.speed_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.speed_slider)
        
        # Předvolby
        preset_layout = QHBoxLayout()
        
        cautious_btn = QPushButton("Opatrný\n30%")
        cautious_btn.clicked.connect(lambda: self._set_preset(0.3))
        preset_layout.addWidget(cautious_btn)
        
        normal_btn = QPushButton("Normální\n60%")
        normal_btn.clicked.connect(lambda: self._set_preset(0.6))
        preset_layout.addWidget(normal_btn)
        
        fast_btn = QPushButton("Rychlý\n90%")
        fast_btn.clicked.connect(lambda: self._set_preset(0.9))
        preset_layout.addWidget(fast_btn)
        
        layout.addLayout(preset_layout)
        layout.addStretch()
        
    def _on_slider_changed(self, value: int):
        """Handler pro změnu slideru"""
        self.current_speed = value / 100.0
        self.speed_label.setText(f"{value}%")
        self.speed_changed.emit(self.current_speed)
        
    def _set_preset(self, speed: float):
        """Nastav předvolenou rychlost"""
        self.speed_slider.setValue(int(speed * 100))


class ControlPanel(QWidget):
    """Hlavní control panel"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)
        
        # Connection widget
        self.connection_widget = ConnectionWidget(self.config)
        connection_group = QGroupBox()
        connection_layout = QVBoxLayout(connection_group)
        connection_layout.addWidget(self.connection_widget)
        layout.addWidget(connection_group)
        
        # Mode selector
        self.mode_selector = ModeSelector(self.config)
        mode_group = QGroupBox()
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.addWidget(self.mode_selector)
        layout.addWidget(mode_group)
        
        # Speed control
        self.speed_control = SpeedControl(self.config)
        speed_group = QGroupBox()
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.addWidget(self.speed_control)
        layout.addWidget(speed_group)
        
        # Emergency stop button
        self.emergency_stop_button = QPushButton("🛑 NOUZOVÉ ZASTAVENÍ")
        self.emergency_stop_button.setMinimumHeight(60)
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                font-size: 16px;
                font-weight: bold;
                border: 3px solid #eba0ac;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #f38ba8;
                border: 3px solid #cba6f7;
            }
        """)
        layout.addWidget(self.emergency_stop_button)
        
        layout.addStretch()
