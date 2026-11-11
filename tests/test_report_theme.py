"""Optional real-browser regression tests: install Playwright and Chromium first."""
import json
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
        (cls.root / "discovery.json").write_text(json.dumps({"candidates": [
            {"id": group, "status": "measured", "repository": f"https://example.test/{group}"}
            for group in ("native", "diagram")
        ]}), encoding="utf-8")
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
        self.page.add_init_script(path=str(Path(__file__).with_name("theme_browser_helpers.js")))
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def open_report(self, theme):
        self.page.emulate_media(color_scheme=theme)
        self.page.goto((self.root / "report.html").as_uri())
        self.page.wait_for_function(
            "typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 2")
        # Await native animation completion before observing a theme-triggered draw.
        # This test hook never calls update(), so it cannot repair a missing update.
        self.page.wait_for_function("""Object.values(Chart.instances).every(
            chart => window.themeRendered.includes(chart.canvas.id))""")
        self.page.evaluate("() => new Promise(requestAnimationFrame)")
        self.assertEqual(self.errors, [])

    def assert_drawn_titles(self, expected):
        try:
            self.page.wait_for_function("""expected =>
                Object.values(Chart.instances).every(chart => window.themeDraws.some(draw =>
                    draw.canvas === chart.canvas.id &&
                    draw.text === chart.options.plugins.title.text && draw.color === expected))
            """, arg=expected, timeout=3000)
        except Exception:
            self.fail(f"Missing actual canvas title draw in {expected}: " +
                      str(self.page.evaluate("window.themeDraws")))
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
        self.assert_drawn_titles(expected)
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
            self.page.evaluate("window.themeDraws = []")
            self.page.emulate_media(color_scheme=theme)
            self.assert_theme(theme)
            self.assertEqual(before, self.page.evaluate(
                "Object.values(Chart.instances).map(c => JSON.stringify(c.data))"))
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

    def assert_element_contrast(self, locator, label):
        self.assertGreater(locator.count(), 0, label)
        for element in locator.all():
            self.assertTrue(element.inner_text().strip(), f"{label}: empty text fixture")
            result = element.evaluate("el => window.textContrast(el)")
            self.assertGreaterEqual(result["ratio"], 4.5, f"{label}: {result}")

    def test_actual_text_contrast(self):
        selectors = [
            "header h1", "header p", ".meta-item", ".section h2", ".section > p",
            "thead th", ".lib-name a", ".version", ".lib-type", ".lib-desc",
            ".bench-cell", ".bench-cell .ci", ".bench-cell.na",
            ".bench-cell.fastest", ".diagnostics p", "footer", "footer a",
        ]
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.open_report(theme)
                for selector in selectors:
                    self.assert_element_contrast(self.page.locator(selector), f"{theme} {selector}")

    def test_actual_link_hover_and_focus_contrast(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.open_report(theme)
                link = self.page.locator(".lib-name a").first
                link.hover()
                # Wait for the existing color transition to finish.
                link.evaluate("async el => { await Promise.all(el.getAnimations().map(a => a.finished)); }")
                self.assert_element_contrast(link, f"{theme} hover")
                self.assertEqual(link.evaluate("el => getComputedStyle(el).textDecorationLine"), "underline")
                self.page.mouse.move(0, 0)
                self.page.keyboard.press("Tab")
                focused = self.page.locator(":focus-visible")
                self.assert_element_contrast(focused, f"{theme} focus")
                self.assertEqual(focused.evaluate("el => getComputedStyle(el).outlineStyle"), "solid")

    def assert_lifecycle_refresh(self, event):
        self.open_report("light")
        self.page.evaluate("""() => {
            window.themeDraws = [];
            document.documentElement.style.setProperty('--text', '#123456');
        }""")
        # Isolate this listener without media changes, resize, navigation or a
        # test-issued chart.update(). These synthetic events do not prove bfcache.
        self.page.evaluate(event)
        self.assert_drawn_titles("#123456")

    def test_synthetic_pageshow_refreshes_canvas(self):
        self.assert_lifecycle_refresh("window.dispatchEvent(new PageTransitionEvent('pageshow'))")

    def test_synthetic_visible_event_refreshes_canvas(self):
        self.assert_lifecycle_refresh("""() => {
            if (document.hidden) throw new Error('Expected visible test page');
            document.dispatchEvent(new Event('visibilitychange'));
        }""")

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
