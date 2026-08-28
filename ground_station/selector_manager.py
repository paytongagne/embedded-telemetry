from PySide6.QtWidgets import QDialog

from ground_station.connection import connection_metadata
from ground_station.connection_dialog import ConnectionDialog


class ConnectionSelectorManager:
    """Lazily selects a real transport after QApplication has been created."""

    _INTERNAL = {"_manager", "_dialog_parent"}

    def __init__(self, parent=None):
        object.__setattr__(self, "_manager", None)
        object.__setattr__(self, "_dialog_parent", parent)

    def __getattr__(self, name):
        manager = object.__getattribute__(self, "_manager")
        if manager is None:
            if name == "connected":
                return False
            if name == "port":
                return "SELECT CONNECTION"
            if name == "baud":
                return 0
            if name == "auto_reconnect":
                return False
            raise AttributeError(name)
        return getattr(manager, name)

    def __setattr__(self, name, value):
        if name in self._INTERNAL or "_manager" not in self.__dict__:
            object.__setattr__(self, name, value)
            return

        manager = object.__getattribute__(self, "_manager")
        if manager is not None and hasattr(manager, name):
            setattr(manager, name, value)
            return

        object.__setattr__(self, name, value)

    def _ensure_manager(self):
        if self._manager is not None:
            return True

        dialog = ConnectionDialog(self._dialog_parent)
        if dialog.exec() != QDialog.Accepted:
            return False

        object.__setattr__(self, "_manager", dialog.build_manager())
        return True

    def available_ports(self):
        if not self._ensure_manager():
            return []
        return self._manager.available_ports()

    def set_port(self, port):
        if not self._ensure_manager():
            return None
        return self._manager.set_port(port)

    def set_baud(self, baud):
        if not self._ensure_manager():
            return None
        return self._manager.set_baud(baud)

    def connect(self):
        if not self._ensure_manager():
            return False
        return self._manager.connect()

    def disconnect(self):
        if self._manager is None:
            return None
        return self._manager.disconnect()

    def reconnect(self):
        if not self._ensure_manager():
            return False
        return self._manager.reconnect()

    def send(self, message):
        if not self._ensure_manager():
            return False
        return self._manager.send(message)

    def get_line_nowait(self):
        if self._manager is None:
            return None
        return self._manager.get_line_nowait()

    def get_event_nowait(self):
        if self._manager is None:
            return None
        return self._manager.get_event_nowait()

    def connection_metadata(self):
        if self._manager is None:
            return "Unselected", "none"
        return connection_metadata(self._manager)
