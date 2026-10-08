# Delivery verification

Executed in the Linux delivery environment, 7 October 2026.

| Check | Result |
|---|---|
| Backend pytest suite | 15 passed |
| ByteTrack + BoT-SORT association | Both passed; stable IDs across motion and a short gap |
| Class-pool ID allocation | Passed; new classes do not recycle current IDs |
| Real YOLO inference | Passed using an untrained local YOLOv8n checkpoint |
| Uploaded AVI → YOLO → tracker → WebSocket | Passed; JPEG decoded and frame metadata checked |
| Nonempty demo targets → serialized video packet | Passed with six tracks |
| Browser flow | Passed in Chromium: demo, six tracks, selection, seeker, pause, resume, stop, settings |
| TypeScript / Vite production build | Passed |
| Visual review | Screenshot inspected; grayscale camera, green brackets, crop, target details, metrics and controls |
| Sample video | Generated locally as explicitly labeled synthetic MJPEG AVI |

Python 3.12, PyTorch 2.7.1 CPU, torchvision 0.22.1, Ultralytics 8.3.161, OpenCV 4.11.0.86. See requirements.txt and package-lock.json for application dependency pins. A third-party AnyIO/Starlette deprecation warning was observed without test failure.

These tests verify software behavior, not drone detection accuracy. Untrained integration weights and runtime session databases are not bundled. No drone-trained checkpoint, labeled real-world test set, physical camera, RTSP device or CUDA GPU was available for validation. Native Windows/macOS and Docker execution were not exercised. Their installation/configuration paths are provided and must be checked on the intended machine. The observed approximately 30 FPS demo result is not a YOLO benchmark.

The software remains a local research implementation, not a validated operational surveillance product. Dataset evaluation, camera-specific testing and performance measurement remain necessary before drawing research conclusions.
