VALID_COMMANDS = {
    "STATUS",
    "SET_RATE",
    "PAUSE",
    "RESUME",
    "RESET",
    "CLEAR_FAULTS",
    "INJECT_FAULT",
}

MIN_RATE_MS = 100
MAX_RATE_MS = 10000


def build_command(name, value=None):
    name = name.strip().upper()

    if name not in VALID_COMMANDS:
        raise ValueError(f"Unsupported command: {name}")

    if value is None:
        return f"CMD,{name}"

    return f"CMD,{name},{value}"


def parse_response(line):
    if not line:
        return None

    line = line.strip()
    parts = line.split(",")

    if not parts:
        return None

    response_type = parts[0]

    if response_type == "ACK":
        return {
            "type": "ACK",
            "command": parts[1] if len(parts) > 1 else None,
            "value": parts[2] if len(parts) > 2 else None,
            "raw": line,
        }

    if response_type == "ERR":
        return {
            "type": "ERR",
            "error": parts[1] if len(parts) > 1 else "UNKNOWN",
            "details": ",".join(parts[2:]) if len(parts) > 2 else "",
            "raw": line,
        }

    if response_type == "STATUS":
        data = {
            "type": "STATUS",
            "raw": line,
        }

        for item in parts[1:]:
            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            data[key] = value

        return data

    return {
        "type": "UNKNOWN",
        "raw": line,
    }


def command_status():
    return build_command("STATUS")


def command_set_rate(milliseconds):
    milliseconds = int(milliseconds)

    if not MIN_RATE_MS <= milliseconds <= MAX_RATE_MS:
        raise ValueError(
            f"Telemetry rate must be between {MIN_RATE_MS} and {MAX_RATE_MS} ms"
        )

    return build_command("SET_RATE", milliseconds)


def command_pause():
    return build_command("PAUSE")


def command_resume():
    return build_command("RESUME")


def command_reset():
    return build_command("RESET")


def command_clear_faults():
    return build_command("CLEAR_FAULTS")


def command_inject_fault(target):
    target = target.strip().upper()

    valid_targets = {
        "IMU",
        "BME",
    }

    if target not in valid_targets:
        raise ValueError(f"Unsupported fault target: {target}")

    return build_command("INJECT_FAULT", target)
