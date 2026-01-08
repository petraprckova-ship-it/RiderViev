"""
Video Display - střední panel s video streamem
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from loguru import logger
import numpy as np
import cv2

from ...config import Config
from ...video.gstreamer_client import GStreamerClient


class VideoWidget(QWidget):
    """Widget pro zobrazení videa s overlays"""
    
    def __init__(self):
        super().__init__()
        self.frame: np.ndarray = None
        self.detections = []
        self.tracks = []
        self.fps = 0
        self.show_fps = True
        self.show_overlays = True
        
        # Černé pozadí jako placeholder
        self.setStyleSheet("background-color: #000000;")
        self.setMinimumSize(640, 480)
        
    def set_frame(self, frame: np.ndarray):
        """Nastav nový snímek"""
        self.frame = frame
        self.update()
        
    def set_detections(self, detections):
        """Nastav detekce"""
        self.detections = detections
        
    def set_tracks(self, tracks):
        """Nastav tracky"""
        self.tracks = tracks
        
    def set_fps(self, fps: float):
        """Nastav FPS"""
        self.fps = fps
        
    def paintEvent(self, event):
        """Vykreslení"""
        painter = QPainter(self)
        
        if self.frame is not None:
            # Konverze OpenCV BGR -> RGB
            frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            # Vytvoř QImage
            q_image = QImage(
                frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )
            
            # Škáluj na velikost widgetu (zachovej aspect ratio)
            scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Centrování
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # Vykreslení overlays
            if self.show_overlays:
                self._draw_overlays(painter, x, y, scaled_pixmap.width(), scaled_pixmap.height())
                
            # FPS counter
            if self.show_fps:
                self._draw_fps(painter)
        else:
            # Placeholder text
            painter.setPen(QColor("#cdd6f4"))
            painter.setFont(QFont("Inter", 18))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Čekám na video stream..."
            )
            
    def _draw_overlays(self, painter: QPainter, offset_x, offset_y, scaled_w, scaled_h):
        """Vykreslení detection overlays"""
        if not self.tracks:
            return
            
        # Škálovací faktor
        if self.frame is not None:
            scale_x = scaled_w / self.frame.shape[1]
            scale_y = scaled_h / self.frame.shape[0]
        else:
            return
            
        painter.setPen(QPen(QColor("#89b4fa"), 3))
        painter.setFont(QFont("JetBrains Mono", 12))
        
        for track in self.tracks:
            # Bbox
            x1 = int(track.bbox[0] * scale_x) + offset_x
            y1 = int(track.bbox[1] * scale_y) + offset_y
            x2 = int(track.bbox[2] * scale_x) + offset_x
            y2 = int(track.bbox[3] * scale_y) + offset_y
            
            # Vykreslení bbox
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            
            # ID a confidence
            text = f"ID:{track.track_id} {track.confidence:.2f}"
            painter.drawText(x1, y1 - 5, text)
            
    def _draw_fps(self, painter: QPainter):
        """Vykreslení FPS counteru"""
        painter.setPen(QColor("#a6e3a1"))
        painter.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        
        fps_text = f"FPS: {self.fps:.1f}"
        
        # Pozadí pro čitelnost
        text_rect = painter.fontMetrics().boundingRect(fps_text)
        bg_rect = QRect(
            self.width() - text_rect.width() - 20,
            10,
            text_rect.width() + 10,
            text_rect.height() + 10
        )
        
        painter.fillRect(bg_rect, QColor(0, 0, 0, 128))
        painter.drawText(
            self.width() - text_rect.width() - 15,
            30,
            fps_text
        )


class VideoDisplay(QWidget):
    """Hlavní video display panel"""
    
    fullscreen_toggled = pyqtSignal(bool)
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        self._setup_ui()
        
        # GStreamer client
        self.gstreamer_client: GStreamerClient = None
        self.is_streaming = False
        
        # Timer pro simulaci video streamu (dokud není připojeno)
        self._demo_timer = QTimer()
        self._demo_timer.timeout.connect(self._update_demo_frame)
        self._demo_timer.start(33)  # ~30 FPS
        
    def _setup_ui(self):
        """Nastavení UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = VideoWidget()
        layout.addWidget(self.video_widget, 1)
        
        # Toolbar dole
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        
        # Zoom controls
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.setMaximumWidth(50)
        toolbar_layout.addWidget(zoom_out_btn)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setMaximumWidth(50)
        toolbar_layout.addWidget(zoom_in_btn)
        
        toolbar_layout.addStretch()
        
        # Screenshot
        screenshot_btn = QPushButton("📷 Screenshot")
        screenshot_btn.clicked.connect(self._on_screenshot)
        toolbar_layout.addWidget(screenshot_btn)
        
        # Record
        self.record_btn = QPushButton("⏺️ Nahrávat")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self._on_record_toggle)
        toolbar_layout.addWidget(self.record_btn)
        
        # Fullscreen
        fullscreen_btn = QPushButton("⛶ Celá obrazovka")
        fullscreen_btn.clicked.connect(lambda: self.fullscreen_toggled.emit(True))
        toolbar_layout.addWidget(fullscreen_btn)
        
        layout.addLayout(toolbar_layout)
        
    def _update_demo_frame(self):
        """Aktualizuj demo frame (simulace)"""
        # Vytvoř testovací snímek
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Gradient jako pozadí
        for i in range(480):
            intensity = int(30 + (i / 480) * 20)
            frame[i, :] = [intensity, intensity, intensity + 10]
            
        # Text
        cv2.putText(
            frame,
            "Demo Video Stream",
            (200, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (137, 180, 250),
            2
        )
        
        cv2.putText(
            frame,
            "Cekam na pripojeni k robotu...",
            (150, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (205, 214, 244),
            1
        )
        
        self.video_widget.set_frame(frame)
        self.video_widget.set_fps(30.0)
        
    def _on_screenshot(self):
        """Handler pro screenshot"""
        logger.info("Screenshot uložen")
        # TODO: Implementovat ukládání
        
    def _on_record_toggle(self, checked: bool):
        """Handler pro nahrávání"""
        if checked:
            logger.info("Nahrávání spuštěno")
            self.record_btn.setText("⏹️ Zastavit")
            self.record_btn.setStyleSheet("background-color: #f38ba8;")
        else:
            logger.info("Nahrávání zastaveno")
            self.record_btn.setText("⏺️ Nahrávat")
            self.record_btn.setStyleSheet("")
            
    def start_stream(self, rtsp_url: str):
        """Spuštění RTSP streamu"""
        if self.is_streaming:
            self.stop_stream()
            
        try:
            logger.info(f"Připojuji se k RTSP: {rtsp_url}")
            
            self.gstreamer_client = GStreamerClient(
                rtsp_url=rtsp_url,
                on_frame=self._on_gstreamer_frame
            )
            
            self.gstreamer_client.start()
            self.is_streaming = True
            
            # Zastav demo timer
            self._demo_timer.stop()
            
            logger.info("RTSP stream připojen")
            
        except Exception as e:
            logger.error(f"Nelze spustit RTSP stream: {e}")
            self.is_streaming = False
            
    def stop_stream(self):
        """Zastavení RTSP streamu"""
        if not self.is_streaming:
            return
            
        logger.info("Zastavuji RTSP stream")
        
        if self.gstreamer_client:
            self.gstreamer_client.stop()
            self.gstreamer_client = None
            
        self.is_streaming = False
        
        # Spusť zpět demo timer
        self._demo_timer.start(33)
        
    def _on_gstreamer_frame(self, frame: np.ndarray):
        """Callback pro nový snímek z GStreamer"""
        # Konverze RGB -> BGR pro OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self.video_widget.set_frame(frame_bgr)
        
        # TODO: Aktualizuj FPS z reálného streamu
        self.video_widget.set_fps(30.0)
