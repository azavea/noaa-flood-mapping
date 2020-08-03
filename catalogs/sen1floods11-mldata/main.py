import argparse

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


def main():
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "experiment",
        type=check_experiment,
        help="Experiment to generate. One of {}".format(set(EXPERIMENT.keys())),
    )
    parser.add_argument(
        "--test-size",
        "-t",
        default=0.3,
        dest="test_size",
        type=normalized_float,
        help="Percentage of dataset to use for test set",
    )
    parser.add_argument(
        "--train-size",
        "-T",
        default=None,
        dest="train_size",
        type=normalized_float,
        help="Percentage of dataset to use for train set",
    )
    parser.add_argument(
        "--random-seed",
        "-r",
        dest="random_seed",
        default=None,
        type=int,
        help="Random seed for generating test / train split. Passing the same value will yield the same splits.",
    )
    args = parser.parse_args()

    catalog = Catalog.from_file("./data/catalog/catalog.json")

    experiment = args.experiment
    label_collection_id = EXPERIMENT[experiment]
    label_collection = catalog.get_child(label_collection_id)

    mldata_catalog = Catalog(
        "{}_mldata".format(experiment),
        "Test/Train split for {} experiment in sen1floods11".format(experiment),
    )

    train_collection = Collection(
        "train", "training items for experiment", label_collection.extent
    )
    mldata_catalog.add_child(train_collection)

    test_collection = Collection(
        "test", "test items for collection", label_collection.extent
    )
    mldata_catalog.add_child(test_collection)

    mldata_labels_collection = Collection(
        "labels",
        "labels for scenese in test and train collections",
        label_collection.extent,
    )
    label_items = [i.clone() for i in label_collection.get_items()]
    mldata_catalog.add_child(mldata_labels_collection)
    mldata_labels_collection.add_items(label_items)

    print("Constructing new ml scenes...")
    scenes = np.array(list(map(mapper, label_items))).flatten()
    train_items, test_items = train_test_split(
        scenes,
        test_size=args.test_size,
        train_size=args.train_size,
        random_state=args.random_seed,
    )

    train_collection.add_items(train_items)
    print("Added {} items to train catalog".format(len(train_items)))
    test_collection.add_items(test_items)
    print("Added {} items to test catalog".format(len(test_items)))

    print("Saving catalog...")
    mldata_catalog.normalize_hrefs("./data/mldata_{}".format(experiment))
    import ipdb

    ipdb.set_trace()
    mldata_catalog.save(CatalogType.SELF_CONTAINED)


if __name__ == "__main__":
    main()
