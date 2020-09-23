#!/usr/bin/env python3

import argparse
from datetime import datetime, time, date
from urllib.parse import urlparse

import boto3
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
)
from shapely.geometry import Polygon, mapping


if __name__ == "__main__":
    """Constructs STAC Catalog for surface water observed on a monthly basis around the Mississippi river

    Will include all images with the extension `tif`
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jrc-monthly-root-s3",
        required=True,
        help="Bucket+key path to a directory containing JRC surface water labels",
    )
    args = parser.parse_args()

    parsed_s3_path = urlparse(args.jrc_monthly_root_s3)
    bucket = parsed_s3_path.netloc

    collection_description = (
        "JRC Global Monthly Water around the Mississippi river system",
    )
    collection_title = "Global Monthly Water: Mississippi river system"

    spatial_extent = SpatialExtent(
        [
            [
                29.038948834106055,
                -92.72807246278022,
                42.55475543734189,
                -88.02592402528022,
            ]
        ]
    )

    # The JRC water dataset examines imagery from march, 1984 to december, 2019
    start_dt = datetime.combine(date(1984, 3, 1), time.min)
    end_dt = datetime.combine(date(2019, 12, 1), time.min)
    collection_temporal_extent = TemporalExtent(intervals=[[start_dt, end_dt]])

    collection = Collection(
        id="jrc-monthly-water-mississippi-river",
        description=collection_description,
        extent=Extent(spatial_extent, collection_temporal_extent),
        title=collection_title,
    )

    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket)
    prefix = parsed_s3_path.path.lstrip("/")
    filtered_objects = bucket.objects.filter(Prefix=prefix)

    for obj_summary in filtered_objects:
        extension = obj_summary.key.split(".")[-1]
        if extension == "tif":
            item_id = obj_summary.key.split("/")[-1].split(".")[0]

            year = int(item_id.split("_")[-2])
            month = int(item_id.split("_")[-1])
            item_time = datetime.combine(date(year, month, 1), time.min)

            item = Item(
                item_id,
                geometry=mapping(
                    Polygon(
                        [
                            [-92.72807246278022, 29.038948834106055],
                            [-88.02592402528022, 29.038948834106055],
                            [-88.02592402528022, 42.55475543734189],
                            [-92.72807246278022, 42.55475543734189],
                            [-92.72807246278022, 29.038948834106055],
                        ]
                    )
                ),
                bbox=[
                    29.038948834106055,
                    -92.72807246278022,
                    42.55475543734189,
                    -88.02592402528022,
                ],
                datetime=item_time,
                properties={},
            )
            asset = Asset("s3://{}/{}".format(obj_summary.bucket_name, obj_summary.key))
            item.add_asset("labels", asset)
            collection.add_item(item)

    # Save Complete Catalog
    root_path = "./data/catalog"
    collection.normalize_and_save(root_path, catalog_type=CatalogType.SELF_CONTAINED)
    print("Saved STAC Catalog {} to {}...".format(collection.id, root_path))