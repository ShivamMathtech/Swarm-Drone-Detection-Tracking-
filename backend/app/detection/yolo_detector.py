from pathlib import Path
import numpy as np
from app.config import ROOT


def parse_boxes(boxes, width, height):
    """Convert Ultralytics Nx6 xyxy/conf/class data to finite, clipped float32 rows."""
    if hasattr(boxes, "cpu"): boxes = boxes.cpu().numpy()
    a = np.asarray(boxes, dtype=np.float32).reshape(-1, 6).copy()
    a = a[np.isfinite(a).all(axis=1)]
    a[:, [0, 2]] = a[:, [0, 2]].clip(0, width)
    a[:, [1, 3]] = a[:, [1, 3]].clip(0, height)
    return a[(a[:, 2] > a[:, 0]) & (a[:, 3] > a[:, 1]) & (a[:, 4] >= 0) & (a[:, 4] <= 1)]

class YoloDetector:
    def __init__(self, config):
        import torch
        from ultralytics import YOLO
        path = Path(config.model_path)
        if not path.is_absolute(): path = ROOT / path
        if not path.is_file():
            raise ValueError("MODEL UNAVAILABLE: place trusted drone weights at MODEL_PATH; see README")
        if config.device != "cpu":
            if not torch.cuda.is_available() or int(config.device) >= torch.cuda.device_count():
                raise ValueError("CUDA UNAVAILABLE: select CPU or install compatible CUDA PyTorch")
        self.config = config
        self.model = YOLO(str(path), task="detect")
        self.names = self.model.names

    def detect(self, frame):
        c = self.config
        # Keep low-score candidates for ByteTrack's second association stage.
        result = self.model.predict(frame, conf=min(.1, c.confidence_threshold / 2),
            iou=c.iou_threshold, imgsz=c.image_size, device=c.device, verbose=False)[0]
        return parse_boxes(result.boxes.data, frame.shape[1], frame.shape[0])
