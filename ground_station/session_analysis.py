import math


def _finite(values):
    return [float(value) for value in values if value is not None]


def _rms(values):
    values = _finite(values)
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def _vector_magnitudes(rows, keys):
    output = []
    for row in rows:
        values = [row.get(key) for key in keys]
        if any(value is None for value in values):
            continue
        output.append(math.sqrt(sum(float(value) ** 2 for value in values)))
    return output


def summarize_session(rows):
    if not rows:
        return {
            "packet_count": 0,
            "duration_seconds": 0.0,
            "temperature_min_c": None,
            "temperature_max_c": None,
            "accel_rms_g": None,
            "gyro_rms_dps": None,
            "crc_invalid": 0,
            "fault_packets": 0,
            "degraded_packets": 0,
        }

    times = [row.get("device_time_ms") for row in rows if row.get("device_time_ms") is not None]
    duration = 0.0
    if len(times) >= 2:
        duration = max(0.0, (float(times[-1]) - float(times[0])) / 1000.0)

    temperatures = _finite(row.get("temperature_c") for row in rows)
    accel = _vector_magnitudes(rows, ("ax_g", "ay_g", "az_g"))
    gyro = _vector_magnitudes(rows, ("gx_dps", "gy_dps", "gz_dps"))

    states = [str(row.get("system_state") or "").upper() for row in rows]

    return {
        "packet_count": len(rows),
        "duration_seconds": duration,
        "temperature_min_c": min(temperatures) if temperatures else None,
        "temperature_max_c": max(temperatures) if temperatures else None,
        "accel_rms_g": _rms(accel),
        "gyro_rms_dps": _rms(gyro),
        "crc_invalid": sum(1 for row in rows if row.get("crc_valid") in (0, False)),
        "fault_packets": states.count("FAULT"),
        "degraded_packets": states.count("DEGRADED"),
    }


def compare_summaries(baseline, candidate):
    keys = (
        "packet_count",
        "duration_seconds",
        "temperature_min_c",
        "temperature_max_c",
        "accel_rms_g",
        "gyro_rms_dps",
        "crc_invalid",
        "fault_packets",
        "degraded_packets",
    )
    result = {}
    for key in keys:
        base = baseline.get(key)
        new = candidate.get(key)
        delta = None
        percent = None

        if base is not None and new is not None:
            delta = float(new) - float(base)
            if float(base) != 0.0:
                percent = (delta / abs(float(base))) * 100.0

        result[key] = {
            "baseline": base,
            "candidate": new,
            "delta": delta,
            "percent_change": percent,
        }
    return result
