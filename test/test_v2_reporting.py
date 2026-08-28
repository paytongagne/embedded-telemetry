import tempfile
import unittest
from pathlib import Path

from ground_station.reporting import write_validation_report
from ground_station.validation import ValidationResult


class ValidationReportTests(unittest.TestCase):
    def test_report_is_written_with_results_and_metadata(self):
        results = [
            ValidationResult(
                name="Baseline NORMAL",
                status="PASS",
                detail="Observed NORMAL",
                elapsed_seconds=0.25,
            )
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = write_validation_report(
                results,
                True,
                output_dir=directory,
                metadata={"firmware": "1.2.3", "session_id": 7},
            )
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("Overall result: PASS", text)
            self.assertIn("Baseline NORMAL", text)
            self.assertIn("1.2.3", text)
            self.assertIn("session_id", text)


if __name__ == "__main__":
    unittest.main()
