"""Generate the reference-style report from JMH output; generated reports stay untracked."""
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY_NAMES = {"rust-kmp": "mermaid-rust-kmp", "native": "mermaid-native", "lugf": "lugf027/mermaid", "cmp": "cmp-mermaid", "diagram": "huarangmeng/diagram"}
DESCRIPTIONS = {"rust-kmp": "Rust renderer through the public KMP/JNI API", "native": "Pure Kotlin; JVM source adaptation", "lugf": "Pure Kotlin Mermaid parser and SVG renderer", "cmp": "Compose scene construction; painting excluded", "diagram": "Mermaid lexer + parser to IR snapshot"}
STAGES = [("svg", "SVG", "End-to-end parsing, layout and SVG output"), ("parse", "Parse", "Parsing to model; no layout"), ("scene", "Scene", "Parsing, layout and scene generation; no painting")]
COLORS = ["#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6"]


def esc(value):
    return html.escape(str(value), quote=True)


def format_time(us):
    if not isinstance(us, (int, float)) or not math.isfinite(us):
        return "—"
    if us < 1:
        return f"{us * 1000:.1f} ns"
    if us < 1000:
        return f"{us:.2f} µs"
    if us < 1000000:
        return f"{us / 1000:.2f} ms"
    return f"{us / 1000000:.3f} s"


def script_json(value):
    # Repository metadata must not close the script element.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_results(rows, libraries=None):
    libraries = libraries or {}
    sections, charts = [], []
    chart_index = 0
    for stage, output, description in STAGES:
        chosen = [r for r in rows if r["params"]["operation"].endswith(":" + stage)]
        if not chosen:
            continue
        cases = sorted({r["params"]["caseName"] for r in chosen})
        groups = sorted({r["params"]["operation"].split(":")[0] for r in chosen})
        data = {(r["params"]["operation"].split(":")[0], r["params"]["caseName"]): r["primaryMetric"] for r in chosen}
        fastest = {case: min(data[g, case]["score"] for g in groups if (g, case) in data) for case in cases}
        table_rows = []
        for group in groups:
            meta = libraries.get(group, {})
            name = LIBRARY_NAMES.get(group, group)
            version = meta.get("version", "source")
            url = meta.get("repository", "#")
            cells = []
            for case in cases:
                metric = data.get((group, case))
                if metric is None:
                    cells.append('<td class="bench-cell na">N/A</td>')
                    continue
                low, high = metric.get("scoreConfidence", [None, None])
                highlight = " fastest" if metric["score"] == fastest[case] else ""
                cells.append(f'<td class="bench-cell{highlight}">{format_time(metric["score"])}<span class="ci">[{format_time(low)} .. {format_time(high)}]</span></td>')
            table_rows.append(f'<tr><td class="lib-name"><a href="{esc(url)}" target="_blank" rel="noopener">{esc(name)}</a><span class="version">{esc(version)}</span></td><td class="lib-type">{output}</td><td class="lib-desc">{esc(meta.get("description", ""))}</td>{"".join(cells)}</tr>')
        headers = "".join(f'<th class="bench-header">{esc(case)}</th>' for case in cases)
        canvases = []
        for case_index, case in enumerate(cases):
            present = [g for g in groups if (g, case) in data]
            chart_id = f"chart_{chart_index}"
            chart_index += 1
            color = COLORS[case_index % len(COLORS)]
            datasets = {"labels": [LIBRARY_NAMES.get(g, g) for g in present], "datasets": [{"label": case + " (µs)", "data": [data[g, case]["score"] for g in present], "backgroundColor": color + "44", "borderColor": color, "borderWidth": 2, "borderRadius": 6}]}
            options = {"responsive": True, "maintainAspectRatio": False, "indexAxis": "y", "plugins": {"legend": {"display": False}, "title": {"display": True, "text": case, "font": {"size": 16, "weight": "600"}, "color": "#1e293b", "padding": {"bottom": 16}}}, "scales": {"x": {"beginAtZero": True, "title": {"display": True, "text": "Time (µs)", "font": {"size": 13}}, "grid": {"color": "#e2e8f0"}, "ticks": {"font": {"size": 12}}}, "y": {"grid": {"display": False}, "ticks": {"font": {"size": 13, "weight": "500"}}}}}
            charts.append(f'new Chart(document.getElementById("{chart_id}").getContext("2d"), {{type: "bar", data: {script_json(datasets)}, options: {script_json(options)}}});')
            canvases.append(f'<div class="chart-card"><canvas id="{chart_id}" role="img" aria-label="{esc(output + ": " + case)}"></canvas></div>')
        sections.append(f'<div class="section" id="{stage}"><h2>Results Table · {output}</h2><p>{esc(description)}. Average time; lower is better.</p><div class="table-wrap"><table><thead><tr><th>Library</th><th>Output</th><th>Description</th>{headers}</tr></thead><tbody>{"".join(table_rows)}</tbody></table></div></div><div class="section"><h2>Visual Comparison · {output}</h2><div class="charts-grid">{"".join(canvases)}</div></div>')
    return "".join(sections), "\n".join(charts)


def generate(root=ROOT):
    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))
    rows = read("results/jmh.json")
    if not rows:
        raise ValueError("No benchmark measurements found")
    environment = read("results/environment.json")
    preflight = read("results/preflight.json")
    discovery = read("discovery.json")
    libraries = {}
    for entry in discovery["candidates"]:
        if entry["status"] != "measured":
            continue
        lock = environment.get("libraries", {}).get(entry["id"], {})
        artifact = lock.get("artifact", "")
        libraries[entry["id"]] = {"repository": entry["repository"], "version": artifact.split(":")[-1] if artifact else entry.get("commit", "source")[:8], "description": DESCRIPTIONS.get(entry["id"], "")}
    sections, charts = render_results(rows, libraries)
    cases = {r["params"]["caseName"] for r in rows}
    groups = {r["params"]["operation"].split(":")[0] for r in rows}
    meta = [environment.get("finished_utc", environment["started_utc"]), f"{len(groups)} libraries", f"{len(cases)} test cases", f"{len(rows)} measurements"]
    failures = [r for r in preflight if r.get("status") != "ok"] + environment.get("failures", [])
    diagnostics = ""
    if failures:
        messages = "".join(f'<p>{esc(r["operation"])} / {esc(r["caseName"])}: {esc(r.get("error", "failed"))}</p>' for r in failures)
        diagnostics = f'<div class="section"><h2>Skipped Measurements</h2>{messages}</div>'
    result = (root / "report-template.html").read_text(encoding="utf-8")
    for marker, value in {"__META__": "".join(f'<span class="meta-item">{esc(m)}</span>' for m in meta), "__SECTIONS__": sections, "__CHARTS__": charts, "__DIAGNOSTICS__": diagnostics}.items():
        result = result.replace(marker, value)
    (root / "report.html").write_text(result, encoding="utf-8", newline="\n")
    print(f"Generated report.html with {len(rows)} measurements")


if __name__ == "__main__":
    generate()
