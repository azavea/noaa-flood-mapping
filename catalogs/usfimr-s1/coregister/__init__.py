import affine
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT


def coregister_raster(a_uri, b_uri, dest_file, resampling=Resampling.bilinear):
    """ Coregister raster a to the extent, resolution and projection of raster b.

    Write to dest_file.

    a_uri (read), b_uri (read), and dest_file (write) are passed to
    rasterio.open and thus are bound by its semantics.

    """
    with rasterio.open(a_uri) as ds_a, rasterio.open(b_uri) as ds_b:
        vrt = WarpedVRT(
            ds_a,
            crs=ds_b.crs,
            height=ds_b.height,
            width=ds_b.width,
            resampling=resampling,
            transform=ds_b.transform,
        )
        data = vrt.read(1)
        with rasterio.open(
            dest_file,
            "w",
            compress="lzw",
            count=1,
            crs=ds_b.crs,
            driver="GTiff",
            dtype=data.dtype,
            height=ds_b.height,
            width=ds_b.width,
            tiled=True,
            transform=ds_b.transform,
        ) as dst:
            dst.write(data, indexes=1)
