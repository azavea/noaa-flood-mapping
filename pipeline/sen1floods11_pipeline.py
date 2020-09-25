# flake8: noqa

import os
from os.path import join
from typing import Generator

from pystac import STAC_IO, Catalog, Collection, Item, MediaType
from rastervision.core.backend import *
from rastervision.core.data import *
from rastervision.core.data import (ClassConfig, DatasetConfig,
                                    GeoJSONVectorSourceConfig,
                                    RasterioSourceConfig,
                                    RasterizedSourceConfig, RasterizerConfig,
                                    SceneConfig,
                                    SemanticSegmentationLabelSourceConfig,
                                    StatsTransformerConfig)
from rastervision.core.rv_pipeline import *
from rastervision.gdal_vsi.vsi_file_system import VsiFileSystem
from rastervision.pytorch_backend import *
from rastervision.pytorch_learner import *


def noop_write_method(uri, txt):
    pass


STAC_IO.read_text_method = VsiFileSystem.read_str
STAC_IO.write_text_method = noop_write_method


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
            raster_label_source = RasterioSourceConfig(
                uris=[label_asset.href],)
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
    train_collection = catalog.get_child(id="training_imagery")  # ???
    train_collection = catalog.get_child(id="training_imagery")
    train_scenes = make_scenes(train_collection, channel_order)

    # Read validation scenes from STAC
    validation_collection = catalog.get_child(id="validation_imagery")
    validation_scenes = make_scenes(validation_collection, channel_order)

    # Read testing scenes from STAC
    test_collection_0 = catalog.get_child(id="test_imagery_0")
    test_scenes_0 = make_scenes(test_collection_0, channel_order)
    test_collection_1 = catalog.get_child(id="test_imagery_1")
    test_scenes_1 = make_scenes(test_collection_1, channel_order)

    return DatasetConfig(
        class_config=class_config,
        train_scenes=train_scenes,
        test_scenes=test_scenes_0,
        validation_scenes=validation_scenes,
    )


def get_config(runner, root_uri, catalog_root, hours):
    # Read STAC catalog
    catalog: Catalog = Catalog.from_file(catalog_root)

    # TODO: pull desired channels from root collection properties
    channel_ordering: [int] = [0, 1, 1]

    # TODO: pull ClassConfig info from root collection properties
    class_config: ClassConfig = ClassConfig(
        names=["not water", "water"], colors=["white", "blue"]
    )

    dataset = build_dataset_from_catalog(
        catalog, channel_ordering, class_config)

    chip_sz = 512
    backend = PyTorchSemanticSegmentationConfig(
        model=SemanticSegmentationModelConfig(backbone=Backbone.resnet50),
        solver=SolverConfig(
            lr=1e-4,
            num_epochs=(int(hours) * 4 * 60 * 60) // len(dataset.train_scenes),
            batch_sz=8),
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.sliding, chips_per_scene=1, stride=chip_sz
    )

    return SemanticSegmentationConfig(
        root_uri=root_uri,
        dataset=dataset,
        backend=backend,
        train_chip_sz=chip_sz,
        predict_chip_sz=chip_sz,
        chip_options=chip_options,
        img_format='npy',
    )
