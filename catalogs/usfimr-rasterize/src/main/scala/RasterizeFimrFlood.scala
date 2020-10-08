import geotrellis.vector.io.wkb._
import geotrellis.vector._
import geotrellis.raster._
import geotrellis.raster.rasterize.Rasterizer
import geotrellis.raster.io.geotiff.GeoTiff
import geotrellis.proj4.LatLng

import cats.implicits._
import com.monovore.decline._

import java.nio.file.{Path, Files}

object RasterizeFimrFlood
    extends CommandApp(
      name = "rasterize-flood",
      header = "Rasterizes a USFIMR Flood Event",
      main = {
        val fimrOpt =
          Opts
            .option[Path](
              "fimr-file",
              short = "f",
              help = "The usfimr file to rasterize"
            )

        val jrcOpt =
          Opts
            .option[Path](
              "jrc-file",
              short = "j",
              help = "The jrc dataset to rasterize"
            )

        val jrcOccurrenceThresholdOpt =
          Opts
            .option[Int](
              "jrc-threshold",
              help =
                "The threshold for counting some percent of occurrence as 'permanent'"
            )
            .withDefault(40)

        val outputOpt =
          Opts
            .option[Path]("output", short = "o", help = "The output file")

        (fimrOpt, jrcOpt, jrcOccurrenceThresholdOpt, outputOpt).mapN {
          (fimrFile, jrcFile, jrcOccurrenceThreshold, outputFile) =>
            // relevant fimr data: 1, 2, 3, 15, 16
            println(s"Rasterizing $fimrFile to $outputFile...")

            val geomBytes: Array[Byte] = Files.readAllBytes(fimrFile)
            val invalidGeom = WKB.read(geomBytes)
            // fix for invalid geoms
            val geom = invalidGeom.buffer(0)

            // global surface water raster (the relevant region)
            val jrcRs = RasterSource(jrcFile.toString)
            val jrcCropped = jrcRs.read(geom.extent)
            val jrcRaster = jrcCropped.get
            val jrcThresholdedTile = jrcRaster.tile
              .band(0)
              .map({ occurrence =>
                if (occurrence >= jrcOccurrenceThreshold && occurrence <= 100) 1
                else 0
              })

            val outputRe = RasterExtent(
              jrcRaster.extent,
              jrcRaster.cellSize
            )
            val rasterizedFimrTile =
              Rasterizer.rasterizeWithValue(geom, outputRe, 2)

            val outputTile = rasterizedFimrTile merge jrcThresholdedTile
            val outputTiff = GeoTiff(outputTile, outputRe.extent, LatLng)

            outputTiff.write(outputFile.toString)
        }
      }
    )
