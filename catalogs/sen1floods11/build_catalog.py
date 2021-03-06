import argparse
from datetime import datetime
import json
import os

import click
from pystac import (
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Extensions,
    Extent,
    Item,
    Link,
    LinkType,
    SpatialExtent,
    TemporalExtent,
)
from pystac.extensions.label import LabelClasses, LabelType
import rasterio
from shapely.geometry import GeometryCollection, box, shape

from storage.cloud_storage import S3Storage


def chip_cache_id(country, event_id):
    return "{}_{}".format(country, event_id)


# Remote Rasterio reads for bbox take forever. We can optimize by caching bbox for a given
# chip after its first read as all chips with the same country+event_id have the same bbox
CHIP_BBOX_CACHE = {}

# pystac walks to find source sentinel chips also take forever. So lets just cache refs to them
# here instead since we visit and construct them all before we need to reference them in the
# associate LabelItems
SENTINEL_CHIP_ITEM_CACHE = {
    "S1": {},
    "S2": {},
}


def get_chip_bbox(uri, country, event_id):
    cache_key = chip_cache_id(country, event_id)
    bbox = CHIP_BBOX_CACHE.get(cache_key, None)
    if bbox is None:
        with rasterio.open(uri) as src:
            new_bbox = list(src.bounds)
            CHIP_BBOX_CACHE[cache_key] = new_bbox
            return new_bbox
    else:
        return bbox


def image_date_for_country(sentinel_version, country):
    """ Returns Datetime for country from metadata or None if no result """
    # Misnamed country id in tiffs -- here's a nice hack to get info from metadata...
    if country == "Mekong":
        country = "Cambodia"
    cnn_chips_geojson_file = "./chips_metadata.geojson"
    f = open(cnn_chips_geojson_file)
    chip_metadata = json.load(f)
    f.close()
    metadata = next(
        (
            x
            for x in chip_metadata["features"]
            if x["properties"]["location"] == country
        ),
        None,
    )
    if metadata is not None:
        date_field = "{}_date".format(sentinel_version.lower())
        return datetime.strptime(metadata["properties"][date_field], "%Y/%m/%d")
    else:
        print("WARN: No image date for {} {}".format(sentinel_version, country))
        return None


def collection_update_extents(collection):
    bounds = GeometryCollection(
        [shape(s.geometry) for s in collection.get_all_items()]
    ).bounds
    collection.extent.spatial = SpatialExtent(bounds)

    dates = {
        i.datetime
        for i in collection.get_all_items()
        if isinstance(i.datetime, datetime)
    }
    if len(dates) == 1:
        collection.extent.temporal = TemporalExtent([(next(iter(dates)), None)])
    elif len(dates) > 1:
        collection.extent.temporal = TemporalExtent([(min(dates), max(dates))])
    else:
        print("WARN: {} has no TemporalExtent. Dates: {}".format(collection.id, dates))
        collection.extent.temporal = TemporalExtent(
            [(datetime(1900, 1, 1, 0, 0, 0), None)]
        )


def collection_add_sentinel_chips(collection, uri_list, sentinel_version, debug=False):
    """ Add sentinel images to a collection """
    if debug:
        uri_list = list(uri_list)[:10]
    for uri in uri_list:

        if not uri.endswith(".tif"):
            continue

        item_id = os.path.basename(uri).split(".")[0]
        country, event_id, *_ = item_id.split("_")
        params = {}
        params["id"] = item_id
        params["collection"] = collection
        params["properties"] = {
            "country": country,
            "event_id": event_id,
        }
        params["bbox"] = get_chip_bbox(uri, country, event_id)
        params["geometry"] = box(*params["bbox"]).__geo_interface__

        params["datetime"] = image_date_for_country(sentinel_version, country)

        # Create Tiff Item
        item = Item(**params)
        asset = Asset(
            href=uri, title="GeoTiff", media_type="image/tiff; application=geotiff"
        )
        item.add_asset(key="image", asset=asset)
        SENTINEL_CHIP_ITEM_CACHE[sentinel_version.upper()][
            chip_cache_id(country, event_id)
        ] = item
        collection.add_item(item)
        print("Collection {}: Added STAC Item {}".format(collection.id, item.id))


def label_collection_add_items(
    collection,
    root_catalog,
    uri_list,
    links_func,
    label_description,
    label_type,
    label_classes=None,
    label_tasks=None,
    debug=False,
):
    """ Add uri_list tif uris to collection as LabelItems

    root_catalog is the top level node in the STAC Catalog where the chips labeled by these tifs
    can be found. Required to correctly setup Links to the source chips.

    links_func is a method with the following signature:
        def links_func(root_catalog: Catalog,
                       label_item: LabelItem,
                       country: str,
                       event_id: int): [Link]
    This method should construct a list of links that map the label_item to the STAC objects in
    the root_catalog that label_item is derived from. Assumes for now that the asset referenced
    uses the key "labels"

    The label_ arguments will be passed down to each LabelItem in the collection

    """
    if debug:
        uri_list = list(uri_list)[:10]
    for uri in uri_list:
        if not uri.endswith(".tif"):
            continue

        item_id = os.path.basename(uri).split(".")[0]
        country, event_id, *_ = item_id.split("_")

        params = {}
        params["id"] = item_id
        params["collection"] = collection
        params["datetime"] = image_date_for_country("s1", country)
        params["stac_extensions"] = [Extensions.LABEL]
        params["properties"] = {
            "country": country,
            "event_id": event_id,
        }
        params["bbox"] = get_chip_bbox(uri, country, event_id)
        params["geometry"] = box(*params["bbox"]).__geo_interface__

        label_ext_params = {}
        if isinstance(label_classes, list):
            label_ext_params["label_classes"] = label_classes
        else:
            label_ext_params["label_classes"] = []
        label_ext_params["label_description"] = label_description
        if label_tasks is not None:
            label_ext_params["label_tasks"] = label_tasks
        label_ext_params["label_type"] = label_type

        item = Item(**params)
        item.ext.label.apply(**label_ext_params)
        # Add Asset
        asset = Asset(
            href=uri, title="GeoTiff", media_type="image/tiff; application=geotiff"
        )
        item.add_asset(key="labels", asset=asset)

        item.links = links_func(root_catalog, item, country, event_id)

        collection.add_item(item)
        print("Collection {}: Added STAC Item {}".format(collection.id, item.id))


def source_links_for_labels(items, label_item):
    """ Maps input STAC Items (items) to label_item "labels" via label extension "source" Links """
    return [
        Link(
            "source",
            o,
            link_type=LinkType.RELATIVE,
            media_type="image/tiff; application=geotiff",
            properties={"label:assets": "labels"},
        ).set_owner(label_item)
        for o in items
        if o is not None
    ]


def sentinel1_links_func(root_catalog, label_item, country, event_id):
    """ links_func that looks up country + event id in only S1 """
    return source_links_for_labels(
        [SENTINEL_CHIP_ITEM_CACHE["S1"].get(chip_cache_id(country, event_id), None)],
        label_item,
    )


def sentinel2_links_func(root_catalog, label_item, country, event_id):
    """ links_func that looks up country + event id in only S2 """
    return source_links_for_labels(
        [SENTINEL_CHIP_ITEM_CACHE["S2"].get(chip_cache_id(country, event_id), None)],
        label_item,
    )


def sentinel1_sentinel2_links_func(root_catalog, label_item, country, event_id):
    """ links_func that looks up country + event id in both S1 and S2 """
    cache_id = chip_cache_id(country, event_id)
    return source_links_for_labels(
        [
            SENTINEL_CHIP_ITEM_CACHE["S1"].get(cache_id, None),
            SENTINEL_CHIP_ITEM_CACHE["S2"].get(cache_id, None),
        ],
        label_item,
    )


def main():
    """

# The Data

446 qc'ed chips containing flood events, hand-labeled flood classifications
4385 non-qc'ed chips containing water exported only with sentinel 1 and 2 flood classifications

# The Catalog Outline

** We want to generate a root catalog that is all, or only training, or only validation items **
^^^ Script should support this

- Root Catalog
    - Collection: Sentinel 1 data chips
        - Item: The Item
    - Collection: Sentinel 2 data chips
        - Item: The Item
    - Collection: Sentinel 1 weak labels
        - Item: The Item
    - Collection: Sentinel 2 weak labels
        - Item: The Item
    - Collection: Hand labels
        - Item: The Item
    - Collection: Permanent water labels
        - Item: The Item
    - Collection: Traditional otsu algo labels
        - Item: The Item

## Alternate catalog structure

This structure was considered but rejected in the interest of facilitating collections for each
of the label datasets.

- Root Catalog
    - Collection: Sentinel 1
        - Catalog: Country
            - Catalog: Event ID
                (Note: Catalog will always have the first item. Then it will either have the second
                       item or all the others depending on which dir the first item came from)
                - Item: (dir: S1 + S1_NoQC) Sentinel 1 data chip
                - Item: (dir: S1Flood_NoQC) Labels from "weak" classification algorithm applied to S1
                - Item: (dir: QC_v2) Labels from hand classification (ORed with item below)
                - Item: (dir: S1Flood) Labels from traditional Otsu algorithm
                - Item: (dir: Perm) Labels from perm water dataset (this is a Byte tiff, only 1 or 0
                        for yes or no perm water)
    - Collection: Sentinel 2
        - Catalog: Country
            - Catalog: Event ID
                - Item: (dir: S2 + S2_NoQC) Sentinel 2 data chip
                - Item: (dir: S2Flood) Labels from traditional Otsu algorithm applied to S2
    - Collection: PermJRC
        - Catalog: Lat 10
            - Catalog: Lon 10
                - Item: (dir: PermJRC)
    """
    parser = argparse.ArgumentParser(description="Build STAC Catalog for sen1floods11")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    debug = args.debug

    storage = S3Storage("sen1floods11-data")

    catalog_description = "Bonafilia, D., Tellman, B., Anderson, T., Issenberg, E. 2020. Sen1Floods11: a georeferenced dataset to train and test deep learning flood algorithms for Sentinel-1. The IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR) Workshops, 2020, pp. 210-211. Available Open access at: http://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html"  # noqa: E501
    catalog_title = "A georeferenced dataset to train and test deep learning flood algorithms for Sentinel-1"  # noqa: E501

    catalog = Catalog("sen1floods11", catalog_description, title=catalog_title)
    print("Created Catalog {}".format(catalog.id))

    # Build Sentinel 1 Collection
    sentinel1 = Collection(
        "S1",
        "Sentinel-1 GRD Chips overlapping labeled data. IW mode, GRD product. See https://developers.google.com/earth-engine/sentinel1 for information on preprocessing",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
    )
    collection_add_sentinel_chips(sentinel1, storage.ls("S1/"), "s1", debug=debug)
    collection_add_sentinel_chips(sentinel1, storage.ls("S1_NoQC/"), "s1", debug=debug)
    collection_update_extents(sentinel1)
    catalog.add_child(sentinel1)

    # Build Sentinel 2 Collection
    sentinel2 = Collection(
        "S2",
        "Sentinel-2 MSI L1C chips overlapping labeled data. Contains all spectral bands (1 - 12). Does not contain QA mask.",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
    )
    collection_add_sentinel_chips(sentinel2, storage.ls("S2/"), "s2", debug=debug)
    collection_add_sentinel_chips(sentinel2, storage.ls("S2_NoQC/"), "s2", debug=debug)
    collection_update_extents(sentinel2)
    catalog.add_child(sentinel2)

    # Build S1 Weak Labels Collection
    s1weak_labels = Collection(
        "S1Flood_NoQC",
        "Chips of water/nowater labels derived from standard OTSU thresholding of Sentinel-1 VH band overlapping weakly-labeled data.",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
        stac_extensions=[Extensions.LABEL],
    )
    label_collection_add_items(
        s1weak_labels,
        catalog,
        storage.ls("S1Flood_NoQC/"),
        sentinel1_links_func,
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
        debug=debug,
    )
    collection_update_extents(s1weak_labels)
    catalog.add_child(s1weak_labels)

    # Build S2 Weak Labels Collection
    s2weak_labels = Collection(
        "NoQC",
        "Weakly-labeled chips derived from traditional Sentinel-2 Classification",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
        stac_extensions=[Extensions.LABEL],
    )
    label_collection_add_items(
        s2weak_labels,
        catalog,
        storage.ls("NoQC/"),
        sentinel2_links_func,
        "-1: No Data / Not Valid. 0: Not Water. 1: Water.",  # noqa: E501
        LabelType.RASTER,
        label_classes=[LabelClasses([-1, 0, 1])],
        label_tasks=["classification"],
        debug=debug,
    )
    collection_update_extents(s2weak_labels)
    catalog.add_child(s2weak_labels)

    # Build Hand Labels Collection
    hand_labels = Collection(
        "QC_v2",
        "446 hand labeled chips of surface water from selected flood events",
        extent=Extent(SpatialExtent([None, None, None, None]), None),
        stac_extensions=[Extensions.LABEL],
    )
    label_collection_add_items(
        hand_labels,
        catalog,
        storage.ls("QC_v2/"),
        sentinel1_sentinel2_links_func,
        "Hand labeled chips containing ground truth. -1: No Data / Not Valid. 0: Not Water. 1: Water.",  # noqa: E501
        LabelType.RASTER,
        label_classes=[LabelClasses([-1, 0, 1])],
        label_tasks=["classification"],
        debug=debug,
    )
    collection_update_extents(hand_labels)
    catalog.add_child(hand_labels)

    # Build Permanent Labels collection
    permanent_labels = Collection(
        "Perm",
        "Permanent water chips generated from the 'transition' layer of the JRC (European Commission Joint Research Centre) dataset",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
        stac_extensions=[Extensions.LABEL],
    )
    label_collection_add_items(
        permanent_labels,
        catalog,
        storage.ls("Perm/"),
        lambda *_: [],  # No easy way to map JRC source files to the label chips...
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
        debug=debug,
    )
    collection_update_extents(permanent_labels)
    catalog.add_child(permanent_labels)

    # Build Otsu algorithm Labels collection
    otsu_labels = Collection(
        "S1Flood",
        "Chips of water/nowater derived from standard OTSU thresholding of Sentinel-1 VH band overlapping labeled data",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
        stac_extensions=[Extensions.LABEL],
    )
    label_collection_add_items(
        otsu_labels,
        catalog,
        storage.ls("S1Flood/"),
        sentinel1_links_func,
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
        debug=debug,
    )
    collection_update_extents(otsu_labels)
    catalog.add_child(otsu_labels)

    # Save Complete Catalog
    root_path = "./catalog"
    catalog.normalize_and_save(root_path, catalog_type=CatalogType.SELF_CONTAINED)
    print("Saved STAC Catalog {} to {}...".format(catalog.id, root_path))


if __name__ == "__main__":
    main()
