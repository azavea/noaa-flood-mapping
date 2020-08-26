#!/usr/bin/env python3

import argparse
import sys
import csv

import numpy as np
from pystac import Catalog, CatalogType, Collection, Link, LinkType
from sklearn.model_selection import train_test_split

# Map of experiment name to collection name in sen1floods11 STAC catalog
EXPERIMENT = {"s2weak": "NoQC", "s1weak": "S1Flood_NoQC", "hand": "QC_v2"}


def mapper(item):
    """ Map STAC LabelItem to list of STAC Item images with labels as links.

    This is a one to many mapping because each label item could be sourced
    from multiple image scenes.

    """
    source_links = list(filter(lambda l: l.rel == "source", item.links))
    for link in source_links:
        link.resolve_stac_object()
    source_items = [link.target.clone() for link in source_links if "_S1" in link.target.id]
    if len(source_items) == 0:
        print("WARNING: No source images for {}".format(item.id))

    for source_item in source_items:
        label_asset = item.assets["labels"]
        # Remove label item source links to avoid recursion -- we're inverting
        # the label / item relationship.
        item.links = list(filter(lambda l: l.rel != "source", item.links))
        source_item.links = [
            Link(
                "labels",
                item,
                link_type=LinkType.RELATIVE,
                media_type=label_asset.media_type,
            ).set_owner(source_item)
        ]

    return source_items


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "experiment",
        choices=EXPERIMENT.keys(),
        type=str,
        help="Experiment to generate. One of {}".format(set(EXPERIMENT.keys())),
    )
    parser.add_argument(
        "--valid-csv",
        dest="valid_csv",
        default=None,
        type=str,
        help="The CSV from which to take the list of validation images"
    )
    parser.add_argument(
        "--test-csvs",
        dest="test_csvs",
        default=[],
        nargs='+',
        type=str,
        help="The CSVs from which to take the list of training images"
    )
    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()

    if args.valid_csv is not None:
        valid_set = set()
        with open(args.valid_csv) as csvfile:
            for row in csv.reader(csvfile):
                name = row[0].split("/")[1]
                name = "_".join(name.split("_")[0:-1])
                valid_set.add(name)

    test_sets = []
    any_test_set = set()
    for test_csv in args.test_csvs:
        test_set = set()
        with open(test_csv) as csvfile:
            for row in csv.reader(csvfile):
                name = row[0].split("/")[1]
                name = "_".join(name.split("_")[0:-1])
                test_set.add(name)
                any_test_set.add(name)
        test_sets.append(test_set)

    def yes_validation(item):
        id = item.id
        id = "_".join(id.split("_")[0:-1])
        return id in valid_set and "Bolivia" not in item.id

    def yes_test_i(i, item):
        id = item.id
        id = "_".join(id.split("_")[0:-1])
        return id in test_sets[i]

    def yes_any_test(item):
        id = item.id
        id = "_".join(id.split("_")[0:-1])
        return id in any_test_set

    def yes_training(item):
        return not yes_any_test(item) and not yes_validation(item) and "Bolivia" not in item.id

    catalog = Catalog.from_file("./data/catalog/catalog.json")

    experiment = args.experiment
    label_collection_id = EXPERIMENT[experiment]
    label_collection = catalog.get_child(label_collection_id)
    test_label_collection_id = EXPERIMENT["hand"]
    test_label_collection = catalog.get_child(test_label_collection_id)

    # Top-Level
    mldata_catalog = Catalog(
        "{}_mldata".format(experiment),
        "Training/Validation/Test split for {} experiment in sen1floods11".format(experiment),
    )

    # Training Imagery and Labels
    training_imagery_collection = Collection(
        "training_imagery",
        "training items for experiment",
        label_collection.extent
    )
    training_labels_collection = Collection(
        "training_labels",
        "labels for scenes in the training collection",
        label_collection.extent,
    )
    training_label_items = [i.clone() for i in label_collection.get_items() if yes_training(i)]
    mldata_catalog.add_child(training_labels_collection)
    training_labels_collection.add_items(
        [i.clone() for i in label_collection.get_items() if yes_training(i)])
    mldata_catalog.add_child(training_imagery_collection)
    training_imagery_items = np.array(list(map(mapper, training_label_items))).flatten()
    training_imagery_collection.add_items(training_imagery_items)
    print("Added {} items to training catalog".format(len(training_label_items)))

    # Validation Imagery and Labels
    validation_imagery_collection = Collection(
        "validation_imagery",
        "validation items for experiment",
        test_label_collection.extent
    )
    validation_labels_collection = Collection(
        "validation_labels",
        "labels for scenes in the validation collection",
        test_label_collection.extent,
    )
    validation_label_items = [i.clone()
                              for i in test_label_collection.get_items() if yes_validation(i)]
    mldata_catalog.add_child(validation_labels_collection)
    validation_labels_collection.add_items(
        [i.clone() for i in label_collection.get_items() if yes_validation(i)])
    mldata_catalog.add_child(validation_imagery_collection)
    validation_imagery_items = np.array(list(map(mapper, validation_label_items))).flatten()
    validation_imagery_collection.add_items(validation_imagery_items)
    print("Added {} items to validation catalog".format(len(validation_label_items)))

    # Test Imagery and Labels
    for i in range(len(test_sets)):
        test_imagery_collection = Collection(
            "test_imagery_{}".format(i),
            "test items for experiment",
            test_label_collection.extent
        )
        test_labels_collection = Collection(
            "test_labels_{}".format(i),
            "labels for scenes in the test collection",
            test_label_collection.extent,
        )
        test_label_items = [j.clone()
                            for j in test_label_collection.get_items() if yes_test_i(i, j)]
        mldata_catalog.add_child(test_labels_collection)
        test_labels_collection.add_items([j.clone()
                                          for j in label_collection.get_items() if yes_test_i(i, j)])
        mldata_catalog.add_child(test_imagery_collection)
        test_imagery_items = np.array(list(map(mapper, test_label_items))).flatten()
        test_imagery_collection.add_items(test_imagery_items)
        print("Added {} items to test catalog {}".format(len(test_label_items), i))

    print("Saving catalog...")
    mldata_catalog.normalize_hrefs("./data/mldata_{}".format(experiment))
    mldata_catalog.save(CatalogType.SELF_CONTAINED)


if __name__ == "__main__":
    main()
