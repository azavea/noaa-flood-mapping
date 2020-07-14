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


def image_date_for_country(sentinel_version, country):
    """ Returns Datetime for country from metadata or None if no result """
    cnn_chips_geojson_file = "./chips_metadata.geojson"
    f = open(cnn_chips_geojson_file)
    chip_metadata = json.load(f)
    f.close()
    metadata = next(
        (x for x in chip_metadata["features"] if x["id"].startswith(country)), None,
    )
    if metadata is not None:
        date_field = "{}_date".format(sentinel_version.lower())
        return datetime.strptime(metadata["properties"][date_field], "%Y-%m-%d")
    else:
        return None


def collection_update_extents(collection):
    bounds = GeometryCollection(
        [shape(s.geometry) for s in collection.get_all_items()]
    ).bounds
    collection.extent.spatial = SpatialExtent(bounds)

    t_min = min([i.datetime for i in collection.get_all_items()])
    t_max = max([i.datetime for i in collection.get_all_items()])
    if t_min == t_max:
        collection.extent.temporal = TemporalExtent([(t_min, None)])
    else:
        collection.extent.temporal = TemporalExtent([(t_min, t_max)])


def collection_add_sentinel_chips(collection, uri_list, sentinel_version):
    """ Add sentinel images to a collection """
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

        with rasterio.open(uri) as src:
            params["bbox"] = list(src.bounds)
            params["geometry"] = box(*params["bbox"]).__geo_interface__

        params["datetime"] = image_date_for_country(sentinel_version, country)

        # Create Tiff Item
        item = Item(**params)
        asset = Asset(
            href=uri, title="GeoTiff", media_type="image/tiff; application=geotiff"
        )
        item.add_asset(key="image", asset=asset)
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
        with rasterio.open(uri) as src:
            params["bbox"] = list(src.bounds)
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
        [root_catalog.get_item("{}_{}_S1".format(country, event_id), recursive=True)],
        label_item,
    )


def sentinel2_links_func(root_catalog, label_item, country, event_id):
    """ links_func that looks up country + event id in only S2 """
    return source_links_for_labels(
        [root_catalog.get_item("{}_{}_S2".format(country, event_id), recursive=True)],
        label_item,
    )


def sentinel1_sentinel2_links_func(root_catalog, label_item, country, event_id):
    """ links_func that looks up country + event id in both S1 and S2 """
    return source_links_for_labels(
        [
            root_catalog.get_item("{}_{}_S1".format(country, event_id), recursive=True),
            root_catalog.get_item("{}_{}_S2".format(country, event_id), recursive=True),
        ],
        label_item,
    )


@click.command(help="Build STAC Catalog for sen1floods11")
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
    collection_add_sentinel_chips(sentinel1, list(storage.ls("S1/"))[:2], "s1")
    collection_add_sentinel_chips(sentinel1, list(storage.ls("S1_NoQC/"))[:2], "s1")
    collection_update_extents(sentinel1)
    catalog.add_child(sentinel1)

    # Build Sentinel 2 Collection
    sentinel2 = Collection(
        "S2",
        "Sentinel-2 MSI L1C chips overlapping labeled data. Contains all spectral bands (1 - 12). Does not contain QA mask.",  # noqa: E501
        extent=Extent(SpatialExtent([None, None, None, None]), None),
    )
    collection_add_sentinel_chips(sentinel2, list(storage.ls("S2/"))[:2], "s2")
    collection_add_sentinel_chips(sentinel2, list(storage.ls("S2_NoQC/"))[:2], "s2")
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
        list(storage.ls("S1Flood_NoQC/"))[:2],
        sentinel1_links_func,
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
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
        list(storage.ls("NoQC/"))[:2],
        sentinel2_links_func,
        "-1: No Data / Not Valid. 0: Not Water. 1: Water.",  # noqa: E501
        LabelType.RASTER,
        label_classes=[LabelClasses([-1, 0, 1])],
        label_tasks=["classification"],
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
        list(storage.ls("QC_v2/"))[:2],
        sentinel1_sentinel2_links_func,
        "Hand labeled chips containing ground truth. -1: No Data / Not Valid. 0: Not Water. 1: Water.",  # noqa: E501
        LabelType.RASTER,
        label_classes=[LabelClasses([-1, 0, 1])],
        label_tasks=["classification"],
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
        list(storage.ls("Perm/"))[:2],
        lambda *_: [],  # No easy way to map JRC source files to the label chips...
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
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
        list(storage.ls("S1Flood/"))[:2],
        sentinel1_links_func,
        "0: Not Water. 1: Water.",
        LabelType.RASTER,
        label_classes=[LabelClasses([0, 1])],
        label_tasks=["classification"],
    )
    collection_update_extents(otsu_labels)
    catalog.add_child(otsu_labels)

    # Save Complete Catalog
    root_path = "./catalog"
    catalog.normalize_and_save(root_path, catalog_type=CatalogType.SELF_CONTAINED)
    print("Saved STAC Catalog {} to {}...".format(catalog.id, root_path))


if __name__ == "__main__":
    main()
