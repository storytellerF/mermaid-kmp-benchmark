"""Optional real-browser regression tests: install Playwright and Chromium first."""
import shutil
import tempfile
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

import generate_report
import test_report


@unittest.skipIf(sync_playwright is None, "Playwright is required for browser theme tests")
class ReportThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        test_report.ReportTests().fixture(cls.root, [
            test_report.row("native:parse"), test_report.row("native:parse", "complex_flowchart"),
            test_report.row("diagram:parse"),
        ], [{"operation": "lugf:svg", "caseName": "simple_flowchart",
             "status": "failed", "error": "Invalid SVG " + "unbroken-diagnostic" * 30}])
        generate_report.generate(cls.root)
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        cls.browser = cls.runtime.chromium.launch(
            executable_path=shutil.which("google-chrome"),
            args=["--no-sandbox"])
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def open_report(self, theme):
        self.page.emulate_media(color_scheme=theme)
        self.page.goto((self.root / "report.html").as_uri())
        self.page.wait_for_function(
            "typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 2")
        self.assertEqual(self.errors, [])

    def assert_theme(self, theme):
        expected = "#f1f5f9" if theme == "dark" else "#1e293b"
        self.page.wait_for_function(
            "expected => Object.values(Chart.instances).every(c => c.options.plugins.title.color === expected)",
            arg=expected)
        palette = self.page.evaluate("""() => {
            const css = getComputedStyle(document.documentElement);
            const value = name => css.getPropertyValue(name).trim();
            return Object.values(Chart.instances).map(chart => ({
                title: chart.options.plugins.title.color,
                tick: chart.options.scales.x.ticks.color,
                grid: chart.options.scales.x.grid.color,
                tooltip: chart.options.plugins.tooltip.bodyColor,
                expected: [value('--text'), value('--muted'), value('--border'), value('--tooltip-text')]
            }));
        }""")
        for chart in palette:
            self.assertEqual([chart["title"], chart["tick"], chart["grid"], chart["tooltip"]], chart["expected"])
        self.assertEqual(self.errors, [])

    def test_initial_theme_matches_system(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.open_report(theme)
                self.assert_theme(theme)

    def test_live_theme_changes_preserve_measurements_and_semantic_colors(self):
        self.open_report("light")
        before = self.page.evaluate("Object.values(Chart.instances).map(c => JSON.stringify(c.data))")
        for theme in ("dark", "light", "dark"):
            self.page.emulate_media(color_scheme=theme)
            self.assert_theme(theme)
        self.assertEqual(before, self.page.evaluate(
            "Object.values(Chart.instances).map(c => JSON.stringify(c.data))"))

    def test_return_to_report_uses_current_system_theme(self):
        self.open_report("light")
        self.page.goto("about:blank")
        self.page.emulate_media(color_scheme="dark")
        self.page.go_back()
        self.assert_theme("dark")
        self.page.reload()
        self.assert_theme("dark")

    def test_text_and_interaction_contrast(self):
        # These pairs include table headers, confidence intervals on highlighted
        # cells, missing results, diagnostics, tooltips and header gradient ends.
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.open_report(theme)
                ratios = self.page.evaluate("""() => {
                    const css = getComputedStyle(document.documentElement);
                    const value = name => css.getPropertyValue(name).trim();
                    const luminance = hex => {
                        const rgb = hex.match(/[a-f0-9]{2}/gi).map(v => parseInt(v, 16) / 255)
                            .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
                        return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
                    };
                    const ratio = (a, b) => {
                        const values = [luminance(a), luminance(b)].sort((a, b) => b - a);
                        return (values[0] + .05) / (values[1] + .05);
                    };
                    const pairs = [];
                    for (const background of ['--page', '--surface', '--surface-alt', '--badge', '--success-bg']) {
                        for (const foreground of ['--text', '--muted', '--link', '--link-hover'])
                            pairs.push([foreground, background]);
                    }
                    pairs.push(['--success', '--success-bg'], ['--error', '--error-bg'],
                               ['--tooltip-text', '--tooltip-bg']);
                    const result = pairs.map(([a, b]) => [a + '/' + b, ratio(value(a), value(b))]);
                    for (const background of ['--header-start', '--header-end']) {
                        result.push(['header/' + background, ratio('#ffffff', value(background))]);
                        // Header metadata uses a 15% black overlay.
                        const end = value(background).slice(1).match(/../g)
                            .map(v => Math.round(parseInt(v, 16) * .85).toString(16).padStart(2, '0')).join('');
                        result.push(['metadata/' + background, ratio('#ffffff', '#' + end)]);
                    }
                    return result;
                }""")
                for pair, ratio in ratios:
                    self.assertGreaterEqual(ratio, 4.5, f"{theme}: {pair}")
                link = self.page.locator(".lib-name a").first
                link.hover()
                self.assertEqual(link.evaluate("el => getComputedStyle(el).textDecorationLine"), "underline")
                self.page.mouse.move(0, 0)
                self.page.keyboard.press("Tab")
                focused = self.page.locator(":focus-visible")
                self.assertGreater(focused.count(), 0)
                self.assertEqual(focused.evaluate("el => getComputedStyle(el).outlineStyle"), "solid")

    def test_tables_and_diagnostics_survive_chart_cdn_failure(self):
        self.page.route("https://cdn.jsdelivr.net/**", lambda route: route.abort())
        self.page.emulate_media(color_scheme="dark")
        self.page.goto((self.root / "report.html").as_uri())
        self.assertEqual(self.page.locator("table").count(), 1)
        self.assertIn("Invalid SVG", self.page.locator(".diagnostics").inner_text())
        self.page.emulate_media(color_scheme="light")
        self.assertEqual(self.page.locator(".bench-cell.na").inner_text(), "N/A")
        self.assertEqual(self.errors, [])

    def test_narrow_viewport_keeps_diagnostics_inside_page(self):
        self.open_report("dark")
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_function("document.documentElement.scrollWidth <= innerWidth")
        self.assertLessEqual(self.page.locator(".diagnostics").evaluate(
            "el => el.scrollWidth"), 390)
