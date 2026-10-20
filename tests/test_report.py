import json
import tempfile
import unittest
from pathlib import Path
import generate_report


def row(operation, case="simple_flowchart", score=2.5):
    return {"params": {"operation": operation, "caseName": case}, "primaryMetric": {"score": score, "scoreConfidence": [score * 0.9, score * 1.1]}}


class ReportTests(unittest.TestCase):
    def test_escapes_html_metadata(self):
        section, _ = generate_report.render_results([row("untrusted<script>:svg")])
        self.assertIn("untrusted&lt;script&gt;", section)
        self.assertNotIn("untrusted<script>", section)

    def test_script_data_cannot_close_script_element(self):
        _, charts = generate_report.render_results([row("</script>:svg")])
        self.assertNotIn("</script>", charts)
        self.assertIn("\\u003c", charts)

    def test_formats_time_units(self):
        for value, expected in [(0.5, "500.0 ns"), (2.5, "2.50 µs"), (2500, "2.50 ms"), (2500000, "2.500 s")]:
            with self.subTest(value=value):
                self.assertEqual(generate_report.format_time(value), expected)

    def test_each_stage_has_separate_matrix_and_charts(self):
        sections, charts = generate_report.render_results([row("rust-kmp:svg"), row("native:parse")])
        self.assertEqual(sections.count("<table>"), 2)
        self.assertEqual(charts.count("new Chart("), 2)
        svg, parse = sections.split('<div class="section" id="parse">')
        self.assertIn("mermaid-rust-kmp", svg)
        self.assertNotIn("mermaid-rust-kmp", parse)

    def test_missing_measurement_is_na(self):
        sections, _ = generate_report.render_results([row("native:parse"), row("native:parse", "complex_flowchart"), row("diagram:parse")])
        self.assertIn('class="bench-cell na">N/A', sections)

    def test_highlights_lowest_score_in_each_input(self):
        sections, _ = generate_report.render_results([row("native:svg", score=2), row("lugf:svg", score=4)])
        self.assertEqual(sections.count('class="bench-cell fastest"'), 1)
        self.assertIn('class="bench-cell fastest">2.00 µs', sections)

    def fixture(self, root, rows, preflight):
        (root / "results").mkdir()
        (root / "report-template.html").write_text((generate_report.ROOT / "report-template.html").read_text(encoding="utf-8"), encoding="utf-8")
        fixtures = {"results/jmh.json": rows, "results/environment.json": {"started_utc": "test", "failures": []}, "results/preflight.json": preflight, "discovery.json": {"candidates": []}}
        for name, value in fixtures.items():
            (root / name).write_text(json.dumps(value), encoding="utf-8")

    def test_failed_preflight_is_diagnostic_not_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, [row("native:parse")], [{"operation": "diagram:parse", "caseName": "complex_flowchart", "status": "failed", "error": "<bad>"}])
            generate_report.generate(root)
            report = (root / "report.html").read_text(encoding="utf-8")
            self.assertIn("Skipped Measurements", report)
            self.assertIn("&lt;bad&gt;", report)
            self.assertNotIn("0.00 µs", report)

    def test_empty_results_fail_instead_of_publishing_blank_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, [], [])
            with self.assertRaisesRegex(ValueError, "No benchmark measurements"):
                generate_report.generate(root)
            self.assertFalse((root / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
