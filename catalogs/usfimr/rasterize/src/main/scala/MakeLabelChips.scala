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

object MakeLabelChips
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
              "Directory of rasterized jrc/usfimr data",
              short = "j",
              help = "The jrc/usfimr dataset to chip"
            )

        val outputOpt =
          Opts
            .option[Path](
              "output-dir",
              short = "o",
              help = "The output directory"
            )

        (catalogOpt, rasterizedLabelsOpt, outputOpt).mapN {
          (catalogDir, rasterizedLabelsDir, outputDir) =>
            val labels = Map(
              1 -> s"$rasterizedLabelsDir/01.tif",
              2 -> s"$rasterizedLabelsDir/02.tif",
              3 -> s"$rasterizedLabelsDir/03.tif",
              15 -> s"$rasterizedLabelsDir/15.tif",
              16 -> s"$rasterizedLabelsDir/16.tif"
            )

            val train = new File(s"$catalogDir/train")
            val test = new File(s"$catalogDir/test")
            val validation = new File(s"$catalogDir/validation")

            // feed in json for train/test/val entry
            def writeChip(catalogEntry: File): Unit = {
              val bytes = Files.readAllBytes(catalogEntry.toPath)
              val rawJson = new String(
                bytes,
                StandardCharsets.UTF_8
              )
              val json: Json = parse(rawJson).getOrElse(Json.Null)
              val cursor = json.hcursor

              // Extent
              //val bbox = cursor.downField("bbox").as[List[Double]].right.get
              //val extent = Extent(bbox(1), bbox(0), bbox(3), bbox(2))
              val maskPath = cursor
                .downField("assets")
                .downField("MASK")
                .downField("href")
                .as[String]
                .right
                .get
              val maskRs = RasterSource(maskPath)

              // Labels
              val labelNumber = cursor
                .downField("links")
                .downArray
                .downField("href")
                .as[String]
                .right
                .get
                .split("/")
                .takeRight(2)
                .head
                .toInt
              val labelPath = labels(labelNumber)

              val labelRs = RasterSource(labelPath)
              labelRs.reprojectToGrid(
                maskRs.crs,
                GridExtent(maskRs.extent, maskRs.cols, maskRs.rows)
              )

              val chipName =
                catalogEntry.toString.split("/").last.split('.').head
              println(chipName)

              val raster = labelRs.read(maskRs.extent).get

              val outputTiff = GeoTiff(raster.tile, raster.extent, maskRs.crs)
              outputTiff.write(s"$outputDir/$chipName.tif")
            }

            // train/test/val section
            def writeMultipleChips(catalogSection: File): Unit = {
              val chips = catalogSection.listFiles.filter(_.isDirectory)
              chips.flatMap(_.listFiles).foreach(writeChip)
            }

            writeMultipleChips(train)
            writeMultipleChips(test)
            writeMultipleChips(validation)

        }
      }
    )
