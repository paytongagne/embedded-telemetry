import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


class FaultBlackBox:
    """Captures a pre-fault ring buffer plus a post-fault telemetry window."""

    def __init__(self, pre_samples=60, post_samples=20, output_dir="captures"):
        self.pre_samples = max(1, int(pre_samples))
        self.post_samples = max(0, int(post_samples))
        self.output_dir = Path(output_dir)
        self.buffer = deque(maxlen=self.pre_samples)
        self.active = None
        self.last_state = None

    def reset(self):
        self.buffer.clear()
        self.active = None
        self.last_state = None

    def update(self, telemetry, metadata=None):
        data = dict(telemetry)
        state = str(data.get("STATUS", data.get("STATE", "UNKNOWN"))).upper()
        completed = None

        if self.active is not None:
            self.active["post_fault"].append(data)
            if len(self.active["post_fault"]) >= self.post_samples:
                completed = self._finalize()

        if self.active is None and state == "FAULT" and self.last_state != "FAULT":
            self.active = {
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "metadata": dict(metadata or {}),
                "pre_fault": list(self.buffer),
                "trigger": data,
                "post_fault": [],
            }
            if self.post_samples == 0:
                completed = self._finalize()

        self.buffer.append(data)
        self.last_state = state
        return completed

    def _finalize(self):
        capture = self.active
        self.active = None
        if capture is None:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f_utc")
        path = self.output_dir / f"fault_capture_{stamp}.json"
        path.write_text(json.dumps(capture, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path
