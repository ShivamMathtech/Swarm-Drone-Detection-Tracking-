# Swarm Drone Detection & Tracking System

A local computer-vision research console with configurable Ultralytics YOLO detection, ByteTrack / BoT-SORT association, persistent IDs, recorded-video playback, webcam / RTSP input, and a neon-green Canvas HUD.

**Start with DEMO to verify your installation. Real drone detection requires your own trusted, drone-trained weights. No trained weights or detection-accuracy claims are included.** A general COCO model is not a drone detector. The software does not contain weapon control, interception, engagement commands, range estimation, or physical-motion guidance.

![Running demo console](docs/console-demo.png)

## 1. Architecture

```mermaid
flowchart TD
    A[Video file or live capture] --> B[YOLO detection]
    D[Synthetic demo scene] --> E[Demo contour detection]
    B --> C[ByteTrack or BoT-SORT]
    E --> C
    C --> F[Track history and SQLite]
    F --> G[Frame plus metadata packet]
    G --> H[React Canvas HUD and crop]
```

- FastAPI owns configuration, uploads, stream controls, WebSocket clients and exports.
- A separate spawned worker process owns video capture, model, tracker and database writes. It keeps heavy inference off the API event loop. Stop can terminate a blocked native decoder.
- Live inputs continuously drain capture into a single latest-frame slot. Recorded files follow their source FPS. Processing never intentionally fast-forwards the file; slow hardware can produce slower playback. Frame Skip reduces inference frequency.
- YOLO uses a low candidate threshold for the tracker's second association stage. The configured confidence threshold governs first-stage matching and new tracks. An existing associated track may survive with a lower score and is shown in yellow. The original model class name is preserved.
- Each class has its own association pool. Temporary missing observations appear as LOST, retain their last observed box/path, and may be REACQUIRED with the same ID. IDs are session-local, association is best-effort, and crossing/occlusion can still cause switches. DR is a display prefix; inspect CLASS to distinguish drone/bird/aircraft.
- The worker sends JPEG + compact JSON in one binary packet: 4-byte big-endian JSON length, UTF-8 JSON, then JPEG bytes. This keeps image and coordinates synchronized without Base64 overhead or two-stream drift. Status notifications are JSON text messages. The browser keeps only the newest pending frame.
- A grayscale Canvas presents the actual image, brackets, paths and central reticle. React renders controls, metrics, settings, target details and logs. The seeker crops the same decoded frame, clamped to image bounds. Zoom magnifies a context window initially 12 target-widths wide (minimum 160 source pixels), then clamps the crop to fit the target and frame. It is a digital crop, not optical zoom or sensor steering.

## 2. Requirements

- **Python 3.11 or 3.12, 64-bit recommended.** Do not use Python 3.14 for this pinned environment.
- Node.js 22 LTS (Node 24 also worked during verification), npm.
- CPU works. NVIDIA CUDA is optional. Intel integrated graphics uses CPU in this build.
- Internet for the initial dependency install; trained local weights and the installed application can then run offline.
- One backend process / one active stream. Do not pass `--workers` greater than 1 to Uvicorn.

The dependency pins are a reproducible compatibility baseline, not a claim that every package is the newest release. Review and test dependency updates before deployment.

## 3. Windows setup (PowerShell)

Extract the ZIP and open a terminal **inside `swarm-drone-tracker`**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Backend, terminal 1:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend, terminal 2, from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, leave SOURCE on **DEMO · SYNTHETIC**, and click **START**. You should see six moving synthetic objects, persistent track IDs, selection and a live crop. One object briefly disappears every cycle to exercise reacquisition. Synthetic detections use contour extraction and report synthetic scores; they are not YOLO accuracy results.

Using the virtual environment executable directly avoids PowerShell activation-policy problems. If you prefer activation, activate it and the backend command is simply:

```text
python -m uvicorn app.main:app --reload
```

## 4. Linux / macOS setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# Linux CPU wheels:
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
# On macOS use: pip install torch==2.7.1 torchvision==0.22.1
pip install -r backend/requirements.txt
cp .env.example .env
cd backend
python -m uvicorn app.main:app --reload
```

In another terminal:

```bash
cd swarm-drone-tracker/frontend
npm install
npm run dev
```

On minimal Debian/Ubuntu servers, OpenCV may require `libgl1` and `libglib2.0-0`. The Docker image includes them. Do not install competing `opencv-python` and `opencv-python-headless` distributions into the same environment.

## 5. Real video detection

1. Train a detector or obtain compatible weights from a trusted source.
2. Copy the resulting `best.pt` to **`weights/drone_detector.pt`**.
3. Open Settings and confirm Model Path, device, resolution and threshold. Stop the stream before applying settings.
4. Select VIDEO FILE, upload an MP4/AVI/MOV/MKV/WebM file, wait for upload validation, then START.
5. Click a bracket or a track-directory row. The seeker and details update to that object.
6. PAUSE/RESUME controls processing. STOP releases the session. Starting again begins a new session and resets track IDs.

The uploader accepts up to 1 GiB and checks that the first frame decodes. A corrupt later frame may still end a recording early. There is no audio track. Uploads are stored under `runtime/uploads` using random IDs, not user-controlled paths. Remove unused recordings manually after stopping sessions.

**Webcam:** select WEBCAM and camera index 0, 1, etc. The camera belongs to the **backend machine**, not the remote browser. Close other apps using the camera. Run natively for the simplest webcam access.

**RTSP:** set a secret only on the server, e.g. edit `.env`:

```dotenv
CAM_RTSP_URL=rtsp://username:password@camera-ip:554/stream
```

Restart the backend, select RTSP and enter the alias `CAM_RTSP_URL`. The frontend never receives the URL or credentials. Additional aliases can use `CAM_LOBBY_URL` etc. Native OpenCV logs are suppressed and backend error messages omit source URLs. RTSP failures are surfaced rather than endlessly retried; check connectivity and restart the session.

## 6. GPU setup

Install a compatible NVIDIA driver and PyTorch CUDA build **in the same environment**. For the pinned torch family, consult the official [PyTorch previous versions instructions](https://pytorch.org/get-started/previous-versions/). Choose the wheel compatible with your driver. For example, CUDA 12.6 wheels:

```bash
pip install --force-reinstall torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print(torch.cuda.is_available())"
```

Select device `CUDA 0` in Settings, or `DEVICE=0` in `.env` before saving settings. Invalid or unavailable devices cause a clear error; the application does not silently pretend to run on GPU. This build exposes CPU and CUDA, not Apple MPS.

## 7. Configuration

```dotenv
MODEL_PATH=weights/drone_detector.pt
CONFIDENCE_THRESHOLD=0.40
IOU_THRESHOLD=0.50
IMAGE_SIZE=1280
DEVICE=cpu
TRACKER=bytetrack
TRACK_BUFFER=30
MATCH_THRESHOLD=0.8
TARGET_FPS=30
FRAME_SKIP=0
MAX_FRAME_WIDTH=1280
```

The Settings panel also controls JPEG quality, trajectory length/thickness/fade, brackets, IDs, confidence, reticle, seeker, digital zoom, debug and research display. `IMAGE_SIZE` must be divisible by 32. Model paths are resolved relative to the repository, independent of the terminal working directory.

Saved Settings override environment defaults on subsequent starts. They are stored in the SQLite `configuration` table. Change settings through the UI to preserve history. Configuration updates require stopping the stream because model/tracker construction happens once per session.

`TRACK_BUFFER` is measured in **processed tracker updates**, not raw source frames or seconds. At 15 processed FPS a buffer of 30 is approximately two seconds. A longer buffer can improve reacquisition but also permit incorrect associations. BoT-SORT uses camera-motion compensation; learned appearance ReID is disabled in this baseline.

## 8. Playback / performance tuning

Start on CPU with IMAGE SIZE **640**, MAX FRAME WIDTH **960**, TARGET FPS **15**, FRAME SKIP **1**, then measure. Small far-away drones may need a larger image size, better optics and dedicated small-object training. Increasing resolution costs inference time. Lowering the threshold cannot recover objects that are only a few indistinct pixels.

- TARGET FPS caps processed output; it does not guarantee throughput.
- FRAME SKIP 1 runs inference every other source frame; IDs/path points are updated only on processed frames.
- JPEG quality 70–80 usually reduces bandwidth while keeping the source readable.
- Single-frame inference minimizes latency for a single stream. Batch inference is reserved for training/evaluation; it is deliberately not imposed on a live feed.
- The server transport queue and browser decode queue discard superseded frames. This prevents unbounded memory/backlog; raw inputs are not saved automatically.
- Reported FPS is measured processed output rate, not the camera's advertised frame rate.
- Inference and tracker timings are measured separately. Pipeline time includes capture/wait, inference, tracker, database write and encoding; it excludes browser transport/render.
- Canvas render time measures the draw call. Capture → display is an approximate browser wall-clock measurement from the frame read; it assumes the backend and browser clocks are synchronized (normal for same-machine use). It does not measure sensor exposure latency or internal camera buffering. `¹` identifies this limitation in the UI.
- Pause keeps a live capture reader draining the camera; resume uses a recent frame. Paused recorded files keep their place.

## 9. Dataset preparation

```text
dataset/
  data.yaml
  images/train/   images/val/   images/test/
  labels/train/   labels/val/   labels/test/
```

Each image has a same-stem `.txt` annotation in the corresponding labels folder. Each row:

```text
class_id center_x center_y width height
```

Coordinates are normalized to `[0,1]`. Use an empty `.txt` for a human-confirmed negative image. Example:

```yaml
path: .
train: images/train
val: images/val
test: images/test
names:
  0: drone
  1: bird
  2: aircraft
  3: helicopter
```

Add names only when matching labels exist. Include distant/small drones, motion blur, different cameras/backgrounds, partial occlusions, weather/lighting and negative examples such as birds, kites and empty sky. Split by original flight, recording, site and date. Adjacent frames must not leak across splits. Review labels and use a held-out test set that reflects the deployment camera.

```bash
python scripts/validate_dataset.py --data dataset/data.yaml
```

The validator checks class IDs, box bounds, matching label files and exact image duplication across splits. It cannot prove the absence of near-duplicate frames or recording-level leakage; review the provenance yourself.

## 10. Train

From the repository root, with the environment active:

```bash
python scripts/train.py --data dataset/data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --batch 8 --device cpu
# NVIDIA example:
python scripts/train.py --data dataset/data.yaml --model yolov8s.pt --epochs 100 --imgsz 1280 --batch 8 --device 0
```

The model argument is configurable. A pretrained model name may trigger an Ultralytics download; use a local path for offline work. Training uses seed 42, deterministic mode and workers 0 by default for Windows compatibility. Hardware/library differences can still affect exact reproducibility. Copy the resulting `runs/train/drone*/weights/best.pt` to `weights/drone_detector.pt`.

## 11. Evaluation and reports

```bash
python scripts/evaluate.py --data dataset/data.yaml --model weights/drone_detector.pt --split test --imgsz 1280 --device cpu --output reports/evaluation
```

This executes YOLO validation and saves **real** precision, recall, mAP50 and mAP50–95 in JSON/CSV, plus Ultralytics plots. Use IMPORT EVALUATION in the footer to display the JSON. Imported metrics are explicitly separate from live-session measurements. They remain in server memory until restart. Exports include them when loaded.

For tracking evaluation, supply frame-level ground-truth identities in a CSV with these columns:

```csv
source_frame,track_id,class_name,x1,y1,x2,y2
1,1,drone,400,220,470,280
2,1,drone,403,221,473,281
```

Export predictions with EXPORT CSV and run:

```bash
python scripts/evaluate_tracking.py --gt annotations.csv --pred swarm-session.csv --iou 0.5 --output reports/tracking.json
```

Coordinates must match the transmitted frame size after MAX FRAME WIDTH resizing, and frame numbers must match the original recording. Use FRAME SKIP 0 for full-frame evaluation, or evaluate GT on the same sampled frames. Mixing unprocessed GT frames with skipped predictions otherwise counts them as misses. Input must contain one session and no duplicate track ID within a frame.

The script uses class-aware Hungarian IoU matching, counts ID switches relative to the last matched identity (including gaps), and reports per-GT-track coverage, precision/recall, false positives and misses. It is **not HOTA/IDF1** and does not claim compatibility with all MOTChallenge conventions. For publications, additionally run TrackEval with a declared standard protocol.

Live persistence is `observed processed frames / frames since first observation`, averaged over retained tracks. It describes continuity, not identity correctness. Live ID switches and detection accuracy stay N/A without annotations. No tracking-confidence probability is fabricated; the displayed confidence is the detector score.

SQLite stores sessions, detections, tracks, events and configuration in `runtime/research.sqlite3` (WAL mode). Track first/last_seen are source-time seconds; detection timestamp is UNIX wall time. Detections also retain processed `frame_id`, original `source_frame`, and `source_time` for reproducible annotation alignment. EXPIRED/ENDED tracks remain in the database even after leaving the current HUD. Exports cover the most recent session; the database retains previous sessions. Large runs increase disk usage and export memory, so archive sessions between long experiments.

## 12. API

Interactive schema: **http://127.0.0.1:8000/docs**.

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Service and pipeline state |
| GET / POST | `/config` | Read / validate and save settings |
| POST | `/upload-video` | Multipart upload, returns upload_id |
| POST | `/stream/start` | Start demo/webcam/video/RTSP |
| POST | `/stream/stop` | Stop and release resources |
| POST | `/stream/pause`, `/stream/resume` | Pause / resume |
| GET | `/tracks`, `/stats`, `/events` | Current metadata and recent log |
| POST | `/research/report` | Import validated evaluation metrics |
| GET | `/reports/json`, `/reports/csv` | Session exports |
| WS | `/ws/tracking` | Synchronized binary image/JSON packets + text status |

Example start body: `{"source":"demo"}`. For a video: `{"source":"video","upload_id":"<returned UUID>"}`. The Vite development proxy maps `/api/*` to FastAPI; production Nginx uses the same route contract.

## 13. Tests

```bash
python -m pytest -q
cd frontend
npm run build
npx playwright install chromium
# Start backend separately first.
npm run test:e2e
```

Tests cover parser/clipping, xywh conversion, both tracker algorithms, association across a gap, class-pool ID stability, LOST/reacquired/expiry, trajectory limits, wire encoding, config validation, health/API errors, report validation and a real YOLO-to-video-WebSocket integration. The integration creates **untrained** local weights to verify execution/transport without an external model download; it does not validate detection accuracy. A browser test verifies the demo, six tracks, selection/crop, pause/resume, stop and settings. See `docs/VERIFICATION.md` for the checks actually executed in the delivery environment.

## 14. Docker (optional CPU profile)

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080. This profile supports demo/upload/RTSP. Native webcam passthrough and CUDA container runtime configuration are platform-specific and not part of the CPU compose profile. Docker packaging is provided separately from the native test path.

## 15. Troubleshooting

| Symptom | Fix |
|---|---|
| MODEL UNAVAILABLE | Put trusted weights at the configured path. Try DEMO to isolate installation issues. |
| No drones detected | Verify that the model includes a trained drone class, labels are correct and drones are visible at adequate resolution. Evaluate held-out footage. A generic COCO model is insufficient. |
| Python tries compiling NumPy | Use 64-bit Python 3.11/3.12 in a fresh environment; upgrade pip. Avoid copying another machine's virtual environment. |
| CUDA unavailable | Select CPU or install the driver and matching CUDA PyTorch wheels in this environment. |
| Video stutters on CPU | Try image size 640, width 960, skip 1–2 and target 15 FPS. Measure inference latency. 30 FPS at 1280 is not guaranteed. |
| Camera unavailable | Check camera index, permissions and whether another application holds the device. Camera must be connected to backend host. |
| Invalid RTSP | Check server `.env`, alias, LAN reachability, credentials and camera codec; restart backend after editing secrets. |
| Video cannot decode | Convert to H.264 MP4 or MJPEG AVI. Check whether the source file is damaged. |
| WebSocket offline | Start backend on 8000 and frontend on 5173. Check port conflicts/proxy/allowed origins. Browser retries automatically. |
| Brackets briefly disappear | Low confidence, small objects, occlusion or slow frame sampling can break association. Improve data/optics, reduce skip or tune buffer. |
| Settings rejected | Stop the stream first. Image size must be divisible by 32; use CPU or a numeric CUDA index. |
| Old `.env` values persist | Saved UI settings override environment defaults. Update Settings instead. |
| npm platform error | Delete your locally generated `node_modules` and reinstall on the current OS; the ZIP contains no node_modules. |
| RTSP/camera stop delayed | OpenCV native reads may block; Stop waits briefly then terminates the isolated worker. |
| Frozen image after Stop | The last image can remain visible under the STOPPED overlay. START opens a new session; no inference occurs while stopped. |

This is a trusted local research application, with localhost bindings and an origin allowlist. It does not include authentication, TLS, user accounts or Internet-service hardening. Do not expose its API publicly without adding those controls. Load only trusted PyTorch checkpoints and decode trusted research footage. Never commit `.env`, credentials, runtime recordings or private datasets.

## 16. Research extensions

Useful next experiments include small-object training/tiling, recording-level cross-validation, calibrated detection-score reliability, verified appearance ReID, TrackEval IDF1/HOTA, dataset shift analysis, low-light enhancement ablations, class confusion analysis and hardware-specific profiling. Real-world range/altitude/speed would require external sensors or a separately validated calibration model; current HUD values remain N/A.

Technical references: [Ultralytics tracking](https://docs.ultralytics.com/modes/track/), [BYTETracker API](https://docs.ultralytics.com/reference/trackers/byte_tracker/), [YOLO training](https://docs.ultralytics.com/modes/train/), [YOLO validation](https://docs.ultralytics.com/modes/val/), [ByteTrack paper](https://arxiv.org/abs/2110.06864). Review Ultralytics licensing and model/dataset licenses before redistribution or commercial use.

## 17. Folder map

```text
swarm-drone-tracker/
  backend/
    app/
      main.py                 API, lifecycle, worker manager, WebSocket
      config.py               validated settings, source request
      detection/yolo_detector.py
      tracking/tracker.py     class-aware tracker + history
      video/stream.py         webcam/RTSP/file/demo capture
      video/pipeline.py       connected inference and transport
      analytics/metrics.py
      models/schemas.py
      utils/database.py
    requirements.txt
    Dockerfile
  frontend/
    src/
      App.tsx
      components/             camera, seeker, controls, metrics, settings
      hud/draw.ts             Canvas brackets, reticle, paths, crop math
      services/               API and bounded video decode
      store/                  Zustand state
      types/
      main.tsx
      style.css
    tests/console.spec.ts
    package.json
    package-lock.json
    vite.config.ts
    nginx.conf
    Dockerfile
  weights/README.md           place your drone_detector.pt here
  dataset/data.yaml
  dataset/images/{train,val,test}/
  dataset/labels/{train,val,test}/
  scripts/
    train.py
    evaluate.py
    evaluate_tracking.py
    validate_dataset.py
    dataset_utils.py
    make_demo_video.py
  samples/                    synthetic playback fixture
  tests/                      unit/API/YOLO integration tests
  docs/                       screenshot, verification, protocol
  .env.example
  docker-compose.yml
  pytest.ini
  README.md
```
