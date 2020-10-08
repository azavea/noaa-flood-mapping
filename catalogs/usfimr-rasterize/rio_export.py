#!/usr/bin/env python3
import argparse

import pystac

import numpy as np
from PIL import Image
import rasterio as rio
from stac_utils.s3_io import register_s3_io


def s3tovsi(s3path):
    return "/vsis3/{}".format(s3path.split("//")[-1])


def main():
    register_s3_io()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mldata-catalog",
        default="s3://usfimr-s1-mldata/usfimr-s1-mldata-catalog_seed42/catalog.json",
        type=str,
    )
    args = parser.parse_args()

    catalog = pystac.Catalog.from_file(args.mldata_catalog)

    validation = catalog.get_child("validation")
    items = validation.get_items()

    for item in items:
        s3path = item.assets["HAND"].href
        with rio.open(s3tovsi(s3path)) as hand_tif:
            hand_height = hand_tif.height
            hand_width = hand_tif.width
            hand_bounds = hand_tif.bounds

        with rio.open(
            "/vsis3/noaafloodmap-data-us-east-1/nzimmerman/mississippi-s2-cloudless/mississippi-s2-usfimr_correlate-v2.vrt"
        ) as s2cloudless:
            window = rio.windows.from_bounds(
                hand_bounds.left,
                hand_bounds.bottom,
                hand_bounds.right,
                hand_bounds.top,
                transform=s2cloudless.transform,
            )
            # rgb = np.rint(s2cloudless.read([4, 3, 2], window=window) * 850)
            r = np.rint(s2cloudless.read(4, window=window) * 850).astype(np.uint8)
            g = np.rint(s2cloudless.read(3, window=window) * 850).astype(np.uint8)
            b = np.rint(s2cloudless.read(2, window=window) * 850).astype(np.uint8)
            shp = r.shape
            print("origin bounds:", hand_bounds)
            print("origin width/height:", hand_width, hand_height)
            print("expected shape:", r.shape)

        if shp[0] > 500 and shp[1] > 500:
            with rio.open(
                "/tmp/" + item.id[:-4] + "preview.tif",
                "w",
                driver="GTiff",
                dtype=np.uint8,
                count=3,
                height=shp[0],
                width=shp[1],
            ) as dst:
                dst.write_band(1, r)
                dst.write_band(2, g)
                dst.write_band(3, b)


if __name__ == "__main__":
    main()
