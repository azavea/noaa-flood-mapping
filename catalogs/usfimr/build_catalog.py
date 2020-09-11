#!/usr/bin/env python3

import os
from copy import deepcopy
import json
import argparse
from datetime import date, time, datetime

import fiona
from shapely.geometry import shape, mapping
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapefile", required=True)
    args = parser.parse_args()

    shp_path = args.shapefile

    print("Targeting shapefile at path {}".format(shp_path))

    items = []
    running_spatial_extent = (0, 0, 0, 0)
    root_path = "./data/catalog"
    running_start_dt = None
    running_end_dt = None
    with fiona.open(shp_path) as fc:
        for feature in fc:
            geom = feature["geometry"]
            props = feature["properties"]

            if props["Start_Time"] is not None:
                start_time = time.fromisoformat(props["Start_Time"])
            else:
                start_time = datetime.min.time()

            if props["End_Time"] is not None:
                end_time = time.fromisoformat(props["End_Time"])
            else:
                end_time = datetime.min.time()

            start_dt = datetime.combine(
                date.fromisoformat(props["Flood_Date"]), start_time
            )
            end_dt = datetime.combine(date.fromisoformat(props["Flood_Date"]), end_time)
            shapely_geom = shape(geom)
            bbox = shapely_geom.bounds
            bbox_list = [bbox[0], bbox[1], bbox[2], bbox[3]]

            running_spatial_extent = (
                min(running_spatial_extent[0], bbox[0]),
                max(running_spatial_extent[1], bbox[1]),
                min(running_spatial_extent[2], bbox[2]),
                max(running_spatial_extent[3], bbox[3]),
            )

            if running_start_dt:
                if running_start_dt > start_dt:
                    running_start_dt = start_dt
            else:
                running_start_dt = start_dt

            if running_end_dt:
                if running_end_dt < end_dt:
                    running_end_dt = end_dt
            else:
                running_end_dt = end_dt

            fid = feature["id"]

            binary_asset = Asset(
                href="{}-usfimr.wkb".format(fid),
                description="well known binary representation",
                media_type="application/wkb",
            )
            text_asset = Asset(
                href="{}-usfimr.wkt".format(fid),
                description="well known text representation",
                media_type="application/wkt",
            )
            json_asset = Asset(
                href="{}-usfimr.geojson".format(fid),
                description="geojson representation",
                media_type="application/geo+json",
            )
            serializable_convex_hull = mapping(shapely_geom.convex_hull)
            item = Item(
                fid, serializable_convex_hull, bbox_list, start_dt, deepcopy(props)
            )
            text_asset.set_owner(item)
            item.add_asset(key="wkt", asset=text_asset)
            binary_asset.set_owner(item)
            item.add_asset(key="wkb", asset=binary_asset)
            json_asset.set_owner(item)
            item.add_asset(key="geojson", asset=json_asset)
            items.append(item)

            os.makedirs("{}/{}".format(root_path, fid), exist_ok=True)

            with open(
                "{}/{}/{}-usfimr.wkt".format(root_path, fid, fid), "w"
            ) as wkt_file:
                wkt_file.write(shapely_geom.wkt)

            with open(
                "{}/{}/{}-usfimr.wkb".format(root_path, fid, fid), "wb"
            ) as wkb_file:
                wkb_file.write(shapely_geom.wkb)

            with open(
                "{}/{}/{}-usfimr.geojson".format(root_path, fid, fid), "w"
            ) as geojson_file:
                geojson_file.write(json.dumps(geom))

    overall_extent = Extent(
        SpatialExtent(running_spatial_extent),
        TemporalExtent([[running_start_dt, running_end_dt]]),
    )

    root_collection = Collection(
        id="USFIMR",
        description="GloFIMR is an extension of the USFIMR project that commenced in August 2016 with funding from NOAA. The project’s main goal is to provide high-resolution inundation extent maps of flood events to be used by scientists and practitioners for model calibration and flood susceptibility evaluation. The maps are based on analysis of Remote Sensing imagery from a number of Satellite sensors (e.g. Landsat, Sentinel-1, Sentinel-2). The maps are accessible via the online map repository below. The repository is under development and new maps are added upon request.",
        title="U.S. Flood Inundation Mapping Repository",
        extent=overall_extent,
    )

    for item in items:
        root_collection.add_item(item)

    # Save Complete Catalog
    root_collection.normalize_and_save(
        root_path, catalog_type=CatalogType.SELF_CONTAINED
    )
    print("Saved STAC Catalog {} to {}...".format(root_collection.id, root_path))
