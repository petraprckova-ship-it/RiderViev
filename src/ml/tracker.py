"""
ByteTrack tracker pro robustní sledování osob
"""

import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from collections import deque
from loguru import logger
from filterpy.kalman import KalmanFilter
import lap

from .detector import Detection


@dataclass
class Track:
    """Sledovaná osoba s historií"""
    track_id: int
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    age: int = 0  # Počet snímků od začátku tracku
    hits: int = 1  # Počet úspěšných detekcí
    time_since_update: int = 0  # Počet snímků od poslední detekce
    state: str = "tentative"  # tentative, confirmed, lost
    history: deque = field(default_factory=lambda: deque(maxlen=30))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2))
    kalman_filter: Optional[KalmanFilter] = None

    def __post_init__(self):
        """Inicializuj Kalman filter"""
        self.kalman_filter = self._init_kalman_filter()
        self.history.append(self.bbox.copy())

    def _init_kalman_filter(self) -> KalmanFilter:
        """
        Inicializuj Kalman filter pro sledování bbox
        State: [x_center, y_center, width, height, vx, vy, vw, vh]
        """
        kf = KalmanFilter(dim_x=8, dim_z=4)

        # State transition matrix (konstantní velocity model)
        kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0, 0],
            [0, 1, 0, 0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 1]
        ])

        # Measurement matrix (měříme pouze pozici a velikost, ne rychlost)
        kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 0]
        ])

        # Process noise
        kf.Q *= 0.01

        # Measurement noise
        kf.R *= 10.0

        # Initial covariance
        kf.P *= 10.0

        # Inicializuj state
        bbox_xywh = self._bbox_to_xywh(self.bbox)
        kf.x[:4, 0] = bbox_xywh
        kf.x[4:, 0] = 0  # Nulová počáteční rychlost

        return kf

    @staticmethod
    def _bbox_to_xywh(bbox: np.ndarray) -> np.ndarray:
        """Konverze [x1, y1, x2, y2] -> [x_center, y_center, width, height]"""
        x1, y1, x2, y2 = bbox
        return np.array([
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            x2 - x1,
            y2 - y1
        ])

    @staticmethod
    def _xywh_to_bbox(xywh: np.ndarray) -> np.ndarray:
        """Konverze [x_center, y_center, width, height] -> [x1, y1, x2, y2]"""
        x, y, w, h = xywh
        return np.array([
            x - w / 2,
            y - h / 2,
            x + w / 2,
            y + h / 2
        ])

    def predict(self):
        """Predikce dalšího stavu pomocí Kalman filtru"""
        self.kalman_filter.predict()
        self.age += 1
        self.time_since_update += 1

        # Aktualizuj bbox z predikce
        predicted_xywh = self.kalman_filter.x[:4, 0]  # Flatten 2D to 1D
        self.bbox = self._xywh_to_bbox(predicted_xywh)

        # Extrahuj rychlost
        self.velocity = self.kalman_filter.x[4:6, 0].copy()  # Flatten

    def update(self, detection: Detection):
        """Aktualizuj track s novou detekcí"""
        self.time_since_update = 0
        self.hits += 1
        self.confidence = detection.confidence

        # Aktualizuj Kalman filter
        measurement = self._bbox_to_xywh(np.array(detection.bbox))
        self.kalman_filter.update(measurement)

        # Aktualizuj bbox
        updated_xywh = self.kalman_filter.x[:4, 0]  # Flatten
        self.bbox = self._xywh_to_bbox(updated_xywh)

        # Aktualizuj historii
        self.history.append(self.bbox.copy())

        # Aktualizuj stav
        if self.state == "tentative" and self.hits >= 3:
            self.state = "confirmed"

    def mark_missed(self):
        """Označ track jako zmeškaný (žádná detekce v tomto snímku)"""
        self.time_since_update += 1
        if self.time_since_update > 1:
            self.state = "lost"

    def is_confirmed(self) -> bool:
        """Je track potvrzený?"""
        return self.state == "confirmed"

    def is_lost(self) -> bool:
        """Je track ztracený?"""
        return self.state == "lost"

    def get_predicted_bbox(self, steps: int = 1) -> np.ndarray:
        """
        Získej predikovaný bbox o N kroků dopředu

        Args:
            steps: Počet kroků do budoucnosti

        Returns:
            Predikovaný bbox [x1, y1, x2, y2]
        """
        # Jednoduchá lineární predikce
        current_xywh = self._bbox_to_xywh(self.bbox)
        predicted_xywh = current_xywh.copy()
        predicted_xywh[:2] += self.velocity * steps  # Pouze pozice se mění

        return self._xywh_to_bbox(predicted_xywh)

    @property
    def center(self) -> np.ndarray:
        """Střed bbox"""
        return np.array([
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2
        ])


def iou_batch(bboxes_a: np.ndarray, bboxes_b: np.ndarray) -> np.ndarray:
    """
    Vypočítej IoU mezi dvěma sadami bboxů

    Args:
        bboxes_a: Shape (N, 4) ve formátu [x1, y1, x2, y2]
        bboxes_b: Shape (M, 4) ve formátu [x1, y1, x2, y2]

    Returns:
        IoU matice Shape (N, M)
    """
    if len(bboxes_a) == 0 or len(bboxes_b) == 0:
        return np.zeros((len(bboxes_a), len(bboxes_b)))

    # Zajisti 2D arrays
    bboxes_a = np.atleast_2d(bboxes_a)
    bboxes_b = np.atleast_2d(bboxes_b)

    # Expand dimensions pro broadcasting
    bboxes_a = np.expand_dims(bboxes_a, axis=1)  # (N, 1, 4)
    bboxes_b = np.expand_dims(bboxes_b, axis=0)  # (1, M, 4)

    # Průsečík
    xx1 = np.maximum(bboxes_a[..., 0], bboxes_b[..., 0])
    yy1 = np.maximum(bboxes_a[..., 1], bboxes_b[..., 1])
    xx2 = np.minimum(bboxes_a[..., 2], bboxes_b[..., 2])
    yy2 = np.minimum(bboxes_a[..., 3], bboxes_b[..., 3])

    w = np.maximum(0.0, xx2 - xx1)
    h = np.maximum(0.0, yy2 - yy1)
    intersection = w * h

    # Plochy
    area_a = (bboxes_a[..., 2] - bboxes_a[..., 0]) * (bboxes_a[..., 3] - bboxes_a[..., 1])
    area_b = (bboxes_b[..., 2] - bboxes_b[..., 0]) * (bboxes_b[..., 3] - bboxes_b[..., 1])

    # IoU
    union = area_a + area_b - intersection
    iou = intersection / np.maximum(union, 1e-6)

    return iou.squeeze()


class ByteTracker:
    """
    ByteTrack algoritmus pro multi-object tracking
    """

    def __init__(
        self,
        track_buffer: int = 30,
        match_threshold: float = 0.8,
        min_track_length: int = 3,
        high_conf_threshold: float = 0.6,
        low_conf_threshold: float = 0.3
    ):
        """
        Args:
            track_buffer: Kolik snímků udržovat ztracené tracky
            match_threshold: IoU threshold pro matching
            min_track_length: Minimální délka tracku pro potvrzení
            high_conf_threshold: Threshold pro high-confidence detekce
            low_conf_threshold: Threshold pro low-confidence detekce
        """
        self.track_buffer = track_buffer
        self.match_threshold = match_threshold
        self.min_track_length = min_track_length
        self.high_conf_threshold = high_conf_threshold
        self.low_conf_threshold = low_conf_threshold

        self.tracks: List[Track] = []
        self.next_track_id = 1
        self.frame_id = 0

    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Aktualizuj tracker s novými detekcemi

        Args:
            detections: Seznam detekcí z aktuálního snímku

        Returns:
            Seznam aktivních tracků
        """
        self.frame_id += 1

        # Predikce pro všechny existující tracky
        for track in self.tracks:
            track.predict()

        # Rozdělení detekcí na high a low confidence
        high_conf_dets = [d for d in detections if d.confidence >= self.high_conf_threshold]
        low_conf_dets = [
            d for d in detections
            if self.low_conf_threshold <= d.confidence < self.high_conf_threshold
        ]

        # 1. Přiřazení high-confidence detekcí k confirmed tracks
        confirmed_tracks = [t for t in self.tracks if t.is_confirmed()]
        unmatched_tracks_1, unmatched_dets_1 = self._match_detections_to_tracks(
            high_conf_dets, confirmed_tracks
        )

        # 2. Přiřazení zbylých low-confidence detekcí k unmatched confirmed tracks
        unmatched_tracks_2, unmatched_dets_2 = self._match_detections_to_tracks(
            low_conf_dets, unmatched_tracks_1, threshold=0.5
        )

        # 3. Přiřazení zbylých high-confidence detekcí k tentative tracks
        tentative_tracks = [t for t in self.tracks if t.state == "tentative"]
        unmatched_tracks_3, unmatched_dets_3 = self._match_detections_to_tracks(
            unmatched_dets_1, tentative_tracks
        )

        # 4. Vytvoření nových tracků z nepoužitých high-confidence detekcí
        for det in unmatched_dets_3:
            self._init_track(det)

        # Označení nepoužitých tracků jako missed
        for track in unmatched_tracks_2:
            track.mark_missed()

        # Odstranění starých ztracených tracků
        self.tracks = [
            t for t in self.tracks
            if t.time_since_update <= self.track_buffer
        ]

        # Vrať pouze confirmed tracky
        return [t for t in self.tracks if t.is_confirmed()]

    def _match_detections_to_tracks(
        self,
        detections: List[Detection],
        tracks: List[Track],
        threshold: Optional[float] = None
    ) -> tuple:
        """
        Přiřaď detekce k trackům pomocí Hungarian algorithm

        Args:
            detections: Seznam detekcí
            tracks: Seznam tracků
            threshold: IoU threshold (použije self.match_threshold pokud None)

        Returns:
            (unmatched_tracks, unmatched_detections)
        """
        if threshold is None:
            threshold = self.match_threshold

        if len(detections) == 0:
            return tracks, []

        if len(tracks) == 0:
            return [], detections

        # Vytvoř IoU cost matrix
        det_bboxes = np.array([d.bbox for d in detections])
        track_bboxes = np.array([t.bbox for t in tracks])

        iou_matrix = iou_batch(track_bboxes, det_bboxes)

        # Konverze na cost matrix (1 - IoU)
        cost_matrix = 1.0 - iou_matrix

        # Hungarian algorithm pro optimální přiřazení
        if cost_matrix.size > 0:
            row_indices, col_indices = lap.lapjv(
                cost_matrix,
                extend_cost=True,
                cost_limit=1.0 - threshold
            )[:2]

            # Zpracuj přiřazení
            matched_tracks = set()
            matched_dets = set()

            for track_idx, det_idx in enumerate(col_indices):
                if det_idx >= 0:  # Validní match
                    cost = cost_matrix[track_idx, det_idx]
                    if cost < 1.0 - threshold:
                        tracks[track_idx].update(detections[det_idx])
                        matched_tracks.add(track_idx)
                        matched_dets.add(det_idx)

            # Unmatched tracky a detekce
            unmatched_tracks = [t for i, t in enumerate(tracks) if i not in matched_tracks]
            unmatched_dets = [d for i, d in enumerate(detections) if i not in matched_dets]

            return unmatched_tracks, unmatched_dets

        return tracks, detections

    def _init_track(self, detection: Detection):
        """Vytvoř nový track z detekce"""
        track = Track(
            track_id=self.next_track_id,
            bbox=detection.bbox.copy(),
            confidence=detection.confidence
        )
        self.tracks.append(track)
        self.next_track_id += 1
        logger.debug(f"Vytvořen nový track ID: {track.track_id}")

    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        """Získej track podle ID"""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None

    def get_all_tracks(self) -> List[Track]:
        """Získej všechny tracky (včetně tentative a lost)"""
        return self.tracks

    def reset(self):
        """Reset trackeru"""
        self.tracks.clear()
        self.next_track_id = 1
        self.frame_id = 0
        logger.info("Tracker resetován")


class TargetSelector:
    """
    Výběr primárního cíle ze seznamu tracků
    """

    def __init__(
        self,
        frame_center: Optional[tuple] = None,
        center_bias: float = 1.0,
        confidence_bias: float = 0.3,
        size_bias: float = 0.2,
        continuity_bias: float = 2.0
    ):
        """
        Args:
            frame_center: Střed snímku (x, y)
            center_bias: Váha pro vzdálenost od středu
            confidence_bias: Váha pro confidence score
            size_bias: Váha pro velikost bbox
            continuity_bias: Váha pro kontinuitu (preferuj současný target)
        """
        self.frame_center = frame_center or (320, 240)
        self.center_bias = center_bias
        self.confidence_bias = confidence_bias
        self.size_bias = size_bias
        self.continuity_bias = continuity_bias
        self.current_target_id: Optional[int] = None

    def select_target(self, tracks: List[Track]) -> Optional[Track]:
        """
        Vyber primární cíl k sledování

        Args:
            tracks: Seznam tracků

        Returns:
            Vybraný track nebo None
        """
        if len(tracks) == 0:
            self.current_target_id = None
            return None

        if len(tracks) == 1:
            self.current_target_id = tracks[0].track_id
            return tracks[0]

        # Vypočítej score pro každý track
        scores = []
        for track in tracks:
            score = self._compute_target_score(track)
            scores.append(score)

        # Vyber track s nejvyšším score
        best_idx = np.argmax(scores)
        best_track = tracks[best_idx]
        self.current_target_id = best_track.track_id

        return best_track

    def _compute_target_score(self, track: Track) -> float:
        """Vypočítej score pro track"""
        # Distance od středu (normalizováno)
        center_dist = np.linalg.norm(track.center - np.array(self.frame_center))
        max_dist = np.linalg.norm(np.array(self.frame_center))
        center_score = 1.0 - (center_dist / max_dist)

        # Confidence score
        conf_score = track.confidence

        # Size score (normalizováno k celému snímku)
        bbox_area = (track.bbox[2] - track.bbox[0]) * (track.bbox[3] - track.bbox[1])
        frame_area = self.frame_center[0] * self.frame_center[1] * 4
        size_score = np.clip(bbox_area / frame_area, 0, 1)

        # Continuity score
        cont_score = 1.0 if track.track_id == self.current_target_id else 0.0

        # Celkový score
        total_score = (
            self.center_bias * center_score +
            self.confidence_bias * conf_score +
            self.size_bias * size_score +
            self.continuity_bias * cont_score
        )

        return total_score

    def set_frame_center(self, center: tuple):
        """Nastav střed snímku"""
        self.frame_center = center
