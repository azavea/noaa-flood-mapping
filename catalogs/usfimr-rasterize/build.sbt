organization := "com.azavea"

name := "usfimr-rasterize"

version := "0.1.0-SNAPSHOT"

scalaVersion := "2.12.12"

libraryDependencies ++= Seq(
  "org.locationtech.geotrellis" %% "geotrellis-gdal" % "3.4.0",
  "org.locationtech.geotrellis" %% "geotrellis-raster" % "3.4.0",
  "org.locationtech.geotrellis" %% "geotrellis-s3" % "3.4.0",
  "com.monovore" %% "decline" % "1.3.0"
)

resolvers += "Sonatype OSS Snapshots" at "http://oss.sonatype.org/content/repositories/snapshots/"
