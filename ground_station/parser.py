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
    "RECOVERY",
    "RECOVERY_ATTEMPTS",
    "BME_FAIL",
    "IMU_FAIL",
}


def crc16_ccitt(payload):
    crc = 0xFFFF

    for byte in payload.encode("utf-8"):
        crc ^= byte << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc


def verify_crc(line):
    if not line or ",CRC=" not in line:
        return True

    payload, received = line.rsplit(",CRC=", 1)

    try:
        received_crc = int(received, 16)
    except ValueError:
        return False

    return crc16_ccitt(payload) == received_crc


def parse_telemetry(line):
    if not line:
        return None

    line = line.strip()

    if not line.startswith("TEL,"):
        return None

    has_crc = ",CRC=" in line
    if not verify_crc(line):
        return None

    parts = line.split(",")

    if len(parts) < 2:
        return None

    try:
        sequence = int(parts[1])
    except ValueError:
        return None

    data = {
        "sequence": sequence,
        "CRC_VALID": True if has_crc else None,
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
        "BME",
        "IMU",
        "AUX",
        "STATUS",
    }

    return required.issubset(data.keys())
