# Development

## Build and verification

JDK 21, Python 3.10+, Git, and network access are required.

```sh
python prepare.py
# Windows: gradlew.bat; Unix: ./gradlew
./gradlew :bench:installDist :bench:test --console=plain
python run_benchmarks.py --profile smoke
python -m unittest discover -s tests
```

On Unix, ensure `gradlew` is executable (`chmod +x gradlew`). `prepare.py` fetches immutable sparse checkouts in `.upstream/`, verifies HEAD and rejects tracked modifications. To change versions, explicitly update `libraries.lock.json`, then use new clean checkouts; never patch downloaded implementations to improve scores.

## Architecture

The four Kotlin upstream implementations are compiled in separate KMP modules with a JVM target. Rust KMP is consumed as the pinned Maven Central artifact `io.github.storytellerf:mermaidffi-kmp:0.0.1-alpha5`; its source checkout records provenance but is not rebuilt. `:bench:verifyRustArtifact` verifies the resolved JVM JAR SHA-256 against libraries.lock.json before installDist. `bench` owns Kotlin adapters and a Java JMH entry point; Java is used for JMH's annotation processor, not for concurrency. The benchmark has no custom timing loop. Source resources are loaded and structural preflight runs in trial setup, outside measurement. Engines are reused; each operation parses the source anew, and no prepared scene or output cache is supplied by the harness. Library-owned internal behavior is retained.

`diagram` combines its core/parser sources so its lexer can be used in the adapter. Native combines four pure modules and adds the required clock actual and upstream-generated version constant. The version constant is not used by this corpus. Upstream platform/build plugins are intentionally not applied: no Android SDK or Apple toolchain is needed. Source code remains unchanged.

Source module dependencies use Kotlin 2.3.21, serialization JSON 1.10.0 and coroutines 1.11.0; CMP also uses kaml 0.104.0 and datetime 0.7.1. These are benchmark toolchain choices, not a claim about upstream release dependencies.

## Corpus and validation

The three `.mmd` files were copied unchanged from the reference project's `test-data/`. Their SHA-256 hashes are saved with each run; the exact reference revision is recorded in `test-data/provenance.json`. Expected node/edge counts: simple 4/3; complex 11/13. Sequence actor/message counts: 3/8. Native and lugf SVG cases also validate their parser structures. Rust KMP exposes only the public end-to-end SVG operation: setup parses its SVG as XML, requires graphic elements and expected labels (ignoring whitespace so wrapped tspans remain valid), but cannot inspect an AST. The timed operation invokes the public KMP facade including JNI, native rendering and returned string conversion. Native loading is outside measurement. CMP validates successful nonempty scene output and positive dimensions only. Diagram rejects lexer errors and ERROR diagnostics and validates IR counts. Setup validates each cell again inside every JMH fork.

Validation is intentionally bounded: it does not establish label fidelity, subgraph geometry, layout quality, or pixel parity. SVG samples are retained for review. Preflight performs repeated calls with a changed source and then the original source; structural counts detect accumulation but do not prove general cache invalidation. Rust KMP also checks the changed simple node label against the mutated input.

## Measurement and report

The standard profile uses 2 forks, 5 warmup iterations and 8 measurement iterations of 1 second each, 1 thread, 512 MiB initial heap, 1 GiB maximum heap, JMH 1.37 and its GC profiler. The smoke profile uses 1 fork, 2 warmups and 3 measurements; label it exploratory. Run on an idle machine with consistent power settings for stronger comparisons. This shared session is not an isolated performance lab.

Every successful cell gets a separate JMH process, JSON and log with a 300-second timeout. Failures are recorded rather than reported as fast results. The aggregate contains only results from the current invocation. The report follows mermaid-rust-benchmark's gradient header, result matrix, fastest-cell highlighting and Chart.js horizontal charts, including the reference palette, typography and card styling. Each KMP measurement stage has a separate matrix and chart group. JMH reports average time and 99.9% confidence intervals; it must not be relabeled as Criterion's median. JVM allocation metrics in the raw JSON exclude Rust native heap allocations.

`generate_report.py` renders `report-template.html` from current JMH data. The template's visual styling is adapted from mermaid-rust-benchmark. Reports use Chart.js 4 from the same CDN as the reference report. `tests` covers stage separation, missing measurements, safe data rendering and failed-row handling; `:bench:test` covers SVG validation.

Generated `report.html`, `results/` (including raw JSON, environment records, logs and SVG samples), `_site/` and ad-hoc source comparison evidence are ignored. Never commit benchmark output or machine-specific result snapshots. Commit benchmark inputs, metadata, code and the report template only. CI generates its own report and publishes it through Pages without committing the artifact back to Git.


## CI

The `.github/workflows/deploy-pages.yml` workflow follows mermaid-rust-benchmark: relevant pushes to main and manual dispatch run the standard benchmark, upload the Pages bundle, then automatically deploy it in the dependent `deploy` job. There is no separate publish input or pull-request smoke workflow. The Pages bundle includes the report as index.html plus its linked JSON data and SVG samples. Pages concurrency uses the `pages` group with cancel-in-progress enabled. Enable Pages using GitHub Actions in repository settings. Runs on different hardware must not be merged into a single ranking; local and live CI measurements describe their own environments. Local scripts generate files only.

## Attribution

Upstream code is fetched rather than vendored and remains under its respective MIT/Apache-2.0 licenses. See upstream LICENSE/NOTICE at the pinned commits. Corpus provenance is the reference repository; no broad relicensing of upstream material is implied.
