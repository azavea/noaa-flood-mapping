#!/usr/bin/env python3

import argparse
import sys
import csv

import numpy as np
from pystac import Catalog, CatalogType, Collection, Link, LinkType
from sklearn.model_selection import train_test_split

# Map of experiment name to collection name in sen1floods11 STAC catalog
EXPERIMENT = {"s2weak": "NoQC", "s1weak": "S1Flood_NoQC", "hand": "QC_v2"}


def check_experiment(val):
    if val in set(EXPERIMENT.keys()):
        return val
    else:
        raise ValueError


def normalized_float(val):
    float_val = float(val)
    if float_val < 0 or float_val > 1:
        raise ValueError
    return float_val


def mapper(item):
    """ Map STAC LabelItem to list of STAC Item images with labels as links.

    This is a one to many mapping because each label item could be sourced
    from multiple image scenes.

    """
    source_links = list(filter(lambda l: l.rel == "source", item.links))
    for link in source_links:
        link.resolve_stac_object()
    source_items = [link.target.clone() for link in source_links]
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


def train_test_val_split(arrays, train_size, test_size, val_size, random_state):
    """ A helper function resembling sklearn's train_test_split but with the addition of validation output """
    proportion_sum = train_size + test_size + val_size
    if proportion_sum != 1.0:
        sys.exit(
            "train, test, validation proprortions must add up to 1.0; currently {}".format(
                proportion_sum
            )
        )

    train, test = train_test_split(arrays, test_size=1 - train_size)
    validation, test = train_test_split(
        test, test_size=test_size / (test_size + val_size)
    )

    return train, test, validation


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "experiment",
        type=check_experiment,
        help="Experiment to generate. One of {}".format(set(EXPERIMENT.keys())),
    )
    parser.add_argument(
        "--sample",
        "-s",
        default=1.0,
        dest="sample",
        type=normalized_float,
        help="Percentage of total dataset to build mldata STAC from. Useful for quick experiments",
    )
    parser.add_argument(
        "--test-size",
        "-t",
        default=0.2,
        dest="test_size",
        type=normalized_float,
        help="Percentage of dataset to use for test set",
    )
    parser.add_argument(
        "--train-size",
        "-T",
        default=0.6,
        dest="train_size",
        type=normalized_float,
        help="Percentage of dataset to use for train set",
    )
    parser.add_argument(
        "--val-size",
        "-v",
        default=0.2,
        dest="val_size",
        type=normalized_float,
        help="Percentage of dataset to use for validation set",
    )
    parser.add_argument(
        "--random-seed",
        "-r",
        dest="random_seed",
        default=None,
        type=int,
        help="Random seed for generating test / train split. Passing the same value will yield the same splits.",
    )
    parser.add_argument(
        "--valid-csv",
        dest="valid_csv",
        default=None,
        type=str,
        help="The CSV from which to take the list of validation images"
    )
    parser.add_argument(
        "--test-csv",
        dest="test_csv",
        default=None,
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

    if args.test_csv is not None:
        test_set = set()
        with open(args.test_csv) as csvfile:
            for row in csv.reader(csvfile):
                name = row[0].split("/")[1]
                name = "_".join(name.split("_")[0:-1])
                test_set.add(name)

    def yes_validation(item):
        id = item.id
        id = "_".join(id.split("_")[0:-1])
        return id in valid_set and "Bolivia" not in item.id

    def yes_test(item):
        id = item.id
        id = "_".join(id.split("_")[0:-1])
        return id in test_set

    def yes_training(item):
        return not yes_test(item) and not yes_validation(item) and "Bolivia" not in item.id

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
    validation_label_items = [i.clone() for i in test_label_collection.get_items() if yes_validation(i)]
    mldata_catalog.add_child(validation_labels_collection)
    validation_labels_collection.add_items(
        [i.clone() for i in label_collection.get_items() if yes_validation(i)])
    mldata_catalog.add_child(validation_imagery_collection)
    validation_imagery_items = np.array(list(map(mapper, validation_label_items))).flatten()
    validation_imagery_collection.add_items(validation_imagery_items)
    print("Added {} items to validation catalog".format(len(validation_label_items)))

    # Test Imagery and Labels
    test_imagery_collection = Collection(
        "test_imagery",
        "test items for experiment",
        test_label_collection.extent
    )
    test_labels_collection = Collection(
        "test_labels",
        "labels for scenes in the test collection",
        test_label_collection.extent,
    )
    test_label_items = [i.clone() for i in test_label_collection.get_items() if yes_test(i)]
    mldata_catalog.add_child(test_labels_collection)
    test_labels_collection.add_items([i.clone()
                                      for i in label_collection.get_items() if yes_test(i)])
    mldata_catalog.add_child(test_imagery_collection)
    test_imagery_items = np.array(list(map(mapper, test_label_items))).flatten()
    test_imagery_collection.add_items(test_imagery_items)
    print("Added {} items to test catalog".format(len(test_label_items)))

    print("Saving catalog...")
    mldata_catalog.normalize_hrefs("./data/mldata_{}".format(experiment))
    mldata_catalog.save(CatalogType.SELF_CONTAINED)


if __name__ == "__main__":
    main()
