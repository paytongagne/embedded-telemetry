NUMERIC_KEYS = {
    "TIME",
    "TEMP",
    "PRESS",
    "HUM",
    "AX",
    "AY",
    "AZ",
    "GX",
    "GY",
    "GZ",
    "DIST",
    "TOF_TIMEOUT",
    "I2C_ERR",
}


def parse_telemetry(line):
    if not line:
        return None

    line = line.strip()

    if not line.startswith("TEL,"):
        return None

    parts = line.split(",")

    if len(parts) < 2:
        return None

    try:
        sequence = int(parts[1])
    except ValueError:
        return None

    data = {
        "sequence": sequence
    }

    for item in parts[2:]:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key in NUMERIC_KEYS:
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = None
        else:
            data[key] = value

    return data


def is_telemetry(line):
    return bool(line and line.strip().startswith("TEL,"))


def get_status(data):
    if not data:
        return "UNKNOWN"

    return data.get("STATUS", "UNKNOWN")


def has_required_fields(data):
    if not data:
        return False

    required = {
        "sequence",
        "TIME",
        "TEMP",
        "PRESS",
        "HUM",
        "AX",
        "AY",
        "AZ",
        "GX",
        "GY",
        "GZ",
    }

    return required.issubset(data.keys())