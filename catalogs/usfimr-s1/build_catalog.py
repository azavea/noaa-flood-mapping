#!/usr/bin/env python3

from datetime import datetime
import json
import argparse
from itertools import groupby

from pystac import (
    Asset,
    CatalogType,
    Catalog,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
)
import boto3
import urllib3
import rasterio as rio
from shapely.geometry import Polygon, mapping


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--imagery-root-s3", required=True)
    args = parser.parse_args()

    parsed_s3_path = urllib3.util.parse_url(args.imagery_root_s3)
    bucket = parsed_s3_path.netloc
    try:
        prefix = parsed_s3_path.path[1:]
    except TypeError:
        prefix = ''

    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket)
    filtered_objects = bucket.objects.filter(Prefix=prefix)

    catalog_description = (
        "Sentinel-1 imagery corresponding to flood events catalogued within GLOFIMR"
    )
    catalog_title = "GLOFIMR SAR Imagery"

    catalog = Catalog("glofimr-sar", catalog_description, title=catalog_title)

    # We know the IDs used here (they are derived from the incrementing ID from the GLOFIMR shapefile)
    # TODO: make the IDs/these keys something more descriptive
    flood_data = {"1": [], "2": [], "3": [], "15": [], "16": []}
    for obj in filtered_objects:
        flood_data[obj.key.split("/")[0]].append(obj.Object())

    subcollections = []
    for flood_id, objects in flood_data.items():
        aggregate_bounds = None

        # these objects are ultimately assets that we'd like to group by tile ID, we do that here
        imagery_objects = [obj for obj in objects if obj.content_type == "image/tiff"]
        imagery_grouped = groupby(
            imagery_objects, key=lambda obj: obj.key.split("/")[-2]
        )

        sentinelhub_request = json.loads(
            [obj for obj in objects if obj.key.endswith("json")][0]
            .get()["Body"]
            .read()
            .decode("utf-8")
        )
        time_range = sentinelhub_request["processRequest"]["input"]["data"][0][
            "dataFilter"
        ]["timeRange"]
        start_time = datetime.fromisoformat(time_range["from"][:-1])
        end_time = datetime.fromisoformat(time_range["to"][:-1])
        temporal_extent = TemporalExtent(intervals=[[start_time, end_time]])

        stac_items = []
        for group_id, image_group in imagery_grouped:

            # assemble assets so that they might be grouped (without duplication) in items
            assets = []
            for image in image_group:
                s3_path = "s3://" + image.bucket_name + "/" + image.key

                # The extents should be the same, so whichever one is checked last should be fine
                with rio.open(s3_path) as img:
                    bounds = img.bounds
                assets.append(Asset(s3_path))

            if aggregate_bounds is None:
                aggregate_bounds = bounds
            else:
                aggregate_bounds = rio.coords.BoundingBox(
                    min(bounds.left, aggregate_bounds.left),
                    min(bounds.bottom, aggregate_bounds.bottom),
                    max(bounds.right, aggregate_bounds.right),
                    max(bounds.top, aggregate_bounds.top),
                )

            item_spatial_extent = SpatialExtent(
                [[bounds.bottom, bounds.left, bounds.top, bounds.right]]
            )
            item_extent = Extent(item_spatial_extent, temporal_extent)
            image_item = Item(
                group_id,
                geometry=mapping(
                    Polygon(
                        [
                            [bounds.left, bounds.bottom],
                            [bounds.right, bounds.bottom],
                            [bounds.right, bounds.top],
                            [bounds.left, bounds.top],
                            [bounds.left, bounds.bottom],
                        ]
                    )
                ),
                bbox=[bounds.bottom, bounds.left, bounds.top, bounds.right],
                datetime=start_time,
                properties={},
            )
            for asset in assets:
                image_item.add_asset(asset.href.split("/")[-1].split(".")[0], asset)

            stac_items.append(image_item)
        aggregate_spatial_extent = SpatialExtent(
            [
                [
                    aggregate_bounds.bottom,
                    aggregate_bounds.left,
                    aggregate_bounds.top,
                    aggregate_bounds.right,
                ]
            ]
        )
        aggregate_extent = Extent(aggregate_spatial_extent, temporal_extent)
        collection = Collection(
            flood_id,
            "Imagery coextensive with GLOFIMR flood {}".format(flood_id),
            extent=aggregate_extent,
        )
        for stac_item in stac_items:
            collection.add_item(stac_item)

        catalog.add_child(collection)

    # Save Complete Catalog
    root_path = "./catalog"
    catalog.normalize_and_save(root_path, catalog_type=CatalogType.SELF_CONTAINED)
    print("Saved STAC Catalog {} to {}...".format(catalog.id, root_path))
