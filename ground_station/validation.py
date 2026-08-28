from dataclasses import dataclass
import time


@dataclass
class ValidationResult:
    name: str
    status: str = "PENDING"
    detail: str = ""
    elapsed_seconds: float | None = None


class FaultValidationEngine:
    """Deterministic state-machine validation using the existing fault commands."""

    STEPS = (
        ("Baseline NORMAL", None, "NORMAL", 5.0),
        ("IMU fault -> DEGRADED", "CMD,INJECT_FAULT,IMU", "DEGRADED", 5.0),
        ("Clear IMU -> NORMAL", "CMD,CLEAR_FAULTS", "NORMAL", 5.0),
        ("BME fault -> DEGRADED", "CMD,INJECT_FAULT,BME", "DEGRADED", 5.0),
        ("BME + IMU -> FAULT", "CMD,INJECT_FAULT,IMU", "FAULT", 5.0),
        ("Clear all -> NORMAL", "CMD,CLEAR_FAULTS", "NORMAL", 5.0),
    )

    def __init__(self):
        self.running = False
        self.finished = False
        self.passed = False
        self.current_index = 0
        self.step_started = None
        self.results = []
        self._pending_action = None

    def start(self, now=None):
        now = time.monotonic() if now is None else float(now)
        self.running = True
        self.finished = False
        self.passed = False
        self.current_index = 0
        self.results = [ValidationResult(name=step[0]) for step in self.STEPS]
        self._enter_step(now)

    def stop(self, detail="Stopped by user"):
        if self.running and self.current_index < len(self.results):
            self.results[self.current_index].status = "STOPPED"
            self.results[self.current_index].detail = detail
        self.running = False
        self.finished = True
        self.passed = False
        self._pending_action = None

    def next_action(self):
        action = self._pending_action
        self._pending_action = None
        return action

    def tick(self, state, connected=True, now=None):
        if not self.running:
            return
        now = time.monotonic() if now is None else float(now)

        if not connected:
            self._fail_current("Device disconnected during validation", now)
            return

        _, _, expected_state, timeout = self.STEPS[self.current_index]
        current_state = str(state or "UNKNOWN").upper()

        if current_state == expected_state:
            result = self.results[self.current_index]
            result.status = "PASS"
            result.detail = f"Observed {expected_state}"
            result.elapsed_seconds = now - self.step_started
            self.current_index += 1

            if self.current_index >= len(self.STEPS):
                self.running = False
                self.finished = True
                self.passed = True
                return

            self._enter_step(now)
            return

        if now - self.step_started > timeout:
            self._fail_current(
                f"Timed out waiting for {expected_state}; observed {current_state}",
                now,
            )

    def _enter_step(self, now):
        self.step_started = now
        _, action, _, _ = self.STEPS[self.current_index]
        self.results[self.current_index].status = "RUNNING"
        self._pending_action = action

    def _fail_current(self, detail, now):
        result = self.results[self.current_index]
        result.status = "FAIL"
        result.detail = detail
        result.elapsed_seconds = now - self.step_started
        self.running = False
        self.finished = True
        self.passed = False
        self._pending_action = None
