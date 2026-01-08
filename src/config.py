"""
Konfigurační systém s validací pomocí Pydantic
"""

from pathlib import Path
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import yaml
import json
from loguru import logger


class VideoConfig(BaseModel):
    """Konfigurace video streamu"""
    resolution: Dict[str, int] = {"width": 640, "height": 480}
    fps: int = 30
    codec: Literal["h264", "h265", "mjpeg"] = "h264"
    bitrate: int = 2000000
    keyframe_interval: int = 30
    protocol: Literal["rtsp", "http"] = "rtsp"
    port: int = 8554
    latency_mode: Literal["ultra-low", "low", "normal"] = "low"


class DetectionConfig(BaseModel):
    """Konfigurace detekce osob"""
    model: Literal["yolo11n", "yolo11s", "yolo11m"] = "yolo11s"
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)
    nms_iou_threshold: float = Field(0.45, ge=0.0, le=1.0)
    device: str = "cuda:0"
    backend: Literal["tensorrt", "onnx", "pytorch"] = "tensorrt"
    fp16: bool = True
    batch_size: int = 1


class TrackingConfig(BaseModel):
    """Konfigurace trackingu"""
    algorithm: Literal["bytetrack"] = "bytetrack"
    track_buffer: int = 30
    match_threshold: float = 0.8
    min_track_length: int = 5


class DepthConfig(BaseModel):
    """Konfigurace odhadu hloubky"""
    enabled: bool = False
    model: Literal["depth_anything_v2_small", "midas_v31"] = "depth_anything_v2_small"


class PoseConfig(BaseModel):
    """Konfigurace pose estimation"""
    enabled: bool = False
    model: Literal["mediapipe"] = "mediapipe"


class MLConfig(BaseModel):
    """Konfigurace ML modelů"""
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    depth: DepthConfig = Field(default_factory=DepthConfig)
    pose: PoseConfig = Field(default_factory=PoseConfig)


class DistanceConfig(BaseModel):
    """Konfigurace měření vzdálenosti"""
    method: Literal["bbox", "depth", "fusion"] = "bbox"
    target_min: float = 1.0
    target_max: float = 2.5
    avg_person_height: float = 1.7
    focal_length: Optional[float] = None


class PIDConfig(BaseModel):
    """Konfigurace PID regulátoru"""
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.05
    output_limit: float = 1.0
    integral_limit: float = 1.0
    deadband: float = 0.0


class SpeedProfileConfig(BaseModel):
    """Profil rychlosti robota"""
    max_speed: float = Field(..., gt=0)
    max_turn_rate: float = Field(..., gt=0)
    acceleration: float = Field(..., gt=0)
    deceleration: float = Field(..., gt=0)


class ControlConfig(BaseModel):
    """Konfigurace řízení"""
    frequency: int = 50
    watchdog_timeout: float = 0.5
    pid: Dict[str, PIDConfig] = {
        "linear": PIDConfig(),
        "angular": PIDConfig(kp=2.0, ki=0.2, kd=0.1)
    }
    profiles: Dict[str, SpeedProfileConfig] = {
        "cautious": SpeedProfileConfig(
            max_speed=0.3, max_turn_rate=30, acceleration=0.2, deceleration=0.3
        ),
        "normal": SpeedProfileConfig(
            max_speed=0.6, max_turn_rate=60, acceleration=0.4, deceleration=0.5
        ),
        "aggressive": SpeedProfileConfig(
            max_speed=1.0, max_turn_rate=90, acceleration=0.6, deceleration=0.8
        )
    }
    default_profile: Literal["cautious", "normal", "aggressive"] = "normal"


class SafetyZonesConfig(BaseModel):
    """Konfigurace bezpečnostních zón"""
    red: float = 0.30
    yellow: float = 0.60
    green: float = 1000.0


class ObstacleAvoidanceConfig(BaseModel):
    """Konfigurace vyhýbání překážkám"""
    enabled: bool = True
    strategy: Literal["stop", "reverse", "steer_around", "alert"] = "steer_around"
    prediction_horizon: float = 1.5
    clearance_margin: float = 0.15


class EmergencyConfig(BaseModel):
    """Konfigurace nouzových situací"""
    stop_type: Literal["hard", "soft", "coast"] = "soft"
    connection_lost_action: Literal["stop", "continue", "patrol"] = "stop"
    tilt_threshold: float = 30.0


class GeofencingConfig(BaseModel):
    """Konfigurace geofencingu"""
    enabled: bool = False
    boundary: List[List[float]] = []
    action: Literal["stop", "reverse", "turn"] = "stop"
    warning_distance: float = 0.2


class SafetyConfig(BaseModel):
    """Konfigurace bezpečnosti"""
    zones: SafetyZonesConfig = Field(default_factory=SafetyZonesConfig)
    obstacle_avoidance: ObstacleAvoidanceConfig = Field(default_factory=ObstacleAvoidanceConfig)
    emergency: EmergencyConfig = Field(default_factory=EmergencyConfig)
    geofencing: GeofencingConfig = Field(default_factory=GeofencingConfig)


class NetworkConfig(BaseModel):
    """Konfigurace síťové komunikace"""
    command_port: int = 5555
    telemetry_port: int = 5556
    keepalive_interval: float = 1.0
    reconnect_interval: float = 5.0
    reconnect_max_attempts: int = 10
    tcp_nodelay: bool = True


class UIColorsConfig(BaseModel):
    """Barevné schéma UI"""
    background: str = "#1e1e2e"
    surface: str = "#313244"
    overlay: str = "#45475a"
    text: str = "#cdd6f4"
    subtext: str = "#bac2de"
    primary: str = "#89b4fa"
    success: str = "#a6e3a1"
    warning: str = "#f9e2af"
    error: str = "#f38ba8"


class UIConfig(BaseModel):
    """Konfigurace uživatelského rozhraní"""
    window: Dict[str, Any] = {"width": 1920, "height": 1080, "fullscreen": False}
    colors: Dict[str, UIColorsConfig] = {
        "dark": UIColorsConfig(),
        "light": UIColorsConfig(
            background="#eff1f5",
            surface="#e6e9ef",
            overlay="#ccd0da",
            text="#4c4f69",
            subtext="#6c6f85",
            primary="#1e66f5",
            success="#40a02b",
            warning="#df8e1d",
            error="#d20f39"
        )
    }
    fonts: Dict[str, str] = {
        "heading": "Inter",
        "body": "Inter",
        "mono": "JetBrains Mono"
    }
    overlays: Dict[str, Any] = {
        "bbox_thickness": 2,
        "bbox_alpha": 0.8,
        "zone_alpha": 0.3,
        "trajectory_length": 2.0
    }
    telemetry: Dict[str, float] = {
        "update_interval": 1.0,
        "chart_window": 60.0
    }


class RecordingConfig(BaseModel):
    """Konfigurace nahrávání"""
    save_directory: str = "~/PersonTracker/recordings"
    format: Literal["mp4", "mkv", "avi"] = "mp4"
    quality: Literal["stream", "high"] = "stream"
    include_overlays: bool = True
    include_telemetry: bool = True
    auto_record: bool = False


class DebugConfig(BaseModel):
    """Konfigurace debugování"""
    show_fps: bool = True
    show_latency: bool = True
    show_mini_map: bool = True
    save_frames: bool = False
    save_detections: bool = False
    profiling: bool = False


class AppConfig(BaseModel):
    """Hlavní konfigurace aplikace"""
    name: str = "Person Tracker"
    version: str = "1.0.0"
    language: Literal["cs", "en"] = "cs"
    theme: Literal["dark", "light"] = "dark"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class Config(BaseModel):
    """Kompletní konfigurace aplikace"""
    app: AppConfig = Field(default_factory=AppConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    distance: DistanceConfig = Field(default_factory=DistanceConfig)
    control: ControlConfig = Field(default_factory=ControlConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)

    @classmethod
    def load_from_yaml(cls, path: Path) -> "Config":
        """Načte konfiguraci ze YAML souboru"""
        logger.info(f"Načítám konfiguraci z {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def save_to_yaml(self, path: Path):
        """Uloží konfiguraci do YAML souboru"""
        logger.info(f"Ukládám konfiguraci do {path}")
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, allow_unicode=True)

    def merge_with_user_config(self, user_config_path: Path) -> "Config":
        """Sloučí výchozí konfiguraci s uživatelskou"""
        if not user_config_path.exists():
            logger.info("Uživatelská konfigurace nenalezena, používám výchozí")
            return self

        logger.info(f"Slučuji s uživatelskou konfigurací z {user_config_path}")
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_data = yaml.safe_load(f)

        # Rekurzivní sloučení
        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        merged_data = deep_merge(self.model_dump(), user_data)
        return Config(**merged_data)


class RobotProfile(BaseModel):
    """Profil připojení k robotu"""
    name: str
    ip: str
    port: int = 22
    username: str = "pi"
    ssh_key_path: Optional[str] = None
    password: Optional[str] = None
    video_port: int = 8554
    command_port: int = 5555
    telemetry_port: int = 5556
    last_used: Optional[str] = None
    notes: str = ""

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, v):
        """Validace IP adresy"""
        parts = v.split('.')
        if len(parts) != 4:
            raise ValueError('Neplatná IP adresa')
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                raise ValueError('Neplatná IP adresa')
        return v


class ProfileManager:
    """Správce profilů robotů"""

    def __init__(self, profiles_path: Path):
        self.profiles_path = profiles_path
        self.profiles: List[RobotProfile] = []
        self.load_profiles()

    def load_profiles(self):
        """Načte profily ze souboru"""
        if not self.profiles_path.exists():
            logger.warning(f"Soubor s profily nenalezen: {self.profiles_path}")
            self.profiles = []
            return

        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.profiles = [RobotProfile(**p) for p in data.get('profiles', [])]
            logger.info(f"Načteno {len(self.profiles)} profilů")
        except Exception as e:
            logger.error(f"Chyba při načítání profilů: {e}")
            self.profiles = []

    def save_profiles(self):
        """Uloží profily do souboru"""
        try:
            self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                data = {"profiles": [p.model_dump() for p in self.profiles]}
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Uloženo {len(self.profiles)} profilů")
        except Exception as e:
            logger.error(f"Chyba při ukládání profilů: {e}")

    def add_profile(self, profile: RobotProfile):
        """Přidá nový profil"""
        self.profiles.append(profile)
        self.save_profiles()
        logger.info(f"Přidán profil: {profile.name}")

    def update_profile(self, name: str, updated_profile: RobotProfile):
        """Aktualizuje existující profil"""
        for i, p in enumerate(self.profiles):
            if p.name == name:
                self.profiles[i] = updated_profile
                self.save_profiles()
                logger.info(f"Aktualizován profil: {name}")
                return
        logger.warning(f"Profil nenalezen: {name}")

    def delete_profile(self, name: str):
        """Smaže profil"""
        self.profiles = [p for p in self.profiles if p.name != name]
        self.save_profiles()
        logger.info(f"Smazán profil: {name}")

    def get_profile(self, name: str) -> Optional[RobotProfile]:
        """Vrátí profil podle jména"""
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    def get_last_used_profile(self) -> Optional[RobotProfile]:
        """Vrátí naposledy použitý profil"""
        if not self.profiles:
            return None
        sorted_profiles = sorted(
            [p for p in self.profiles if p.last_used],
            key=lambda x: x.last_used,
            reverse=True
        )
        return sorted_profiles[0] if sorted_profiles else self.profiles[0]


# Globální instance konfigurace
_config: Optional[Config] = None


def get_config() -> Config:
    """Vrátí globální instanci konfigurace"""
    global _config
    if _config is None:
        raise RuntimeError("Konfigurace nebyla inicializována")
    return _config


def init_config(config_path: Optional[Path] = None, user_config_path: Optional[Path] = None) -> Config:
    """Inicializuje globální konfiguraci"""
    global _config

    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"

    _config = Config.load_from_yaml(config_path)

    if user_config_path and user_config_path.exists():
        _config = _config.merge_with_user_config(user_config_path)

    logger.info(f"Konfigurace inicializována: {_config.app.name} v{_config.app.version}")
    return _config
