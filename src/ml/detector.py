"""
YOLO11 Person Detector s TensorRT optimalizací
"""

import numpy as np
import torch
from ultralytics import YOLO
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import time


@dataclass
class Detection:
    """Detekce jedné osoby"""
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    class_id: int = 0  # 0 = person v COCO datasetu
    class_name: str = "person"

    @property
    def center(self) -> Tuple[float, float]:
        """Střed bounding boxu"""
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2
        )

    @property
    def width(self) -> float:
        """Šířka bounding boxu"""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        """Výška bounding boxu"""
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        """Plocha bounding boxu"""
        return self.width * self.height

    def to_xyxy(self) -> np.ndarray:
        """Vrátí bbox ve formátu [x1, y1, x2, y2]"""
        return self.bbox

    def to_xywh(self) -> np.ndarray:
        """Vrátí bbox ve formátu [x_center, y_center, width, height]"""
        return np.array([
            self.center[0],
            self.center[1],
            self.width,
            self.height
        ])

    def to_ltwh(self) -> np.ndarray:
        """Vrátí bbox ve formátu [left, top, width, height]"""
        return np.array([
            self.bbox[0],
            self.bbox[1],
            self.width,
            self.height
        ])


class PersonDetector:
    """
    YOLO11 detektor osob s podporou TensorRT, ONNX a PyTorch
    """

    def __init__(
        self,
        model_name: str = "yolo11s",
        device: str = "cuda:0",
        backend: str = "tensorrt",
        fp16: bool = True,
        confidence_threshold: float = 0.5,
        nms_iou_threshold: float = 0.45,
        model_dir: Optional[Path] = None
    ):
        """
        Args:
            model_name: Jméno modelu (yolo11n, yolo11s, yolo11m)
            device: Zařízení (cuda:0, cpu)
            backend: Backend pro inferenci (tensorrt, onnx, pytorch)
            fp16: Použít FP16 precision
            confidence_threshold: Minimální confidence pro detekci
            nms_iou_threshold: IoU threshold pro NMS
            model_dir: Adresář s modely
        """
        self.model_name = model_name
        self.device = device
        self.backend = backend
        self.fp16 = fp16
        self.confidence_threshold = confidence_threshold
        self.nms_iou_threshold = nms_iou_threshold

        if model_dir is None:
            model_dir = Path(__file__).parent.parent.parent / "models"
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.input_size = (640, 640)
        self.inference_time = 0.0

        self._load_model()

    def _load_model(self):
        """Načte YOLO model"""
        logger.info(f"Načítám YOLO model: {self.model_name} na {self.device} s backendem {self.backend}")

        try:
            # Základní model
            model_path = self.model_dir / f"{self.model_name}.pt"

            if not model_path.exists():
                logger.info(f"Stahuji model {self.model_name}...")
                self.model = YOLO(f"{self.model_name}.pt")
                # Model se automaticky stáhne do ~/.ultralytics/
            else:
                self.model = YOLO(str(model_path))

            # Export do optimalizovaného formátu
            if self.backend == "tensorrt":
                self._export_tensorrt()
            elif self.backend == "onnx":
                self._export_onnx()

            logger.success(f"Model {self.model_name} úspěšně načten")

        except Exception as e:
            logger.error(f"Chyba při načítání modelu: {e}")
            raise

    def _export_tensorrt(self):
        """Export do TensorRT"""
        trt_path = self.model_dir / f"{self.model_name}{'_fp16' if self.fp16 else '_fp32'}.engine"

        if trt_path.exists():
            logger.info(f"Používám existující TensorRT engine: {trt_path}")
            self.model = YOLO(str(trt_path))
        else:
            logger.info("Exportuji do TensorRT (může trvat několik minut)...")
            try:
                self.model.export(
                    format="engine",
                    device=self.device,
                    half=self.fp16,
                    simplify=True
                )
                logger.success("Export do TensorRT dokončen")
            except Exception as e:
                logger.warning(f"TensorRT export selhal: {e}, používám PyTorch")
                self.backend = "pytorch"

    def _export_onnx(self):
        """Export do ONNX"""
        onnx_path = self.model_dir / f"{self.model_name}.onnx"

        if onnx_path.exists():
            logger.info(f"Používám existující ONNX model: {onnx_path}")
            self.model = YOLO(str(onnx_path))
        else:
            logger.info("Exportuji do ONNX...")
            try:
                self.model.export(
                    format="onnx",
                    simplify=True,
                    opset=12
                )
                logger.success("Export do ONNX dokončen")
            except Exception as e:
                logger.warning(f"ONNX export selhal: {e}, používám PyTorch")
                self.backend = "pytorch"

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detekuj osoby v obrazu

        Args:
            frame: RGB obraz ve formátu (H, W, 3)

        Returns:
            Seznam detekcí osob
        """
        start_time = time.perf_counter()

        try:
            # YOLO inference
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                iou=self.nms_iou_threshold,
                classes=[0],  # Pouze třída "person"
                device=self.device,
                verbose=False,
                half=self.fp16
            )

            # Parsování výsledků
            detections = []
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    bbox = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())

                    detection = Detection(
                        bbox=bbox,
                        confidence=conf,
                        class_id=cls,
                        class_name="person"
                    )
                    detections.append(detection)

            self.inference_time = (time.perf_counter() - start_time) * 1000  # ms

            return detections

        except Exception as e:
            logger.error(f"Chyba při detekci: {e}")
            return []

    def warmup(self, iterations: int = 10):
        """
        Zahřej model několika prázdnými běhy

        Args:
            iterations: Počet warmup iterací
        """
        logger.info(f"Zahřívám model ({iterations} iterací)...")
        dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)

        for i in range(iterations):
            self.detect(dummy_input)

        logger.success(f"Model zahřátý, průměrný čas: {self.inference_time:.1f}ms")

    def get_fps(self) -> float:
        """Vrátí odhadované FPS na základě posledního inference času"""
        if self.inference_time > 0:
            return 1000.0 / self.inference_time
        return 0.0

    def update_thresholds(self, confidence: Optional[float] = None, nms_iou: Optional[float] = None):
        """
        Aktualizuj detection thresholdy

        Args:
            confidence: Nový confidence threshold
            nms_iou: Nový NMS IoU threshold
        """
        if confidence is not None:
            self.confidence_threshold = confidence
            logger.info(f"Confidence threshold nastaven na {confidence}")

        if nms_iou is not None:
            self.nms_iou_threshold = nms_iou
            logger.info(f"NMS IoU threshold nastaven na {nms_iou}")


class AdaptiveDetector:
    """
    Adaptivní detektor, který automaticky přepíná mezi modely podle výkonu
    """

    def __init__(
        self,
        device: str = "cuda:0",
        target_fps: float = 25.0,
        **kwargs
    ):
        """
        Args:
            device: Zařízení (cuda:0, cpu)
            target_fps: Cílové FPS
            **kwargs: Další parametry pro PersonDetector
        """
        self.device = device
        self.target_fps = target_fps

        # Seznam modelů od nejrychlejšího
        self.models = ["yolo11n", "yolo11s", "yolo11m"]
        self.current_model_idx = 1  # Začínáme s yolo11s

        self.detector = PersonDetector(
            model_name=self.models[self.current_model_idx],
            device=device,
            **kwargs
        )

        self.fps_history = []
        self.fps_window = 30  # Průměr za posledních 30 snímků
        self.check_interval = 100  # Kontroluj každých 100 snímků
        self.frame_count = 0

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detekce s automatickou adaptací"""
        detections = self.detector.detect(frame)

        self.frame_count += 1
        current_fps = self.detector.get_fps()
        self.fps_history.append(current_fps)

        # Udržuj historii jen za poslední window
        if len(self.fps_history) > self.fps_window:
            self.fps_history.pop(0)

        # Kontroluj výkon
        if self.frame_count % self.check_interval == 0:
            self._check_performance()

        return detections

    def _check_performance(self):
        """Zkontroluj výkon a případně přepni model"""
        if len(self.fps_history) < self.fps_window:
            return

        avg_fps = np.mean(self.fps_history)
        logger.debug(f"Průměrné FPS: {avg_fps:.1f}, Cílové: {self.target_fps}")

        # Pokud je FPS příliš nízké a můžeme použít rychlejší model
        if avg_fps < self.target_fps * 0.9 and self.current_model_idx > 0:
            self.current_model_idx -= 1
            new_model = self.models[self.current_model_idx]
            logger.warning(f"FPS pod cílem, přepínám na rychlejší model: {new_model}")
            self._switch_model(new_model)

        # Pokud máme hodně rezervy a můžeme použít přesnější model
        elif avg_fps > self.target_fps * 1.5 and self.current_model_idx < len(self.models) - 1:
            self.current_model_idx += 1
            new_model = self.models[self.current_model_idx]
            logger.info(f"FPS nad cílem, přepínám na přesnější model: {new_model}")
            self._switch_model(new_model)

    def _switch_model(self, model_name: str):
        """Přepni na jiný model"""
        try:
            old_config = {
                'device': self.detector.device,
                'backend': self.detector.backend,
                'fp16': self.detector.fp16,
                'confidence_threshold': self.detector.confidence_threshold,
                'nms_iou_threshold': self.detector.nms_iou_threshold,
            }

            self.detector = PersonDetector(model_name=model_name, **old_config)
            self.detector.warmup(iterations=5)
            self.fps_history.clear()

        except Exception as e:
            logger.error(f"Chyba při přepínání modelu: {e}")
            # Vrať zpět starý index
            self.current_model_idx = self.models.index(self.detector.model_name)

    @property
    def inference_time(self) -> float:
        """Čas inference v ms"""
        return self.detector.inference_time

    def get_fps(self) -> float:
        """Aktuální FPS"""
        return self.detector.get_fps()
