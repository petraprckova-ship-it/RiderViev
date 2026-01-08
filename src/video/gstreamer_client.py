"""
GStreamer video streaming client
"""

try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstApp', '1.0')
    from gi.repository import Gst, GstApp
    GSTREAMER_AVAILABLE = True
except (ImportError, ValueError) as e:
    GSTREAMER_AVAILABLE = False
    Gst = None
    GstApp = None

import numpy as np
from loguru import logger
from typing import Optional, Callable
import threading


class GStreamerClient:
    """
    GStreamer klient pro RTSP video stream
    """
    
    def __init__(self, rtsp_url: str, on_frame: Optional[Callable] = None):
        """
        Args:
            rtsp_url: RTSP URL (např. rtsp://192.168.1.100:8554/video)
            on_frame: Callback funkce pro nové snímky (frame: np.ndarray)
        """
        if not GSTREAMER_AVAILABLE:
            raise RuntimeError(
                "GStreamer není k dispozici. "
                "Na Windows nainstalujte GStreamer z: https://gstreamer.freedesktop.org/download/"
            )
        
        self.rtsp_url = rtsp_url
        self.on_frame = on_frame
        
        # Inicializace GStreamer
        Gst.init(None)
        
        self.pipeline: Optional[Gst.Pipeline] = None
        self.appsink: Optional[GstApp.AppSink] = None
        self.is_running = False
        
        self._frame_count = 0
        self._last_frame: Optional[np.ndarray] = None
        
    def start(self):
        """Spuštění video streamu"""
        if self.is_running:
            logger.warning("Video stream již běží")
            return
            
        logger.info(f"Spouštím video stream: {self.rtsp_url}")
        
        # Vytvoř GStreamer pipeline
        # RTSP source -> H.264 decode -> videoconvert -> appsink
        pipeline_str = (
            f"rtspsrc location={self.rtsp_url} latency=50 ! "
            "rtph264depay ! "
            "h264parse ! "
            "avdec_h264 ! "  # Software decode (pro hardware: v4l2h264dec)
            "videoconvert ! "
            "video/x-raw,format=RGB ! "
            "appsink name=sink emit-signals=true max-buffers=1 drop=true"
        )
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            
            # Získej appsink
            self.appsink = self.pipeline.get_by_name("sink")
            
            if not self.appsink:
                raise RuntimeError("Nelze získat appsink z pipeline")
                
            # Nastavení callbacku
            self.appsink.connect("new-sample", self._on_new_sample)
            
            # Spuštění pipeline
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("Nelze spustit GStreamer pipeline")
                
            self.is_running = True
            logger.info("Video stream spuštěn úspěšně")
            
        except Exception as e:
            logger.error(f"Chyba při spouštění video streamu: {e}")
            self.stop()
            raise
            
    def stop(self):
        """Zastavení video streamu"""
        if not self.is_running:
            return
            
        logger.info("Zastavuji video stream")
        
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            
        self.appsink = None
        self.is_running = False
        
    def _on_new_sample(self, sink: GstApp.AppSink) -> Gst.FlowReturn:
        """Callback pro nový snímek"""
        sample = sink.emit("pull-sample")
        
        if not sample:
            return Gst.FlowReturn.ERROR
            
        # Získej buffer
        buffer = sample.get_buffer()
        caps = sample.get_caps()
        
        # Získej rozměry
        structure = caps.get_structure(0)
        width = structure.get_value("width")
        height = structure.get_value("height")
        
        # Extrahuj data
        success, map_info = buffer.map(Gst.MapFlags.READ)
        
        if not success:
            logger.warning("Nelze mapovat buffer")
            return Gst.FlowReturn.ERROR
            
        try:
            # Konverze na numpy array
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            
            # Kopie dat (buffer se uvolní)
            frame = frame.copy()
            
            self._frame_count += 1
            self._last_frame = frame
            
            # Zavolej callback
            if self.on_frame:
                self.on_frame(frame)
                
        finally:
            buffer.unmap(map_info)
            
        return Gst.FlowReturn.OK
        
    def get_last_frame(self) -> Optional[np.ndarray]:
        """Vrať poslední snímek"""
        return self._last_frame
        
    def get_frame_count(self) -> int:
        """Vrať počet přijatých snímků"""
        return self._frame_count
        
    @staticmethod
    def test_connection(rtsp_url: str, timeout: float = 5.0) -> bool:
        """
        Test připojení k RTSP streamu
        
        Args:
            rtsp_url: RTSP URL
            timeout: Timeout v sekundách
            
        Returns:
            True pokud lze připojit
        """
        Gst.init(None)
        
        pipeline_str = (
            f"rtspsrc location={rtsp_url} latency=50 ! "
            "fakesink"
        )
        
        try:
            pipeline = Gst.parse_launch(pipeline_str)
            ret = pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                return False
                
            # Počkej na PLAYING state
            state_ret = pipeline.get_state(int(timeout * Gst.SECOND))
            
            pipeline.set_state(Gst.State.NULL)
            
            return state_ret[0] == Gst.StateChangeReturn.SUCCESS
            
        except Exception as e:
            logger.error(f"Test připojení selhal: {e}")
            return False


class RTSPStreamRecorder:
    """
    Záznamník RTSP streamu do souboru
    """
    
    def __init__(self, rtsp_url: str, output_path: str):
        """
        Args:
            rtsp_url: RTSP URL
            output_path: Cesta k výstupnímu souboru (.mp4)
        """
        self.rtsp_url = rtsp_url
        self.output_path = output_path
        
        Gst.init(None)
        
        self.pipeline: Optional[Gst.Pipeline] = None
        self.is_recording = False
        
    def start_recording(self):
        """Spuštění záznamu"""
        if self.is_recording:
            logger.warning("Záznam již běží")
            return
            
        logger.info(f"Spouštím záznam do: {self.output_path}")
        
        # Pipeline pro záznam
        # RTSP -> H.264 decode -> H.264 encode -> MP4 mux -> filesink
        pipeline_str = (
            f"rtspsrc location={self.rtsp_url} latency=50 ! "
            "rtph264depay ! "
            "h264parse ! "
            "mp4mux ! "
            f"filesink location={self.output_path}"
        )
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("Nelze spustit záznam")
                
            self.is_recording = True
            logger.info("Záznam spuštěn")
            
        except Exception as e:
            logger.error(f"Chyba při spouštění záznamu: {e}")
            self.stop_recording()
            raise
            
    def stop_recording(self):
        """Zastavení záznamu"""
        if not self.is_recording:
            return
            
        logger.info("Zastavuji záznam")
        
        if self.pipeline:
            # Pošli EOS pro korektní ukončení souboru
            self.pipeline.send_event(Gst.Event.new_eos())
            
            # Počkej na EOS
            bus = self.pipeline.get_bus()
            bus.timed_pop_filtered(
                Gst.CLOCK_TIME_NONE,
                Gst.MessageType.EOS | Gst.MessageType.ERROR
            )
            
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            
        self.is_recording = False
        logger.info(f"Záznam uložen: {self.output_path}")
