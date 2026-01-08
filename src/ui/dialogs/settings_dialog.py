"""
Nastavení aplikace - dialog
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QGroupBox, QSpinBox,
    QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt
from loguru import logger

from ...config import Config


class SettingsDialog(QDialog):
    """Dialog pro nastavení aplikace"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("Nastavení")
        self.setGeometry(100, 100, 500, 400)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout()
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_robot_tab(), "Robot")
        tabs.addTab(self._create_ml_tab(), "ML")
        tabs.addTab(self._create_ui_tab(), "UI")
        
        layout.addWidget(tabs)
        
        # Buttony
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Zrušit")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _create_robot_tab(self) -> QWidget:
        """Vytvoř tab s nastavením robota"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Robot IP
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("Robot IP:"))
        self.robot_ip = QLineEdit()
        self.robot_ip.setText(self.config.robot.ip if self.config.robot else "")
        ip_layout.addWidget(self.robot_ip)
        layout.addLayout(ip_layout)
        
        # Robot Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.robot_port = QSpinBox()
        self.robot_port.setValue(self.config.robot.port if self.config.robot else 8000)
        port_layout.addWidget(self.robot_port)
        layout.addLayout(port_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_ml_tab(self) -> QWidget:
        """Vytvoř tab s nastavením ML"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("YOLO Model:"))
        self.ml_model = QLineEdit()
        self.ml_model.setText(self.config.ml.detector.model_name if self.config.ml else "yolo11n")
        model_layout.addWidget(self.ml_model)
        layout.addLayout(model_layout)
        
        # Confidence
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold:"))
        self.ml_confidence = QDoubleSpinBox()
        self.ml_confidence.setMinimum(0.0)
        self.ml_confidence.setMaximum(1.0)
        self.ml_confidence.setSingleStep(0.05)
        self.ml_confidence.setValue(self.config.ml.detector.confidence_threshold if self.config.ml else 0.5)
        conf_layout.addWidget(self.ml_confidence)
        layout.addLayout(conf_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_ui_tab(self) -> QWidget:
        """Vytvoř tab s nastavením UI"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Dark mode
        dark_mode_layout = QHBoxLayout()
        self.dark_mode = QCheckBox("Tmavý režim")
        self.dark_mode.setChecked(self.config.ui.dark_mode if self.config.ui else True)
        dark_mode_layout.addWidget(self.dark_mode)
        layout.addLayout(dark_mode_layout)
        
        # Update rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Update Rate (Hz):"))
        self.ui_rate = QSpinBox()
        self.ui_rate.setMinimum(1)
        self.ui_rate.setMaximum(60)
        self.ui_rate.setValue(30)
        rate_layout.addWidget(self.ui_rate)
        layout.addLayout(rate_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
