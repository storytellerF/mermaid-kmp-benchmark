# mermaid-kmp-benchmark

用于比较 Kotlin Multiplatform Mermaid 库性能的基准测试。

**在线报告：**[storytellerf.github.io/mermaid-kmp-benchmark](https://storytellerf.github.io/mermaid-kmp-benchmark/)

<a id="libraries"></a>

## 参与比较的库

| 库 | 修订版本／版本号 | 测量的输出 | 说明 |
| --- | --- | --- | --- |
| [mermaid-rust-kmp](https://github.com/storytellerF/mermaid-rust-kmp) | 0.0.1-alpha5 | SVG | 通过 JNI 调用 Rust 的公开 KMP API |
| [mermaid-native](https://github.com/botiverse/mermaid-native) | 01c34d8b | 解析、SVG | 基于纯 Kotlin 通用源码适配的 JVM 版本 |
| [lugf027/mermaid](https://github.com/lugf027/mermaid) | f73ba76b | 解析、SVG | 纯 Kotlin Mermaid 解析器与 SVG 渲染器 |
| [cmp-mermaid](https://github.com/swithun-liu/cmp-mermaid) | 3eaad1a3 | 场景 | 解析、布局及 Compose 场景生成，不包括绘制 |
| [huarangmeng/diagram](https://github.com/huarangmeng/diagram) | bc709ec1 | 解析 | Mermaid 词法分析、语法解析及 IR 快照 |

完整源码修订版本和 Rust KMP 构件校验和固定在 [libraries.lock.json](libraries.lock.json) 中。候选库清单见 [discovery.json](discovery.json)。

<a id="test-cases"></a>

## 测试用例

每种支持的操作都使用三份输入进行测量：

- **simple_flowchart**：4 个节点的 LR 流程图。
- **complex_flowchart**：包含子图和循环的 11 节点 TD 流程图。
- **sequence_diagram**：3 个参与者、8 条消息的时序图。

[JMH](https://github.com/openjdk/jmh) 测量操作的平均耗时。解析、场景生成和端到端 SVG 渲染分别报告。预检失败的项目不计入耗时，并在报告中展示。

<a id="run-locally"></a>

## 本地运行

前置要求：JDK 21、Python 3.10+、Git 和网络访问。

```sh
git clone https://github.com/storytellerF/mermaid-kmp-benchmark.git
cd mermaid-kmp-benchmark
# Linux/macOS only: chmod +x gradlew
python run_benchmarks.py
# Open report.html in the project root
```

快速检查整个执行流程：

```sh
python run_benchmarks.py --profile smoke
```

标准配置启动 2 个 JVM fork，每个执行 5 次预热和 8 次测量，每次 1 秒。冒烟结果仅用于检查执行流程。

报告、原始测量数据、日志和 SVG 样本在本地或 CI 中生成，不提交到仓库。可使用 `python generate_report.py` 从已有测量数据重新生成 HTML。

<a id="interpreting-results"></a>

## 解读结果

只比较同一测量阶段、同一输入下的库。布局、文字度量和输出保真度的差异都会影响负载。结果描述的是记录下来的 JVM 环境，不代表 Android、iOS、Kotlin/Native、JS 或 Wasm 的性能。

mermaid-native 的源码适配并不是上游支持的桌面目标。Rust KMP 使用已发布的 JVM 二进制，每次调用包含 JNI 和字符串转换成本，首次原生库加载不计入耗时。JVM 分配指标不包含 Rust 原生堆分配。

开发环境配置、验证与 CI 行为见 [DEVELOPMENT.md](DEVELOPMENT.md)。
