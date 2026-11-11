pluginManagement { repositories { gradlePluginPortal(); mavenCentral() } }
rootProject.name = "mermaid-kmp-benchmark"
include("native", "lugf", "diagram", "bench")
