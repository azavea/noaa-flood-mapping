import geotrellis.vector.io.wkb._
import geotrellis.vector._
import geotrellis.raster._
import geotrellis.raster.rasterize.Rasterizer
import geotrellis.raster.io.geotiff.GeoTiff
import geotrellis.proj4.LatLng

import _root_.io.circe._
import _root_.io.circe.parser._
import cats.implicits._
import com.monovore.decline._

import java.nio.file.{Path, Files}
import java.nio.charset.StandardCharsets
import java.io.File

object RewriteCatalogEntries
    extends CommandApp(
      name = "make-labels",
      header = "Chip out labels for training",
      main = {
        val catalogOpt =
          Opts
            .option[Path](
              "catalog-dir",
              short = "c",
              help = "Directory with usfimr mldata catalog"
            )

        val rasterizedLabelsOpt =
          Opts
            .option[Path](
              "Directory of chipped, rasterized jrc/usfimr data",
              short = "j",
              help = "The chipped jrc/usfimr dataset"
            )

        (catalogOpt, rasterizedLabelsOpt).mapN {
          (catalogDir, rasterizedLabelsDir) =>
            val train = new File(s"$catalogDir/train")
            val test = new File(s"$catalogDir/test")
            val validation = new File(s"$catalogDir/validation")

            // feed in json for train/test/val entry
            def rewriteEntry(catalogEntry: File): Unit = {
              val bytes = Files.readAllBytes(catalogEntry.toPath)
              val rawJson = new String(
                bytes,
                StandardCharsets.UTF_8
              )
              val json: Json = parse(rawJson).getOrElse(Json.Null)

              val chipName =
                catalogEntry.toString.split("/").last.split('.').head

              val recordCursor = json.hcursor
              val recordHrefRewrite = recordCursor
                .downField("links")
                .downArray
                .downField("href")
                .withFocus(
                  _.mapString(_ =>
                    s"../../usfimr_sar_labels_tif/$chipName.json"
                  )
                )
              val recordOutputJson = recordHrefRewrite.top.get

              Files.write(
                catalogEntry.toPath,
                recordOutputJson.toString.getBytes
              )
            }

            def writeLabelEntry(catalogEntry: File): Unit = {
              val chipName =
                catalogEntry.toString.split("/").last.split('.').head

              val rawJson =
                s"""{"type":"Feature","stac_version":"0.9.0","id":"${chipName}_label","properties":{"datetime":"2017-01-01T01:01:01Z"},"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]},"bbox":[0,0,1,1],"links":[{"rel":"collection","href":"../collection.json","type":"application/json"},{"rel":"root","href":"../../catalog.json","type":"application/json"},{"rel":"parent","href":"../collection.json","type":"application/json"}],"assets":{"labels":{"href":"s3://jrc-fimr-rasterized-labels/${chipName}.tif","type":"image/tiff; application=geotiff","description":"tif label representation"}},"collection":"test"}"""
              val parsedJson = parse(rawJson).getOrElse(Json.Null)

              Files.write(
                new File(
                  s"$catalogDir/usfimr_sar_labels_tif/${chipName}.json"
                ).toPath,
                parsedJson.toString.getBytes
              )
            }

            // train/test/val section
            def rewriteMultipleEntries(catalogSection: File): Unit = {
              val entries = catalogSection.listFiles.filter(_.isDirectory)
              entries.flatMap(_.listFiles).foreach(rewriteEntry)
              entries.flatMap(_.listFiles).foreach(writeLabelEntry)
            }

            rewriteMultipleEntries(train)
            rewriteMultipleEntries(test)
            rewriteMultipleEntries(validation)

        }
      }
    )
