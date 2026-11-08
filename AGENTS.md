<a id="repository-guidance"></a>

# 仓库工作指引

- 保持测量阶段的边界：解析、场景生成和端到端 SVG 生成绝不能放在同一个速度排名中。
- 在 libraries.lock.json 中固定不可变的上游修订版本。不要修改 `.upstream` 中的实现。
- 结构检查失败的项目不计入耗时，并保留诊断信息。
- README.md 作为用户说明的权威文档，DEVELOPMENT.md 记录开发细节。
- report.html 由 report-template.html 和 generate_report.py 生成；测量值只能来自 JMH，不能使用编造的占位数据。
- 构建变更通过 :bench:installDist 验证；适配层变更通过预检和相关 JMH 冒烟测量单元验证。报告生成使用 python -m unittest discover -s tests 测试。

- 不得提交 report.html、results/、_site/ 或生成的比较证据。参考 mermaid-rust-benchmark，在本地运行或 CI 中生成报告，再通过 Pages 发布。
