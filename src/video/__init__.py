"""
Video streaming
"""

try:
    from .gstreamer_client import GStreamerClient, RTSPStreamRecorder, GSTREAMER_AVAILABLE
except ImportError:
    GStreamerClient = None
    RTSPStreamRecorder = None
    GSTREAMER_AVAILABLE = False

__all__ = ['GStreamerClient', 'RTSPStreamRecorder', 'GSTREAMER_AVAILABLE']
