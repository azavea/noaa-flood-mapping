import argparse

import pystac

from stac_utils.s3_io import register_s3_io


def add_set(flood_ids, set_type, mldata_catalog, sar_catalog, usfimr_collection):
    """ Add test, training or validation collections containing flood_ids to mldata_catalog.

    TODO: Properly set the created collection extents. For now they're just set to
          usfimr_collection.extent since we don't use the extent downstream.

    """
    set_types = set(["test", "training", "validation"])
    if set_type not in set_types:
        raise ValueError("set_type must be one of {}".format(set_types))

    imagery_collection_id = "{}_imagery".format(set_type)
    labels_collection_id = "{}_labels".format(set_type)
    if set_type == "test":
        imagery_collection_id += "_0"
        labels_collection_id += "_0"
    imagery_collection = pystac.Collection(
        imagery_collection_id, imagery_collection_id, usfimr_collection.extent
    )
    labels_collection = pystac.Collection(
        labels_collection_id, labels_collection_id, usfimr_collection.extent
    )

    for flood_id in flood_ids:
        usfimr_item = usfimr_collection.get_item(flood_id)
        usfimr_geojson_asset = usfimr_item.assets["geojson"]
        usfimr_geojson_asset.set_owner(usfimr_item)
        usfimr_item_clone = usfimr_item.clone()
        # Reduce item assets to just the geojson as labels
        usfimr_item_clone.assets = {"labels": usfimr_item.assets["geojson"]}
        labels_collection.add_item(usfimr_item_clone)

        for sar_item in sar_catalog.get_child(flood_id).get_items():
            sar_item_clone = sar_item.clone()
            sar_item_clone.links.append(
                pystac.Link(
                    "labels",
                    target=usfimr_item_clone,
                    media_type="application/geo+json",
                    link_type=pystac.LinkType.RELATIVE,
                ).set_owner(sar_item_clone)
            )
            imagery_collection.add_item(sar_item_clone)

    mldata_catalog.add_child(imagery_collection)
    mldata_catalog.add_child(labels_collection)


def main():
    register_s3_io()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--usfimr-collection", default="s3://usfimr-data/collection.json"
    )
    parser.add_argument("--sar-catalog", required=True, type=str)
    args = parser.parse_args()

    usfimr_collection = pystac.Collection.from_file(args.usfimr_collection)
    sar_catalog = pystac.Catalog.from_file(args.sar_catalog)

    # TODO: Do better than to arbitrarily choose these
    test_set = set(["1"])
    training_set = set(["2", "3"])
    validation_set = set(["15", "16"])

    mldata_catalog = pystac.Catalog(
        "usfimr-s1-mldata", "MLData STAC Catalog for usfimr-s1 dataset"
    )

    add_set(test_set, "test", mldata_catalog, sar_catalog, usfimr_collection)
    add_set(training_set, "training", mldata_catalog, sar_catalog, usfimr_collection)
    add_set(
        validation_set, "validation", mldata_catalog, sar_catalog, usfimr_collection
    )

    mldata_catalog.normalize_and_save(
        "./data/mldata-catalog", catalog_type=pystac.CatalogType.SELF_CONTAINED
    )


if __name__ == "__main__":
    main()
