#!/usr/bin/env python3
import argparse

import pystac

from stac_utils.s3_io import register_s3_io


def construct_label_item(ttv_item, chip_label_dir):
    clone = ttv_item.clone()
    label_asset = pystac.Asset(
        href=chip_label_dir + clone.id + ".tif",
        description="USFIMR + JRC surface water labels",
        media_type=pystac.MediaType.GEOTIFF,
    )
    clone.assets = {}
    clone.id = clone.id + "_label"
    label_asset.set_owner(clone)
    clone.add_asset("labels", label_asset)
    return clone


def main():
    register_s3_io()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mldata-catalog",
        default="s3://usfimr-s1-mldata/usfimr-s1-mldata-catalog_seed42/catalog.json",
        type=str,
    )
    parser.add_argument(
        "--chip-label-dir",
        default="s3://jrc-fimr-rasterized-labels/version2",
        type=str,
    )
    args = parser.parse_args()

    catalog = pystac.Catalog.from_file(args.mldata_catalog)
    chip_label_dir = args.chip_label_dir.rstrip("/") + "/"

    train = catalog.get_child("train")
    test = catalog.get_child("test")
    validation = catalog.get_child("validation")

    mldata_catalog = pystac.Catalog(
        "usfimr_jrc-s1-mldata-rasterized",
        "MLData STAC Catalog for usfimr+jrc labels of flood and permanent water with S1 imagery",
    )

    label_items = []
    train_collection = pystac.Collection("train", "Training collection", train.extent)
    for t in train.get_items():
        train_collection.add_item(t)
        label_items.append(construct_label_item(t, chip_label_dir))
    test_collection = pystac.Collection("test", "Test collection", test.extent)
    for t in test.get_items():
        test_collection.add_item(t)
        label_items.append(construct_label_item(t, chip_label_dir))
    val_collection = pystac.Collection(
        "validation", "Validation collection", validation.extent
    )
    for v in validation.get_items():
        val_collection.add_item(v)
        label_items.append(construct_label_item(v, chip_label_dir))

    label_catalog = pystac.Catalog(
        "usfimr_sar_labels_tif", "USFIMR + JRC labels for flood detection"
    )
    for l in label_items:
        label_catalog.add_item(l)

    mldata_catalog.add_child(label_catalog)
    mldata_catalog.add_child(train_collection)
    mldata_catalog.add_child(test_collection)
    mldata_catalog.add_child(val_collection)

    mldata_catalog.normalize_and_save(
        "./data/catalog",
        catalog_type=pystac.CatalogType.SELF_CONTAINED,
    )


if __name__ == "__main__":
    main()
