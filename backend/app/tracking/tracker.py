from types import SimpleNamespace
import numpy as np

class DetectionBatch:
    """Numpy Results-like adapter consumed by Ultralytics trackers."""
    def __init__(self, rows): self.rows = np.asarray(rows, dtype=np.float32).reshape(-1, 6)
    def __len__(self): return len(self.rows)
    def __getitem__(self, index): return DetectionBatch(self.rows[index])
    @property
    def conf(self): return self.rows[:, 4]
    @property
    def cls(self): return self.rows[:, 5]
    @property
    def xywh(self):
        a = self.rows[:, :4].copy()
        a[:, 2:] -= a[:, :2]
        a[:, :2] += a[:, 2:] / 2
        return a

class MultiTracker:
    def __init__(self, config):
        from ultralytics.trackers.byte_tracker import BYTETracker
        from ultralytics.trackers.bot_sort import BOTSORT
        self.cls = BYTETracker if config.tracker == "bytetrack" else BOTSORT
        self.args = SimpleNamespace(track_high_thresh=config.confidence_threshold,
            track_low_thresh=min(.1, config.confidence_threshold / 2),
            new_track_thresh=config.confidence_threshold, track_buffer=config.track_buffer,
            match_thresh=config.match_threshold, fuse_score=True,
            gmc_method="sparseOptFlow", proximity_thresh=.5, appearance_thresh=.25,
            with_reid=False, model="auto")
        self.trackers = {}
        self.ids = {}
        self.next_id = 1

    def update(self, rows, frame):
        rows = np.asarray(rows, dtype=np.float32).reshape(-1, 6)
        # Independent class pools prevent a bird track from turning into a drone ID.
        for class_id in rows[:, 5].astype(int):
            if class_id not in self.trackers:
                # Constructor resets a global counter in Ultralytics; preserve existing IDs.
                from ultralytics.trackers.basetrack import BaseTrack
                count = BaseTrack._count
                self.trackers[class_id] = self.cls(self.args, frame_rate=30)
                BaseTrack._count = count
        out = []
        for class_id, tracker in self.trackers.items():
            result = tracker.update(DetectionBatch(rows[rows[:, 5] == class_id]), frame)
            for r in result:
                key = (class_id, int(r[4]))
                if key not in self.ids:
                    self.ids[key] = self.next_id; self.next_id += 1
                out.append({"track_id": self.ids[key], "class_id": int(class_id),
                    "bbox": [float(x) for x in r[:4]], "confidence": float(r[5])})
        return out

class TrackHistory:
    def __init__(self, config):
        self.config = config
        self.items = {}
        self.frame = 0
        self.detection_count = 0
        self.total_tracks = 0
    def update(self, rows, timestamp, names):
        self.frame += 1
        events, seen = [], set()
        for row in rows:
            tid = row["track_id"]; seen.add(tid)
            self.detection_count += 1
            old = self.items.get(tid)
            status = "REACQUIRED" if old and old["status"] == "LOST" else "ACTIVE"
            if old is None:
                self.total_tracks += 1
                events.append(f"Detected DR-{tid:02d}")
            elif status == "REACQUIRED": events.append(f"DR-{tid:02d} reacquired")
            elif (old['confidence'] < self.config.confidence_threshold) != (row['confidence'] < self.config.confidence_threshold):
                events.append(f"DR-{tid:02d} confidence threshold crossed")
            box = row["bbox"]
            center = [(box[0]+box[2])/2, (box[1]+box[3])/2]
            history = (old["trajectory"] if old else []) + [center]
            first = old["first_seen"] if old else timestamp
            observed = (old["observed_frames"] if old else 0) + 1
            first_frame = old["first_frame"] if old else self.frame
            self.items[tid] = {**row, "id": f"DR-{tid:02d}",
                "class_name": names.get(row["class_id"], str(row["class_id"])),
                "center": center, "status": status, "trajectory": history[-self.config.trajectory_length:],
                "first_seen": first, "last_seen": timestamp, "last_frame": self.frame,
                "first_frame": first_frame, "age_seconds": timestamp-first,
                "observed_frames": observed, "persistence": observed/(self.frame-first_frame+1),
                "range_m": None, "altitude_m": None, "speed_mps": None}
        for tid, item in list(self.items.items()):
            if tid in seen: continue
            if self.frame - item["last_frame"] > self.config.track_buffer:
                events.append(f"{item['id']} expired")
                del self.items[tid]
            else:
                if item["status"] != "LOST": events.append(f"{item['id']} temporarily lost")
                item["status"] = "LOST"
                item["age_seconds"] = timestamp - item["first_seen"]
                item["persistence"] = item["observed_frames"]/(self.frame-item["first_frame"]+1)
        return list(self.items.values()), events
