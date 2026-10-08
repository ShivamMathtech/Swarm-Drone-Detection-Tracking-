# Synthetic video fixture

`synthetic-swarm.avi` is a six-second, 1280×720, 30 FPS MJPEG clip generated from procedural drone-like shapes over a grayscale scene. Its pixels are explicitly labeled synthetic. It is for decoder/playback checks, not model training or accuracy evaluation.

The application's built-in DEMO source uses the same procedural scene continuously and runs a contour detector plus the selected real tracker without weights. VIDEO FILE mode always uses YOLO, including when this fixture is uploaded: it requires configured weights and may correctly produce zero detections from an untrained or unsuitable model.

Regenerate from the repository root:

```bash
python scripts/make_demo_video.py --seconds 12 --output samples/synthetic-swarm.avi
```
