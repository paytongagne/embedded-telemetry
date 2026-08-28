from ground_station.connection import connection_metadata
from ground_station.database import TelemetryDatabase
from ground_station.parser import parse_telemetry


class RecordingManager:
    """Transport proxy that records accepted telemetry, commands, and link events."""

    _INTERNAL = {"_manager", "database", "session_id", "_closed"}

    def __init__(self, manager, database=None):
        object.__setattr__(self, "_manager", manager)
        object.__setattr__(self, "database", database or TelemetryDatabase())
        object.__setattr__(self, "session_id", None)
        object.__setattr__(self, "_closed", False)

    def __getattr__(self, name):
        return getattr(self._manager, name)

    def __setattr__(self, name, value):
        if name in self._INTERNAL or "_manager" not in self.__dict__:
            object.__setattr__(self, name, value)
            return

        if hasattr(self._manager, name):
            setattr(self._manager, name, value)
            return

        object.__setattr__(self, name, value)

    def _metadata(self):
        if hasattr(self._manager, "connection_metadata"):
            return self._manager.connection_metadata()
        return connection_metadata(self._manager)

    def _ensure_session(self):
        if self.session_id is not None:
            return self.session_id

        if not getattr(self._manager, "connected", False):
            return None

        transport, endpoint = self._metadata()
        session_id = self.database.start_session(transport, endpoint)
        object.__setattr__(self, "session_id", session_id)
        self.database.log_event(session_id, "INFO", "CONNECTION", f"Connected to {endpoint}")
        return session_id

    def available_ports(self):
        return self._manager.available_ports()

    def set_port(self, port):
        return self._manager.set_port(port)

    def set_baud(self, baud):
        return self._manager.set_baud(baud)

    def connect(self):
        return self._manager.connect()

    def reconnect(self):
        return self._manager.reconnect()

    def disconnect(self):
        result = self._manager.disconnect()
        self._finish_session("Disconnected")
        return result

    def send(self, message):
        success = self._manager.send(message)
        if success:
            session_id = self._ensure_session()
            self.database.log_event(
                session_id,
                "INFO",
                "COMMAND",
                message.rstrip("\r\n"),
            )
        return success

    def get_line_nowait(self):
        line = self._manager.get_line_nowait()
        if line is None:
            return None

        telemetry = parse_telemetry(line)
        if telemetry is not None:
            session_id = self._ensure_session()
            self.database.log_telemetry(session_id, telemetry)
            if telemetry.get("FW"):
                self.database.set_firmware_version(session_id, telemetry.get("FW"))

        return line

    def get_event_nowait(self):
        event = self._manager.get_event_nowait()
        if event is None:
            return None

        event_type, value = event
        if event_type == "CONNECTED":
            self._ensure_session()
        elif event_type == "DISCONNECTED":
            self._finish_session(f"Disconnected from {value}")
        else:
            session_id = self._ensure_session()
            self.database.log_event(session_id, event_type, "TRANSPORT", value)

        return event

    def _finish_session(self, message):
        session_id = self.session_id
        if session_id is None:
            return
        self.database.log_event(session_id, "INFO", "CONNECTION", message)
        self.database.end_session(session_id)
        object.__setattr__(self, "session_id", None)

    def close(self):
        if self._closed:
            return
        self._finish_session("Ground station closed")
        self.database.close()
        object.__setattr__(self, "_closed", True)
