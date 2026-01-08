"""
Hlavní okno aplikace
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent
from loguru import logger

from ..config import Config
from .widgets.control_panel import ControlPanel
from .widgets.video_display import VideoDisplay
from .widgets.telemetry_panel import TelemetryPanel
from .dialogs.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """
    Hlavní okno aplikace Person Tracker
    """

    # Signály
    connection_changed = pyqtSignal(bool)  # True = připojeno
    mode_changed = pyqtSignal(str)  # Změna režimu
    emergency_stop_triggered = pyqtSignal()

    def __init__(self, config: Config):
        super().__init__()

        self.config = config
        self.is_connected = False

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._apply_theme()

        # Timer pro update UI
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self._update_ui)
        self.ui_update_timer.start(33)  # ~30 FPS

        logger.info("Hlavní okno inicializováno")

    def _setup_ui(self):
        """Nastavení uživatelského rozhraní"""
        self.setWindowTitle(f"{self.config.app.name} v{self.config.app.version}")

        # Nastavení velikosti okna
        window_config = self.config.ui.window
        self.resize(window_config['width'], window_config['height'])

        if window_config.get('fullscreen', False):
            self.showFullScreen()

        # Centrální widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Hlavní layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter pro rozdělení prostoru
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Levý panel - Control Panel
        self.control_panel = ControlPanel(self.config)
        self.control_panel.setMinimumWidth(300)
        self.control_panel.setMaximumWidth(400)
        self.main_splitter.addWidget(self.control_panel)

        # Střední panel - Video Display
        self.video_display = VideoDisplay(self.config)
        self.main_splitter.addWidget(self.video_display)

        # Pravý panel - Telemetry
        self.telemetry_panel = TelemetryPanel(self.config)
        self.telemetry_panel.setMinimumWidth(350)
        self.telemetry_panel.setMaximumWidth(450)
        self.main_splitter.addWidget(self.telemetry_panel)

        # Nastavení poměrů splitteru
        self.main_splitter.setSizes([300, 1000, 350])

        # Propojení signálů
        self._connect_signals()

    def _setup_menu(self):
        """Vytvoření menu"""
        menubar = self.menuBar()

        # Soubor menu
        file_menu = menubar.addMenu("&Soubor")

        # Připojit
        connect_action = QAction("&Připojit k robotu", self)
        connect_action.setShortcut(QKeySequence("Ctrl+O"))
        connect_action.triggered.connect(self.control_panel.connection_widget.on_connect_clicked)
        file_menu.addAction(connect_action)

        # Odpojit
        disconnect_action = QAction("&Odpojit", self)
        disconnect_action.setShortcut(QKeySequence("Ctrl+D"))
        disconnect_action.triggered.connect(self.control_panel.connection_widget.on_disconnect_clicked)
        file_menu.addAction(disconnect_action)

        file_menu.addSeparator()

        # Ukončit
        exit_action = QAction("&Ukončit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Ovládání menu
        control_menu = menubar.addMenu("&Ovládání")

        # Emergency Stop
        estop_action = QAction("&NOUZOVÉ ZASTAVENÍ", self)
        estop_action.setShortcut(QKeySequence("Space"))
        estop_action.triggered.connect(self._on_emergency_stop)
        control_menu.addAction(estop_action)

        control_menu.addSeparator()

        # Režimy
        auto_action = QAction("Režim: &Auto-sledování", self)
        auto_action.setShortcut(QKeySequence("Ctrl+A"))
        auto_action.triggered.connect(lambda: self._set_mode("auto"))
        control_menu.addAction(auto_action)

        manual_action = QAction("Režim: &Manuální", self)
        manual_action.setShortcut(QKeySequence("Ctrl+M"))
        manual_action.triggered.connect(lambda: self._set_mode("manual"))
        control_menu.addAction(manual_action)

        stop_action = QAction("Režim: &Stop", self)
        stop_action.setShortcut(QKeySequence("Ctrl+S"))
        stop_action.triggered.connect(lambda: self._set_mode("stop"))
        control_menu.addAction(stop_action)

        # Zobrazení menu
        view_menu = menubar.addMenu("&Zobrazení")

        # Fullscreen
        fullscreen_action = QAction("&Celá obrazovka", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        view_menu.addSeparator()

        # Panely
        toggle_control_action = QAction("Zobrazit &Ovládací panel", self)
        toggle_control_action.setCheckable(True)
        toggle_control_action.setChecked(True)
        toggle_control_action.triggered.connect(lambda checked: self.control_panel.setVisible(checked))
        view_menu.addAction(toggle_control_action)

        toggle_telemetry_action = QAction("Zobrazit &Telemetrii", self)
        toggle_telemetry_action.setCheckable(True)
        toggle_telemetry_action.setChecked(True)
        toggle_telemetry_action.triggered.connect(lambda checked: self.telemetry_panel.setVisible(checked))
        view_menu.addAction(toggle_telemetry_action)

        # Nastavení menu
        settings_menu = menubar.addMenu("&Nastavení")

        # Nastavení
        settings_action = QAction("&Předvolby", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        settings_menu.addAction(settings_action)

        # Nápověda menu
        help_menu = menubar.addMenu("&Nápověda")

        # O aplikaci
        about_action = QAction("&O aplikaci", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self):
        """Nastavení klávesových zkratek"""
        # WASD pro manuální ovládání
        # Implementováno ve video_display

        # F1-F4 pro rychlé změny režimu
        # Už je v menu
        pass

    def _setup_statusbar(self):
        """Nastavení stavového řádku"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Výchozí zpráva
        self.status_bar.showMessage("Připraveno | Odpojeno")

    def _apply_theme(self):
        """Aplikuj barevné téma"""
        theme = self.config.app.theme
        colors = self.config.ui.colors[theme]

        # QSS stylesheet
        stylesheet = f"""
        QMainWindow {{
            background-color: {colors.background};
            color: {colors.text};
        }}
        
        QWidget {{
            background-color: {colors.background};
            color: {colors.text};
            font-family: {self.config.ui.fonts['body']};
            font-size: 14px;
        }}
        
        QMenuBar {{
            background-color: {colors.surface};
            color: {colors.text};
            border-bottom: 1px solid {colors.overlay};
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors.overlay};
        }}
        
        QMenu {{
            background-color: {colors.surface};
            color: {colors.text};
            border: 1px solid {colors.overlay};
        }}
        
        QMenu::item:selected {{
            background-color: {colors.primary};
        }}
        
        QStatusBar {{
            background-color: {colors.surface};
            color: {colors.subtext};
            border-top: 1px solid {colors.overlay};
        }}
        
        QPushButton {{
            background-color: {colors.primary};
            color: {colors.background};
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {colors.success};
        }}
        
        QPushButton:pressed {{
            background-color: {colors.overlay};
        }}
        
        QPushButton:disabled {{
            background-color: {colors.overlay};
            color: {colors.subtext};
        }}
        """

        self.setStyleSheet(stylesheet)
        logger.info(f"Téma aplikováno: {theme}")

    def _connect_signals(self):
        """Propojení signálů mezi komponenty"""
        # Control panel signály
        self.control_panel.connection_widget.connection_changed.connect(self._on_connection_changed)
        self.control_panel.mode_selector.mode_changed.connect(self._on_mode_changed)
        self.control_panel.emergency_stop_button.clicked.connect(self._on_emergency_stop)

        # TODO: Propojit další signály pro ML pipeline, network, atd.

    def _update_ui(self):
        """Pravidelná aktualizace UI"""
        # TODO: Aktualizuj video display, telemetrii, atd.
        pass

    def _on_connection_changed(self, connected: bool):
        """Handler pro změnu stavu připojení"""
        self.is_connected = connected
        self.connection_changed.emit(connected)

        if connected:
            self.status_bar.showMessage("✓ Připojeno k robotu")
            logger.success("Připojeno k robotu")
        else:
            self.status_bar.showMessage("✗ Odpojeno od robota")
            logger.info("Odpojeno od robota")

    def _on_mode_changed(self, mode: str):
        """Handler pro změnu režimu"""
        self.mode_changed.emit(mode)
        self.status_bar.showMessage(f"Režim: {mode}")
        logger.info(f"Režim změněn na: {mode}")

    def _on_emergency_stop(self):
        """Handler pro nouzové zastavení"""
        self.emergency_stop_triggered.emit()
        logger.warning("⚠️ NOUZOVÉ ZASTAVENÍ aktivováno")

        QMessageBox.warning(
            self,
            "Nouzové zastavení",
            "Robot byl nouzově zastaven!\n\nPro pokračování změňte režim.",
            QMessageBox.StandardButton.Ok
        )

    def _set_mode(self, mode: str):
        """Nastav režim"""
        self.control_panel.mode_selector.set_mode(mode)

    def _toggle_fullscreen(self, checked: bool):
        """Přepni fullscreen"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _show_settings(self):
        """Zobraz dialog nastavení"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            logger.info("Nastavení uloženo")
            # TODO: Aplikuj změny konfigurace

    def _show_about(self):
        """Zobraz dialog O aplikaci"""
        about_text = f"""
        <h2>{self.config.app.name}</h2>
        <p>Verze: {self.config.app.version}</p>
        <p>Pokročilá desktopová aplikace pro detekci, sledování osob 
        a autonomní navigaci dvoukolového samovyvažovacího robota 
        Yahboom Rider Pi CM4.</p>
        <p><b>Autor:</b> Petra Prčková</p>
        <p><b>Licence:</b> MIT</p>
        <hr>
        <p><small>⚠️ Bezpečnostní upozornění: Robot se pohybuje autonomně. 
        Vždy zajistěte bezpečný provozní prostor.</small></p>
        """

        QMessageBox.about(self, f"O aplikaci {self.config.app.name}", about_text)

    def closeEvent(self, event: QCloseEvent):
        """Handler pro zavření okna"""
        reply = QMessageBox.question(
            self,
            "Ukončit aplikaci",
            "Opravdu chcete ukončit aplikaci?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("Ukončuji aplikaci...")

            # TODO: Odpojit od robota, uložit konfiguraci, atd.

            event.accept()
        else:
            event.ignore()
