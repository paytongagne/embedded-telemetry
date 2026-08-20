import unittest
from unittest.mock import patch

from ground_station.stats import TelemetryStats


class PacketLossTests(unittest.TestCase):
    def test_sequence_gap_counts_lost_packets(self):
        stats = TelemetryStats()
        stats.update({"sequence": 10})
        stats.update({"sequence": 14})

        self.assertEqual(stats.total_packets, 2)
        self.assertEqual(stats.lost_packets, 3)
        self.assertAlmostEqual(stats.packet_loss_percent, 60.0)

    def test_contiguous_sequence_has_no_loss(self):
        stats = TelemetryStats()
        for sequence in range(1, 6):
            stats.update({"sequence": sequence})

        self.assertEqual(stats.lost_packets, 0)
        self.assertEqual(stats.packet_loss_percent, 0.0)

    def test_average_packet_rate(self):
        stats = TelemetryStats()

        with patch("ground_station.stats.time.time", side_effect=[0.0, 1.0, 1.5, 2.0]):
            stats.session_start_time = 0.0
            stats.update({"sequence": 1})
            stats.update({"sequence": 2})
            stats.update({"sequence": 3})

        self.assertAlmostEqual(stats.packet_rate_hz, 2.0)
        self.assertAlmostEqual(stats.average_packet_rate_hz, 1.5)

    def test_malformed_packet_counter(self):
        stats = TelemetryStats()
        stats.update(None)
        stats.update(None)
        self.assertEqual(stats.malformed_packets, 2)


if __name__ == "__main__":
    unittest.main()
