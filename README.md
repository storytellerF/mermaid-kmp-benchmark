# mermaid-kmp-benchmark

Performance benchmark comparing Kotlin Multiplatform Mermaid libraries.

**Live report:** [storytellerf.github.io/mermaid-kmp-benchmark](https://storytellerf.github.io/mermaid-kmp-benchmark/)

## Libraries

| Library | Revision / version | Output measured | Description |
| --- | --- | --- | --- |
| [mermaid-rust-kmp](https://github.com/storytellerF/mermaid-rust-kmp) | 0.0.1-alpha5 | SVG | Public KMP API backed by Rust through JNI |
| [mermaid-native](https://github.com/botiverse/mermaid-native) | 01c34d8b | Parse, SVG | Pure Kotlin common-source JVM adaptation |
| [lugf027/mermaid](https://github.com/lugf027/mermaid) | f73ba76b | Parse, SVG | Pure Kotlin Mermaid parser and SVG renderer |
| [cmp-mermaid](https://github.com/swithun-liu/cmp-mermaid) | 3eaad1a3 | Scene | Parse + layout + Compose scene generation; excludes painting |
| [huarangmeng/diagram](https://github.com/huarangmeng/diagram) | bc709ec1 | Parse | Mermaid lexer + parser + IR snapshot |

Full source revisions and the Rust KMP artifact checksum are pinned in [libraries.lock.json](libraries.lock.json). The candidate inventory is in [discovery.json](discovery.json).

## Test Cases

Each supported operation is benchmarked against three inputs:

- **simple_flowchart** — 4-node LR flowchart.
- **complex_flowchart** — 11-node TD flowchart with subgraphs and a loop.
- **sequence_diagram** — 3 participants and 8 messages.

[JMH](https://github.com/openjdk/jmh) measures average operation time. Parsing, scene generation and end-to-end SVG rendering are reported separately. Failed preflight checks are excluded from timing and shown in the report.

## Run Locally

Prerequisites: JDK 21, Python 3.10+, Git and network access.

```sh
git clone https://github.com/storytellerF/mermaid-kmp-benchmark.git
cd mermaid-kmp-benchmark
# Linux/macOS only: chmod +x gradlew
python run_benchmarks.py
# Open report.html in the project root
```

For a quick pipeline check:

```sh
python run_benchmarks.py --profile smoke
```

The standard profile uses 2 JVM forks, each with 5 warmup iterations and 8 measurement iterations of 1 second. Smoke results are only for checking the pipeline.

Reports, raw measurements, logs and SVG samples are generated locally or in CI; they are not committed to the repository. Regenerate the HTML from existing measurements with `python generate_report.py`.

## Interpreting Results

Compare libraries within the same measurement stage and input. Different layouts, text metrics and output fidelity affect workload. Results describe the recorded JVM environment, not Android, iOS, Kotlin/Native, JS or Wasm performance.

The mermaid-native source adaptation is not an upstream-supported desktop target. Rust KMP uses its published JVM binary and includes per-call JNI/string conversion costs, with initial native loading outside timing. JVM allocation metrics exclude Rust native heap allocations.

Developer setup, verification and CI behavior are documented in [DEVELOPMENT.md](DEVELOPMENT.md).
