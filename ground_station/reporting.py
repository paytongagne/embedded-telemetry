from datetime import datetime, timezone
from html import escape
from pathlib import Path


def write_validation_report(results, passed, output_dir="reports", metadata=None):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    generated = datetime.now(timezone.utc)
    filename = generated.strftime("validation_%Y%m%d_%H%M%S_utc.html")
    path = output / filename
    metadata = dict(metadata or {})

    rows = []
    for result in results:
        elapsed = "--" if result.elapsed_seconds is None else f"{result.elapsed_seconds:.3f} s"
        rows.append(
            "<tr>"
            f"<td>{escape(result.name)}</td>"
            f"<td>{escape(result.status)}</td>"
            f"<td>{escape(elapsed)}</td>"
            f"<td>{escape(result.detail or '')}</td>"
            "</tr>"
        )

    metadata_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in metadata.items()
    )

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Embedded Telemetry Validation Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
h1 {{ margin-bottom: 4px; }}
.summary {{ font-size: 22px; font-weight: 700; margin: 16px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }}
th {{ background: #f3f4f6; }}
.small {{ color: #6b7280; font-size: 13px; }}
</style>
</head>
<body>
<h1>Embedded Telemetry Fault-Recovery Validation</h1>
<div class="small">Generated {escape(generated.isoformat())}</div>
<div class="summary">Overall result: {"PASS" if passed else "FAIL"}</div>
<table>
<tr><th>Test step</th><th>Status</th><th>Elapsed</th><th>Detail</th></tr>
{''.join(rows)}
</table>
<h2>Run Metadata</h2>
<table>
{metadata_rows or '<tr><td>No additional metadata recorded.</td></tr>'}
</table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return path
