# Repository guidance

- Preserve phase boundaries: parse, scene generation, and end-to-end SVG must never share a speed ranking.
- Keep immutable upstream revisions in libraries.lock.json. Do not modify `.upstream` implementations.
- Exclude failed structural checks from timings and retain their diagnostics.
- Maintain canonical user instructions in README.md and developer details in DEVELOPMENT.md.
- Generated report.html comes from report-template.html and generate_report.py; measurements come only from JMH, never invented placeholders.
- Verify build changes with :bench:installDist and adapter changes with preflight plus relevant JMH smoke cells. Test report generation using python -m unittest discover -s tests.

- Never commit report.html, results/, _site/ or generated comparison evidence. Reports are produced during local runs or CI and published through Pages, following mermaid-rust-benchmark.
