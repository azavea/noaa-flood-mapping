import argparse
from copy import deepcopy

from pystac import (
    Catalog,
    CatalogType,
    Collection,
    Extensions,
    Item,
)
from sklearn.model_selection import train_test_split


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
    """ Map STAC LabelItem to format necessary for our test/train catalogs. """
    params = {
        "id": item.id,
        "bbox": item.bbox,
        "datetime": item.datetime,
        "geometry": item.geometry,
        "properties": deepcopy(item.properties),
        "stac_extensions": [Extensions.LABEL],
    }

    source_links = list(filter(lambda l: l.rel == "source", item.links))
    for link in source_links:
        link.resolve_stac_object()
    source_assets = [link.target.assets["image"].clone() for link in source_links]
    if len(source_assets) == 0:
        print("WARNING: No source images for {}".format(item.id))

    new_item = Item(**params)
    new_item.add_asset("labels", item.assets["labels"].clone())
    for index, source_asset in enumerate(source_assets):
        new_item.add_asset("image_{}".format(index), source_asset)
    return new_item


def main():
    """

    TODOS:
    - [ ] Add self links to sen1floods11 stac by pulling, loading and rewriting the catalog from s3
    - [ ] Publish updated sen1floods11 catalog
    - [ ] Test performance of this code reading from the remote catalog
    - [ ] Update this code to add link to source item in sen1floods11 stack, requires (1)
    - [ ] Update this code to the schema discussed in https://github.com/azavea/noaa-flood-mapping/issues/38#issuecomment-667178703
    - [ ] Do we need to parameterize this code with absolute urls to s3 bucket?

    """
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

    print("Constructing new label items...")
    label_items = map(mapper, label_collection.get_items())
    train_items, test_items = train_test_split(
        list(label_items),
        test_size=args.test_size,
        train_size=args.train_size,
        random_state=args.random_seed,
    )

    train_collection.add_items(train_items)
    print("Added {} items to train catalog".format(len(train_items)))
    test_collection.add_items(test_items)
    print("Added {} items to test catalog".format(len(test_items)))

    print("Saving catalog...")
    mldata_catalog.normalize_and_save(
        "./data/mldata_{}".format(experiment), CatalogType.SELF_CONTAINED
    )


if __name__ == "__main__":
    main()
