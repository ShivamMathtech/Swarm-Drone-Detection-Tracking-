# Tracking WebSocket protocol

Endpoint: `/ws/tracking`. Browser binary type: `arraybuffer`.

Text messages contain `type: "status"`, a status (`STOPPED`, `STARTING`, `RUNNING`, `PAUSED`, `ENDED`, `ERROR`), message and session_id. No raw RTSP URLs are returned.

A binary frame message contains:

1. Four unsigned big-endian bytes giving JSON length N.
2. Exactly N bytes of UTF-8 JSON metadata.
3. Remaining bytes: JPEG of the matching video frame.

Metadata includes type, wall timestamp/captured_at, source/processed frame numbers, media time, width/height, measured FPS, inference/tracker/pipeline latency, demo flag, model label, targets, optional raw detections, current statistics and frame events. Coordinates use transmitted image pixels, before CSS scaling. No position extrapolation is used for the observed path.

Each target has integer track_id, display id, class_id/class_name, confidence, xyxy bbox, center, ACTIVE/LOST/REACQUIRED status, trajectory, first/last_seen in source-time seconds, age, observation count and persistence. Physical range/altitude/speed fields are null. LOST boxes are the last observation, not a current localization.

A bounded server queue and browser pending slot can skip superseded packets. Fetch `/events` for the persistent recent event log rather than assuming every frame event was delivered. Live sources can also discard raw camera frames in the capture reader to bound latency. Multiple browser observers share one active stream; this is not a multi-tenant API.
