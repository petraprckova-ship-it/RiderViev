"""
Distance estimation - odhad vzdálenosti k osobě
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class DistanceInfo:
    """Informace o vzdálenosti k osobě"""
    distance: float  # metry
    method: str  # bbox, depth, fusion
    confidence: float  # 0.0 - 1.0
    bbox_height: Optional[float] = None
    depth_value: Optional[float] = None


class BBoxDistanceEstimator:
    """
    Odhad vzdálenosti na základě výšky bounding boxu
    Používá pinhole camera model
    """

    def __init__(
        self,
        focal_length: Optional[float] = None,
        avg_person_height: float = 1.7,
        image_height: int = 480
    ):
        """
        Args:
            focal_length: Ohnisková vzdálenost kamery (px), None = auto-kalibrace
            avg_person_height: Průměrná výška osoby v metrech
            image_height: Výška snímku v pixelech
        """
        self.focal_length = focal_length
        self.avg_person_height = avg_person_height
        self.image_height = image_height

        # Pokud není focal_length, použij odhad (FOV ~60°)
        if self.focal_length is None:
            self.focal_length = image_height / (2 * np.tan(np.deg2rad(30)))
            logger.info(f"Odhadnutá focal length: {self.focal_length:.1f}px")

    def estimate(self, bbox: np.ndarray, confidence: float = 0.7) -> DistanceInfo:
        """
        Odhadni vzdálenost z výšky bbox

        Args:
            bbox: [x1, y1, x2, y2]
            confidence: Confidence detekce

        Returns:
            DistanceInfo
        """
        bbox_height = bbox[3] - bbox[1]

        # Pinhole model: distance = (real_height * focal_length) / image_height
        distance = (self.avg_person_height * self.focal_length) / bbox_height

        # Confidence snižuj pro velmi malé nebo velké boxy
        bbox_confidence = confidence
        if bbox_height < self.image_height * 0.1:  # Příliš malý box
            bbox_confidence *= 0.5
        elif bbox_height > self.image_height * 0.9:  # Příliš velký box
            bbox_confidence *= 0.7

        return DistanceInfo(
            distance=distance,
            method="bbox",
            confidence=bbox_confidence,
            bbox_height=bbox_height
        )

    def calibrate(self, measured_distance: float, bbox_height: float):
        """
        Kalibruj focal length ze známé vzdálenosti

        Args:
            measured_distance: Skutečná vzdálenost v metrech
            bbox_height: Výška bbox v pixelech při této vzdálenosti
        """
        # focal_length = (distance * bbox_height) / real_height
        self.focal_length = (measured_distance * bbox_height) / self.avg_person_height
        logger.success(f"Focal length nakalibrována: {self.focal_length:.1f}px")


class DepthMapDistanceEstimator:
    """
    Odhad vzdálenosti z depth mapy (Depth-Anything-V2 nebo MiDaS)
    """

    def __init__(self, depth_scale: float = 1.0):
        """
        Args:
            depth_scale: Škálovací faktor pro převod depth hodnot na metry
        """
        self.depth_scale = depth_scale
        self.depth_model = None  # Načte se lazy

    def estimate(
        self,
        bbox: np.ndarray,
        depth_map: np.ndarray,
        confidence: float = 0.8
    ) -> DistanceInfo:
        """
        Odhadni vzdálenost z depth mapy

        Args:
            bbox: [x1, y1, x2, y2]
            depth_map: Depth mapa (H, W)
            confidence: Confidence detekce

        Returns:
            DistanceInfo
        """
        # Extrahuj ROI z depth mapy
        x1, y1, x2, y2 = bbox.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2 = min(depth_map.shape[1], x2)
        y2 = min(depth_map.shape[0], y2)

        roi_depth = depth_map[y1:y2, x1:x2]

        if roi_depth.size == 0:
            logger.warning("Prázdný ROI pro depth estimation")
            return DistanceInfo(distance=0, method="depth", confidence=0)

        # Použij medián pro robustnost vůči outlierům
        median_depth = np.median(roi_depth)

        # Konverze na metry
        distance = median_depth * self.depth_scale

        # Variabilita v ROI snižuje confidence
        depth_std = np.std(roi_depth)
        depth_confidence = confidence * np.exp(-depth_std / median_depth)

        return DistanceInfo(
            distance=distance,
            method="depth",
            confidence=depth_confidence,
            depth_value=median_depth
        )

    def calibrate_scale(self, measured_distance: float, depth_value: float):
        """
        Kalibruj depth scale ze známé vzdálenosti

        Args:
            measured_distance: Skutečná vzdálenost v metrech
            depth_value: Depth hodnota při této vzdálenosti
        """
        self.depth_scale = measured_distance / depth_value
        logger.success(f"Depth scale nakalibrována: {self.depth_scale:.4f}")


class FusionDistanceEstimator:
    """
    Sensor fusion - kombinuje bbox a depth metody
    """

    def __init__(
        self,
        bbox_estimator: BBoxDistanceEstimator,
        depth_estimator: Optional[DepthMapDistanceEstimator] = None,
        bbox_weight: float = 0.3,
        depth_weight: float = 0.7
    ):
        """
        Args:
            bbox_estimator: BBox estimátor
            depth_estimator: Depth estimátor (optional)
            bbox_weight: Váha bbox odhadu
            depth_weight: Váha depth odhadu
        """
        self.bbox_estimator = bbox_estimator
        self.depth_estimator = depth_estimator
        self.bbox_weight = bbox_weight
        self.depth_weight = depth_weight

        # Normalizuj váhy
        total_weight = bbox_weight + (depth_weight if depth_estimator else 0)
        self.bbox_weight /= total_weight
        if depth_estimator:
            self.depth_weight /= total_weight
        else:
            self.depth_weight = 0

    def estimate(
        self,
        bbox: np.ndarray,
        confidence: float,
        depth_map: Optional[np.ndarray] = None
    ) -> DistanceInfo:
        """
        Odhadni vzdálenost pomocí fusion

        Args:
            bbox: [x1, y1, x2, y2]
            confidence: Confidence detekce
            depth_map: Depth mapa (optional)

        Returns:
            DistanceInfo
        """
        # BBox odhad (vždy k dispozici)
        bbox_info = self.bbox_estimator.estimate(bbox, confidence)

        # Pokud není depth estimator nebo depth mapa, použij jen bbox
        if self.depth_estimator is None or depth_map is None:
            return bbox_info

        # Depth odhad
        depth_info = self.depth_estimator.estimate(bbox, depth_map, confidence)

        # Fusion
        fused_distance = (
            self.bbox_weight * bbox_info.distance +
            self.depth_weight * depth_info.distance
        )

        # Fusion confidence (průměr vážený confidence)
        fused_confidence = (
            self.bbox_weight * bbox_info.confidence +
            self.depth_weight * depth_info.confidence
        )

        return DistanceInfo(
            distance=fused_distance,
            method="fusion",
            confidence=fused_confidence,
            bbox_height=bbox_info.bbox_height,
            depth_value=depth_info.depth_value
        )


class DistanceTracker:
    """
    Sleduje vzdálenost s filtrací pro plynulé hodnoty
    """

    def __init__(self, smoothing: float = 0.3, history_size: int = 10):
        """
        Args:
            smoothing: EMA smoothing factor (0-1, vyšší = více smoothing)
            history_size: Velikost historie pro medián filtr
        """
        self.smoothing = smoothing
        self.history_size = history_size
        self.distance_history = []
        self.smoothed_distance: Optional[float] = None

    def update(self, distance: float) -> float:
        """
        Aktualizuj s novou vzdáleností

        Args:
            distance: Naměřená vzdálenost

        Returns:
            Vyhlazená vzdálenost
        """
        # Přidej do historie
        self.distance_history.append(distance)
        if len(self.distance_history) > self.history_size:
            self.distance_history.pop(0)

        # Medián filtr pro odstranění outlierů
        median_distance = np.median(self.distance_history)

        # EMA smoothing
        if self.smoothed_distance is None:
            self.smoothed_distance = median_distance
        else:
            self.smoothed_distance = (
                self.smoothing * self.smoothed_distance +
                (1 - self.smoothing) * median_distance
            )

        return self.smoothed_distance

    def reset(self):
        """Reset trackeru"""
        self.distance_history.clear()
        self.smoothed_distance = None

    def get_distance(self) -> Optional[float]:
        """Získej aktuální vzdálenost"""
        return self.smoothed_distance

    def get_velocity(self) -> Optional[float]:
        """
        Získej rychlost změny vzdálenosti (m/s)
        Předpokládá update rate ~30Hz
        """
        if len(self.distance_history) < 2:
            return None

        # Derivace vzdálenosti
        dt = 1.0 / 30.0  # Předpokládáme 30 FPS
        velocity = (self.distance_history[-1] - self.distance_history[-2]) / dt

        return velocity


class ZoneClassifier:
    """
    Klasifikace vzdálenosti do bezpečnostních zón
    """

    def __init__(
        self,
        red_zone: float = 0.30,
        yellow_zone: float = 0.60,
        target_min: float = 1.0,
        target_max: float = 2.5
    ):
        """
        Args:
            red_zone: Vzdálenost pro červenou zónu (m)
            yellow_zone: Vzdálenost pro žlutou zónu (m)
            target_min: Minimální cílová vzdálenost (m)
            target_max: Maximální cílová vzdálenost (m)
        """
        self.red_zone = red_zone
        self.yellow_zone = yellow_zone
        self.target_min = target_min
        self.target_max = target_max

    def classify(self, distance: float) -> Tuple[str, str]:
        """
        Klasifikuj vzdálenost

        Args:
            distance: Vzdálenost v metrech

        Returns:
            (zone_color, zone_name) např. ("red", "emergency_stop")
        """
        if distance < self.red_zone:
            return "red", "emergency_stop"
        elif distance < self.yellow_zone:
            return "yellow", "slow_down"
        elif distance < self.target_min:
            return "orange", "too_close"
        elif distance <= self.target_max:
            return "green", "optimal"
        else:
            return "blue", "too_far"

    def get_zone_action(self, distance: float) -> str:
        """
        Získej akci pro danou zónu

        Args:
            distance: Vzdálenost v metrech

        Returns:
            Akce: stop, slow, maintain, approach
        """
        zone_color, zone_name = self.classify(distance)

        if zone_name == "emergency_stop":
            return "stop"
        elif zone_name == "slow_down":
            return "slow"
        elif zone_name == "too_close":
            return "reverse"
        elif zone_name == "optimal":
            return "maintain"
        else:  # too_far
            return "approach"

    def get_speed_multiplier(self, distance: float) -> float:
        """
        Získej multiplikátor rychlosti pro danou vzdálenost

        Args:
            distance: Vzdálenost v metrech

        Returns:
            Multiplikátor rychlosti (0.0 - 1.0)
        """
        zone_color, zone_name = self.classify(distance)

        if zone_name == "emergency_stop":
            return 0.0
        elif zone_name == "slow_down":
            # Lineární snižování rychlosti v žluté zóně
            ratio = (distance - self.red_zone) / (self.yellow_zone - self.red_zone)
            return 0.3 * ratio
        elif zone_name == "too_close":
            return 0.5
        elif zone_name == "optimal":
            return 1.0
        else:  # too_far
            # Lineární zvyšování rychlosti pokud je příliš daleko
            overshoot = distance - self.target_max
            if overshoot < 1.0:
                return 1.0
            else:
                return min(1.0, 1.0 + overshoot * 0.1)
