# 开发指南

## 构建与验证

需要 JDK 21、Python 3.10+、Git 和网络访问。

```sh
python prepare.py
# Windows: gradlew.bat; Unix: ./gradlew
./gradlew :bench:installDist :bench:test --console=plain
python run_benchmarks.py --profile smoke
python -m unittest discover -s tests
```

Unix 系统上确保 `gradlew` 可执行（`chmod +x gradlew`）。`prepare.py` 在 `.upstream/` 获取固定修订版本的稀疏检出，核验 HEAD，并拒绝存在受跟踪文件修改的检出。更换版本时，显式更新 `libraries.lock.json`，再使用新的干净检出；不得通过修改下载的实现来提高分数。

## 架构

四个 Kotlin 上游实现分别在独立、包含 JVM 目标的 KMP 模块中编译。Rust KMP 使用固定的 Maven Central 构件 `io.github.storytellerf:mermaidffi-kmp:0.0.1-alpha5`；源码检出仅记录来源，不重新构建。`:bench:verifyRustArtifact` 在 installDist 之前，根据 libraries.lock.json 核验解析得到的 JVM JAR 的 SHA-256。`bench` 管理 Kotlin 适配层和 Java JMH 入口；使用 Java 是为了 JMH 注解处理器，与并发无关。基准测试不使用自定义计时循环。源码资源加载和结构预检在 trial setup 中执行，不计入测量。引擎会复用；每次操作重新解析源码，测试工具不提供预生成场景或输出缓存。库自身的内部行为予以保留。

`diagram` 将 core 和 parser 源码合并，使适配层能够使用其词法分析器。Native 合并四个纯模块，补充必需的 clock actual 和上游生成的版本常量。本测试语料不使用该版本常量。有意不应用上游平台或构建插件，因此无需 Android SDK 或 Apple 工具链。源码保持不变。

源码模块依赖使用 Kotlin 2.3.21、serialization JSON 1.10.0 和 coroutines 1.11.0；CMP 还使用 kaml 0.104.0 和 datetime 0.7.1。这些是本基准测试的工具链选择，不代表上游发布版本的依赖。

## 语料与验证

三份 `.mmd` 文件从参考项目的 `test-data/` 原样复制。每次运行保存其 SHA-256，具体参考修订版本记录在 `test-data/provenance.json` 中。预期节点／边数量：简单图 4/3，复杂图 11/13；时序图参与者／消息数量为 3/8。Native 和 lugf 的 SVG 用例同时验证解析器结构。Rust KMP 只公开端到端 SVG 操作：setup 将 SVG 解析为 XML，要求包含图形元素和预期标签（忽略空白，使换行的 tspan 仍然有效），但无法检查 AST。计时操作调用公开 KMP 门面，包含 JNI、原生渲染和返回字符串转换。原生库加载不计入测量。CMP 只验证场景生成成功、输出非空且尺寸为正。Diagram 拒绝词法错误和 ERROR 诊断，并验证 IR 数量。每个 JMH fork 内的 setup 都会再次验证各测量单元。

验证范围有意保持有限：它不能证明标签保真度、子图几何、布局质量或像素一致性。SVG 样本会保留供审查。预检先重复调用，再改动源码，然后恢复原始源码；结构数量可以发现累积问题，但不能证明一般情况下的缓存失效行为。Rust KMP 还会根据修改后的输入，检查简单图中改动的节点标签。

## 测量与报告

标准配置使用 2 个 fork、5 次预热和 8 次测量，每次 1 秒；使用 1 个线程、512 MiB 初始堆、1 GiB 最大堆、JMH 1.37 及其 GC profiler。冒烟配置使用 1 个 fork、2 次预热和 3 次测量，结果应标为探索性数据。需要更可靠的比较时，应在空闲机器上使用一致的电源设置运行。当前共享会话并非隔离的性能实验室。

每个成功的测量单元使用独立 JMH 进程、JSON 和日志，超时为 300 秒。失败会被记录，不能作为快速结果报告。汇总只包含本次调用的结果。报告沿用 mermaid-rust-benchmark 的渐变页头、结果矩阵、最快单元高亮和 Chart.js 横向图表，包括参考配色、字体和卡片样式。每个 KMP 测量阶段都有独立的矩阵和图表组。JMH 报告平均耗时及 99.9% 置信区间，不能将其标为 Criterion 的中位数。原始 JSON 中的 JVM 分配指标不包含 Rust 原生堆分配。

`generate_report.py` 根据当前 JMH 数据渲染 `report-template.html`。模板的视觉样式改编自 mermaid-rust-benchmark。报告从与参考报告相同的 CDN 加载 Chart.js 4。`tests` 覆盖阶段分离、缺失测量值、安全渲染数据和失败行处理；`:bench:test` 覆盖 SVG 验证。

生成的 `report.html`、`results/`（含原始 JSON、环境记录、日志和 SVG 样本）、`_site/` 以及临时源码比较证据均被忽略。不得提交基准测试输出或机器专用的结果快照。只提交输入、元数据、代码和报告模板。CI 自行生成报告并通过 Pages 发布，不将产物提交回 Git。

## CI

`.github/workflows/deploy-pages.yml` 参考 mermaid-rust-benchmark：涉及相关路径的 main push 和手动触发会执行标准基准测试，上传 Pages 包，再由依赖它的 `deploy` 作业自动部署。没有单独的发布输入或 pull request 冒烟工作流。Pages 包包含作为 index.html 的报告，以及关联的 JSON 数据和 SVG 样本。Pages 并发使用 `pages` 组，并启用 cancel-in-progress。在仓库设置中选择通过 GitHub Actions 启用 Pages。不同硬件上的运行不能合并成同一个排名；本地和在线 CI 测量各自描述其环境。本地脚本只生成文件。

## 来源与许可

上游代码通过获取方式使用，而非随仓库内置，仍遵循各自的 MIT/Apache-2.0 许可证。参阅固定提交中的上游 LICENSE/NOTICE。语料来源为参考仓库；这里不表示对上游内容整体重新授权。
