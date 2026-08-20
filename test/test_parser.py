import unittest

from ground_station.parser import (
    crc16_ccitt,
    get_status,
    has_required_fields,
    is_telemetry,
    parse_telemetry,
    verify_crc,
)


def with_crc(payload):
    return f"{payload},CRC={crc16_ccitt(payload):04X}"


class ParserTests(unittest.TestCase):
    def test_parse_complete_packet(self):
        payload = (
            "TEL,42,TIME=12345,TEMP=25.50,PRESS=980.10,HUM=31.20,"
            "AX=0.010,AY=-0.020,AZ=0.999,GX=0.10,GY=0.20,GZ=-0.30,"
            "BME=OK,IMU=OK,AUX=PRESENT,I2C_ERR=0,RECOVERY=0,"
            "BME_FAIL=0,IMU_FAIL=0,STATUS=NORMAL"
        )
        data = parse_telemetry(with_crc(payload))

        self.assertEqual(data["sequence"], 42)
        self.assertEqual(data["TIME"], 12345.0)
        self.assertAlmostEqual(data["TEMP"], 25.50)
        self.assertEqual(data["BME"], "OK")
        self.assertEqual(data["IMU"], "OK")
        self.assertEqual(data["AUX"], "PRESENT")
        self.assertEqual(get_status(data), "NORMAL")
        self.assertTrue(data["CRC_VALID"])
        self.assertTrue(has_required_fields(data))

    def test_crc_rejects_modified_payload(self):
        payload = "TEL,1,TIME=1000,BME=OK,IMU=OK,AUX=PRESENT,STATUS=NORMAL"
        line = with_crc(payload)
        corrupted = line.replace("TIME=1000", "TIME=1001")

        self.assertTrue(verify_crc(line))
        self.assertFalse(verify_crc(corrupted))
        self.assertIsNone(parse_telemetry(corrupted))

    def test_legacy_packet_without_crc_is_supported(self):
        line = "TEL,2,TIME=2000,BME=OK,IMU=OK,AUX=PRESENT,STATUS=NORMAL"
        data = parse_telemetry(line)
        self.assertIsNotNone(data)
        self.assertTrue(has_required_fields(data))

    def test_non_telemetry_rejected(self):
        self.assertIsNone(parse_telemetry("ACK,STATUS"))
        self.assertFalse(is_telemetry("STATUS,STATE=NORMAL"))

    def test_invalid_sequence_rejected(self):
        self.assertIsNone(parse_telemetry("TEL,ABC,TIME=1000"))

    def test_fault_packet_can_still_be_parsed(self):
        payload = (
            "TEL,9,TIME=9000,BME=OK,IMU=FAULT,AUX=PRESENT,"
            "I2C_ERR=0,RECOVERY=0,BME_FAIL=0,IMU_FAIL=1,STATUS=DEGRADED"
        )
        data = parse_telemetry(with_crc(payload))

        self.assertIsNotNone(data)
        self.assertEqual(data["sequence"], 9)
        self.assertEqual(data["IMU"], "FAULT")
        self.assertEqual(data["STATUS"], "DEGRADED")
        self.assertTrue(has_required_fields(data))


if __name__ == "__main__":
    unittest.main()
