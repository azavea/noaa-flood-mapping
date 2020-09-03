#!/usr/bin/env python3

from datetime import date, datetime
from zipfile import ZipFile
import argparse

import requests
import fiona
from shapely.geometry import shape
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
)

hand_download_template = "https://cfim.ornl.gov/data/HAND/20200601/{huc6code}.zip"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-uri", required=True)
    args = parser.parse_args()

    version_dt = datetime.combine(date.fromisoformat("2020-06-01"), datetime.min.time())

    # initial state
    items = []
    running_extent = (0, 0, 0, 0)

    # First, we need the shapefil with all boundaries/extents
    r = requests.get("https://cfim.ornl.gov/data/HAND/handmeta/hand_021.zip")
    with open("/tmp/hand_021.zip", "wb") as shp_zip:
        shp_zip.write(r.content)
    with ZipFile("/tmp/hand_021.zip", "r") as shp_zip:
        shp_zip.extractall("/tmp/hand_021")

    with fiona.open("/tmp/hand_021/hand_021.shp") as fc:
        for feature in fc:
            fid = feature["properties"]["HUC6"]
            geom = feature["geometry"]
            bbox = shape(geom).bounds
            running_extent = (
                min(running_extent[0], bbox[0]),
                max(running_extent[1], bbox[1]),
                min(running_extent[2], bbox[2]),
                max(running_extent[3], bbox[3]),
            )
            bbox_list = [bbox[0], bbox[1], bbox[2], bbox[3]]

            huc_item = Item(fid, geom, bbox_list, version_dt, {})

            hand_asset = Asset(
                href="{}/{}/{}hand.tif".format(args.root_uri, fid, fid),
                description="HAND raster, buffer removed, final result",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="hand", asset=hand_asset)

            wbd_asset = Asset(
                href="{}/{}/{}-wbd.geojson".format(args.root_uri, fid, fid),
                description="HUC unit boundary, extracted from USGS wbd",
                media_type="application/geo+json",
            )
            huc_item.add_asset(key="wbd", asset=wbd_asset)

            flows_asset = Asset(
                href="{}/{}/{}-flows.geojson".format(args.root_uri, fid, fid),
                description="Flowline geometry, extracted from NHDPlus V21",
                media_type="application/geo+json",
            )
            huc_item.add_asset(key="flows", asset=flows_asset)

            inlets_asset = Asset(
                href="{}/{}/{}-inlets.geojson".format(args.root_uri, fid, fid),
                description="Inlets point geometries in the HUC unit",
                media_type="application/geo+json",
            )
            huc_item.add_asset(key="inlets", asset=inlets_asset)

            weights_asset = Asset(
                href="{}/{}/{}-weights.tif".format(args.root_uri, fid, fid),
                description="Weight grid of the rasterized inlet points",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="weights", asset=weights_asset)

            dem_asset = Asset(
                href="{}/{}/{}.tif".format(args.root_uri, fid, fid),
                description="Clipped HUC unit DEM from USGS 3DEP 10m elevation dataset (buffered)",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="dem", asset=dem_asset)

            fel_asset = Asset(
                href="{}/{}/{}fel.tif".format(args.root_uri, fid, fid),
                description="Pit-removed DEM; output of TauDEM pitremove",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="fel", asset=fel_asset)

            flowdir_asset = Asset(
                href="{}/{}/{}p.tif".format(args.root_uri, fid, fid),
                description="D8 flow direction raster; output of TauDEM d8flowdir",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="p", asset=flowdir_asset)

            slope_asset = Asset(
                href="{}/{}/{}sd8.tif".format(args.root_uri, fid, fid),
                description="D8 slope raster; output of TauDEM d8flowdir",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="sd8", asset=slope_asset)

            ang_asset = Asset(
                href="{}/{}/{}ang.tif".format(args.root_uri, fid, fid),
                description="Dinfinity flow direction raster; output of TauDEM dinfflowdir",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="ang", asset=ang_asset)

            slp_asset = Asset(
                href="{}/{}/{}slp.tif".format(args.root_uri, fid, fid),
                description="Dinfinity slope raster; output of TauDEM dinfflowdir",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="slp", asset=slp_asset)

            ssa_asset = Asset(
                href="{}/{}/{}ssa.tif".format(args.root_uri, fid, fid),
                description="Contributing area raster; output of TauDEM aread8",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="ssa", asset=ssa_asset)

            src_asset = Asset(
                href="{}/{}/{}src.tif".format(args.root_uri, fid, fid),
                description="Stream grid; output of TauDEM threshold (threshold=1)",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="src", asset=src_asset)

            dd_asset = Asset(
                href="{}/{}/{}dd.tif".format(args.root_uri, fid, fid),
                description="Buffered HAND raster; output of TauDEM dinfdistdown",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="dd", asset=dd_asset)

            comid_asset = Asset(
                href="{}/{}/{}_comid.txt".format(args.root_uri, fid, fid),
                description="Catchment ID list for a HUC6 unit (COMID, slope, flowline length, and areasqkm)",
                media_type="text/plain",
            )
            huc_item.add_asset(key="comid", asset=comid_asset)

            catchmask_asset = Asset(
                href="{}/{}/{}catchmask.tif".format(args.root_uri, fid, fid),
                description="Rasterized catchments with cell value to be the COMID of the corresponding river reach (buffered)",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="catchmask", asset=catchmask_asset)

            catchhuc_asset = Asset(
                href="{}/{}/{}catchhuc.tif".format(args.root_uri, fid, fid),
                description="Rasterized catchments in HAND extent",
                media_type="image/tiff; application=geotiff",
            )
            huc_item.add_asset(key="catchhuc", asset=catchhuc_asset)

            hydrogeo_asset = Asset(
                href="{}/{}/hydrogeo-fulltable-{}.csv".format(args.root_uri, fid, fid),
                description="Hydraulic property table with the following fields: CatchId, Stage, Number of Cells, SurfaceArea (m2), BedArea (m2), Volume (m3), SLOPE, LENGTHKM, AREASQKM, Roughness, TopWidth (m), WettedPerimeter (m), WetArea (m2), HydraulicRadius (m), Discharge (m3s-1)",
                media_type="text/csv",
            )
            huc_item.add_asset(key="hydrogeo", asset=hydrogeo_asset)

            items.append(huc_item)

    overall_extent = Extent(
        SpatialExtent(
            [running_extent[0], running_extent[1], running_extent[2], running_extent[3]]
        ),
        TemporalExtent([[version_dt, None]]),
    )

    # Root Collection
    root_collection = Collection(
        id="hand_021",
        description="The continental flood inundation mapping (CFIM) framework is a high-performance computing (HPC)-based computational framework for the Height Above Nearest Drainage (HAND)-based inundation mapping methodology. Using the 10m Digital Elevation Model (DEM) data produced by U.S. Geological Survey (USGS) 3DEP (the 3-D Elevation Program) and the NHDPlus hydrography dataset produced by USGS and the U.S. Environmental Protection Agency (EPA), a hydrological terrain raster called HAND is computed for HUC6 units in the conterminous U.S. (CONUS). The value of each raster cell in HAND is an approximation of the relative elevation between the cell and its nearest water stream. Derived from HAND, a hydraulic property table is established to calculate river geometry properties for each of the 2.7 million river reaches covered by NHDPlus (5.5 million kilometers in total length). This table is a lookup table for water depth given an input stream flow value. Such lookup is available between water depth 0m and 25m at 1-foot interval. The flood inundation map can then be computed by using HAND and this lookup table based on the near real-time water forecast from the National Water Model (NWM) at the National Oceanic and Atmospheric Administration (NOAA).",
        title="HAND and the Hydraulic Property Table version 0.2.1",
        extent=overall_extent,
        license="CC-BY-4.0",
    )
    for item in items:
        root_collection.add_item(item)

    # Save Complete Catalog
    root_path = "./catalog"
    root_collection.normalize_and_save(
        root_path, catalog_type=CatalogType.SELF_CONTAINED
    )
    print("Saved STAC Catalog {} to {}...".format(root_collection.id, root_path))
