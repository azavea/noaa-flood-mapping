import argparse

import pystac

import numpy as np
from stac_utils.s3_io import register_s3_io
from sklearn.model_selection import train_test_split


def train_test_val_split(collection, test_size, val_size, random_state):
    train, remain = train_test_split(collection, test_size=(val_size + test_size), random_state=random_state)
    new_test_size = np.around(test_size / (val_size + test_size), 2)
    new_val_size = 1.0 - new_test_size

    val, test = train_test_split(remain, test_size=new_test_size, random_state=random_state)
    return train, test, val


def collect_items(sar_catalog, usfimr_collection):
    images = []
    labels_collection = pystac.Collection(
        "labels", "labels", usfimr_collection.extent
    )
    labels_collection = pystac.Collection(
        "usfimr_sar_labels", "usfimr_sar_labels", usfimr_collection.extent
    )

    for flood_id in ["1", "2", "3", "15", "16"]:
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
            images.append(sar_item_clone)

    return images, labels_collection


def main():
    register_s3_io()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--usfimr-collection", default="s3://usfimr-data/collection.json"
    )
    parser.add_argument("--sar-catalog", required=True, type=str)
    parser.add_argument("--random-seed", default=42, type=int)
    args = parser.parse_args()

    usfimr_collection = pystac.Collection.from_file(args.usfimr_collection)
    sar_catalog = pystac.Catalog.from_file(args.sar_catalog)

    mldata_catalog = pystac.Catalog(
        "usfimr-s1-mldata", "MLData STAC Catalog for usfimr-s1 dataset"
    )

    image_items, labels_collection = collect_items(sar_catalog, usfimr_collection)

    training, testing, validation = train_test_val_split(image_items, 0.2, 0.2, random_state=args.random_seed)

    train_collection = pystac.Collection(
        "train", "train", usfimr_collection.extent
    )
    for t in training:
        train_collection.add_item(t)
    test_collection = pystac.Collection(
        "test", "test", usfimr_collection.extent
    )
    for t in testing:
        test_collection.add_item(t)
    val_collection = pystac.Collection(
        "validation", "validation", usfimr_collection.extent
    )
    for v in validation:
        val_collection.add_item(v)

    mldata_catalog.add_child(labels_collection)
    mldata_catalog.add_child(train_collection)
    mldata_catalog.add_child(test_collection)
    mldata_catalog.add_child(val_collection)

    mldata_catalog.normalize_and_save(
        "./data/mldata-catalog_seed{}".format(args.random_seed), catalog_type=pystac.CatalogType.SELF_CONTAINED
    )


if __name__ == "__main__":
    main()
