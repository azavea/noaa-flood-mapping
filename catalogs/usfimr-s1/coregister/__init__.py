import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge as rasterio_merge
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
            nodata=ds_a.nodata,
            tiled=True,
            transform=ds_b.transform,
        ) as dst:
            dst.write(data, indexes=1)


def coregister_rasters(from_uris, to_uri, dest_file, resampling=Resampling.bilinear):
    """ Write raster with extent, proj, res of to_uri to dest_file by merging from_uris.

    Uses the default rasterio.merge.merge operation of 'first' (reverse painting)
    to combine overlapping values in the input rasters.

    from_uris (read), to_uri (read), and dest_file (write) are passed to
    rasterio.open and thus are bound by its semantics.

    """
    with rasterio.open(to_uri) as ds_to:
        from_ds_list = [rasterio.open(uri) for uri in from_uris]
        vrts = [
            WarpedVRT(
                ds,
                crs=ds_to.crs,
                height=ds_to.height,
                width=ds_to.width,
                resampling=resampling,
                transform=ds_to.transform,
            )
            for ds in from_ds_list
        ]
        out_nodata = from_ds_list[0].nodata
        data, out_transform = rasterio_merge(vrts)
        for vrt in vrts:
            vrt.close()
        for ds in from_ds_list:
            ds.close()
        with rasterio.open(
            dest_file,
            "w",
            compress="lzw",
            count=1,
            crs=ds_to.crs,
            driver="GTiff",
            dtype=data.dtype,
            height=data.shape[1],
            width=data.shape[2],
            nodata=out_nodata,
            tiled=True,
            transform=out_transform,
        ) as dst:
            dst.write(data[0], indexes=1)
