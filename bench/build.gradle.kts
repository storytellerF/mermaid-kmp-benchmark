import java.security.MessageDigest
plugins { kotlin("jvm"); application }
val lock = groovy.json.JsonSlurper().parse(rootProject.file("libraries.lock.json")) as Map<*, *>
val cmpArtifact = (lock["cmp"] as Map<*, *>)["artifact"] as String
kotlin { jvmToolchain(21) }
dependencies {
 implementation(cmpArtifact) { version { strictly(cmpArtifact.substringAfterLast(':')) } }
 implementation(project(":native")); implementation(project(":lugf")); implementation(project(":diagram"))
 implementation("io.github.storytellerf:mermaidffi-kmp:0.0.1-alpha5")
 testImplementation(kotlin("test"))
 implementation("org.openjdk.jmh:jmh-core:1.37")
 annotationProcessor("org.openjdk.jmh:jmh-generator-annprocess:1.37")
 implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.10.0")
}
application { mainClass.set("bench.MainKt") }
sourceSets.main { resources.srcDir("../test-data") }
val verifyPublishedArtifacts by tasks.registering {
 inputs.files(configurations.runtimeClasspath)
 inputs.file(rootProject.file("libraries.lock.json"))
 doLast {
  val lock = groovy.json.JsonSlurper().parse(rootProject.file("libraries.lock.json")) as Map<*, *>
  lock.forEach { (name, value) ->
   val library = value as Map<*, *>
   val coordinate = library["artifact"] as? String
   if (coordinate != null) {
    val (group, module, version) = coordinate.split(":")
    val artifact = configurations.runtimeClasspath.get().resolvedConfiguration.resolvedArtifacts.single {
     val id = it.moduleVersion.id
     id.group == group && id.name == "$module-jvm" && id.version == version
    }.file
    val digest = MessageDigest.getInstance("SHA-256").digest(artifact.readBytes()).joinToString("") { "%02x".format(it) }
    check(digest == library["jvm_artifact_sha256"]) { "$name JVM artifact checksum mismatch: $coordinate" }
    logger.lifecycle("Verified $coordinate JVM artifact SHA-256")
   }
  }
 }
}
tasks.named("compileKotlin") { dependsOn(verifyPublishedArtifacts) }
tasks.named("installDist") { dependsOn(verifyPublishedArtifacts) }
