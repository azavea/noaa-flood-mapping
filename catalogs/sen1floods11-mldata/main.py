from copy import deepcopy

from pystac import (
    Catalog,
    CatalogType,
    Collection,
    Extensions,
    Item,
)
from sklearn.model_selection import train_test_split


EXPERIMENT = {"s2weak": {"labels": "NoQC"}}


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
    catalog = Catalog.from_file("./data/catalog/catalog.json")

    experiment = "s2weak"
    label_collection_id = EXPERIMENT[experiment]["labels"]
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
        list(label_items), test_size=0.3, random_state=42
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
