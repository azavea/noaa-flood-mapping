# flake8: noqa

import os
from os.path import join

from rastervision.core.rv_pipeline import *
from rastervision.core.backend import *
from rastervision.core.data import *
from rastervision.pytorch_backend import *
from rastervision.pytorch_learner import *
from rastervision.gdal_vsi.vsi_file_system import VsiFileSystem

from pystac import Catalog, Collection, Item, MediaType
from rastervision.core.data import (
    ClassConfig,
    RasterioSourceConfig,
    StatsTransformerConfig,
    SemanticSegmentationLabelSourceConfig,
    RasterizedSourceConfig,
    GeoJSONVectorSourceConfig,
    RasterizerConfig,
    SceneConfig,
    DatasetConfig,
)
from typing import Generator


def image_sources(item: Item, channel_order: [int]):
    image_keys = [key for key in item.assets.keys() if key.startswith("image")]
    image_keys.sort()
    image_uris = [
        VsiFileSystem.uri_to_vsi_path(item.assets[key].href) for key in image_keys
    ]
    return RasterioSourceConfig(
        uris=image_uris,
        channel_order=channel_order,
        transformers=[StatsTransformerConfig()],
    )


def make_scenes_from_item(item: Item, channel_order: [int]) -> [SceneConfig]:
    # get all links to labels
    label_items = [
        link.resolve_stac_object().target for link in item.links if link.rel == "labels"
    ]

    # image source configs
    image_source = image_sources(item, channel_order)

    scene_configs = []
    # iterate through links, building a scene config per link
    for label_item in label_items:
        label_asset = label_item.assets["labels"]
        label_uri = label_asset.href

        # semantic segmentation label configuration; convert to tif as necesary
        if label_asset.media_type == MediaType.GEOTIFF:
            raster_label_source = RasterioSourceConfig(uris=[label_asset.href],)
        else:
            vector_label_source = GeoJSONVectorSourceConfig(
                uri=label_uri, default_class_id=0, ignore_crs_field=True
            )
            raster_label_source = RasterizedSourceConfig(
                vector_source=vector_source,
                rasterizer_config=RasterizerConfig(background_class_id=1),
            )

        label_source = SemanticSegmentationLabelSourceConfig(
            raster_source=raster_label_source
        )

        scene_configs.append(
            SceneConfig(
                id=item.id, raster_source=image_source, label_source=label_source
            )
        )
    return scene_configs


def make_scenes(collection: Collection, channel_order: [int]):
    scene_groups = [
        make_scenes_from_item(item, channel_order) for item in collection.get_items()
    ]
    scenes = []
    for group in scene_groups:
        for scene in group:
            scenes.append(scene)
    return scenes


def build_dataset_from_catalog(
    catalog: Catalog, channel_order: [int], class_config: ClassConfig
) -> DatasetConfig:

    # Read taining scenes from STAC
    train_collection = catalog.get_child(id="train")
    train_scenes = make_scenes(train_collection, channel_order)

    # Read testing scenes from STAC
    test_collection = catalog.get_child(id="test")
    test_scenes = make_scenes(test_collection, channel_order)

    # Read validation scenes from STAC
    validation_collection = catalog.get_child(id="validation")
    validation_scenes = make_scenes(validation_collection, channel_order)

    return DatasetConfig(
        class_config=class_config,
        train_scenes=train_scenes,
        test_scenes=test_scenes,
        validation_scenes=validation_scenes,
    )


def get_config(runner):
    output_root_uri = os.environ.get("OUTPUT_ROOT_URI")
    if output_root_uri is None:
        sys.exit("No output URI set. Set the environment variable OUTPUT_ROOT_URI")

    catalog_root = os.environ.get("CATALOG_ROOT_URI")
    if catalog_root is None:
        sys.exit("No catalog URI set. Set the environment variable CATALOG_ROOT_URI")

    # Read STAC catalog
    catalog: Catalog = Catalog.from_file(catalog_root)

    # TODO: pull desired channels from root collection properties
    channel_ordering: [int] = [0, 1]

    # TODO: pull ClassConfig info from root collection properties
    class_config: ClassConfig = ClassConfig(
        names=["not water", "water"], colors=["white", "blue"]
    )

    dataset = build_dataset_from_catalog(catalog, channel_ordering, class_config)

    chip_sz = 300
    backend = PyTorchSemanticSegmentationConfig(
        model=SemanticSegmentationModelConfig(backbone=Backbone.resnet50),
        solver=SolverConfig(lr=1e-4, num_epochs=1, batch_sz=2),
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.random_sample, chips_per_scene=10
    )

    return SemanticSegmentationConfig(
        root_uri=output_root_uri,
        dataset=dataset,
        backend=backend,
        train_chip_sz=chip_sz,
        predict_chip_sz=chip_sz,
        chip_options=chip_options,
    )

