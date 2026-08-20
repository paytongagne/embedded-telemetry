import unittest
from unittest.mock import patch

from ground_station.stats import TelemetryStats


class PacketLossTests(unittest.TestCase):
    def test_sequence_gap_counts_lost_packets(self):
        stats = TelemetryStats()

        with patch("ground_station.stats.time.time", side_effect=[1.0, 2.0]):
            stats.update({"sequence": 10})
            stats.update({"sequence": 13})

        self.assertEqual(stats.total_packets, 2)
        self.assertEqual(stats.lost_packets, 2)

    def test_consecutive_packets_do_not_count_as_lost(self):
        stats = TelemetryStats()

        with patch("ground_station.stats.time.time", side_effect=[1.0, 2.0, 3.0]):
            stats.update({"sequence": 1})
            stats.update({"sequence": 2})
            stats.update({"sequence": 3})

        self.assertEqual(stats.lost_packets, 0)
        self.assertEqual(stats.total_packets, 3)

    def test_malformed_packet_counter(self):
        stats = TelemetryStats()
        stats.update(None)
        self.assertEqual(stats.malformed_packets, 1)

    def test_packet_rate_is_calculated(self):
        stats = TelemetryStats()

        with patch("ground_station.stats.time.time", side_effect=[10.0, 10.5]):
            stats.update({"sequence": 1})
            stats.update({"sequence": 2})

        self.assertAlmostEqual(stats.packet_rate_hz, 2.0)


if __name__ == "__main__":
    unittest.main()
