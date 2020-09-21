# flake8: noqa

import os
from os.path import join
from typing import Generator

import numpy as np

from pystac import STAC_IO, Catalog, Collection, Item, MediaType
from rastervision.core.backend import *
from rastervision.core.data import *
from rastervision.core.data import (ClassConfig, DatasetConfig,
                                    GeoJSONVectorSourceConfig,
                                    RasterioSourceConfig,
                                    RasterizedSourceConfig, RasterizerConfig,
                                    SceneConfig,
                                    SemanticSegmentationLabelSourceConfig)
from rastervision.core.data.raster_transformer.raster_transformer import \
    RasterTransformer
from rastervision.core.data.raster_transformer.raster_transformer_config import \
    RasterTransformerConfig
from rastervision.core.rv_pipeline import *
from rastervision.gdal_vsi.vsi_file_system import VsiFileSystem
from rastervision.pytorch_backend import *
from rastervision.pytorch_learner import *


@register_config('float32_transformer')
class Float32RasterTransformerConfig(RasterTransformerConfig):
    def build(self):
        return Float32RasterTransformer()


class Float32RasterTransformer(RasterTransformer):
    def transform(self, chip, channel_ordfer):
        return chip.astype(dtype=np.float32)


def noop_write_method(uri, txt):
    pass


def pystac_workaround(uri):
    if uri.startswith('/vsizip/') and not uri.startswith('/vsizip//'):
        uri = uri.replace('/vsizip/', '/vsizip//')
    if uri.startswith(
            '/vsitar/vsigzip/') and not uri.startswith('/vsitar/vsigzip//'):
        uri = uri.replace('/vsitar/vsigzip/', '/vsitar/vsigzip//')

    return uri
    return VsiFileSystem.read_str(uri)


STAC_IO.read_text_method = \
    lambda uri: VsiFileSystem.read_str(pystac_workaround(uri))
STAC_IO.write_text_method = noop_write_method


def image_sources(item: Item, channel_order: [int]):
    vh_keys = [key for key in item.assets.keys() if key.startswith("VH")]
    vh_keys.sort()
    vh_uris = [item.assets[key].href for key in vh_keys]

    vv_keys = [key for key in item.assets.keys() if key.startswith("VV")]
    vv_keys.sort()
    vv_uris = [item.assets[key].href for key in vv_keys]

    hand_keys = [key for key in item.assets.keys() if key.startswith("HAND")]
    hand_keys.sort()
    hand_uris = [item.assets[key].href for key in hand_keys]

    vh_source = RasterioSourceConfig(uris=vh_uris, channel_order=[0])
    vv_source = RasterioSourceConfig(uris=vv_uris, channel_order=[0])
    hand_source = RasterioSourceConfig(
        uris=hand_uris,
        transformers=[Float32RasterTransformerConfig()],
        channel_order=[0])

    raster_source = MultiRasterSourceConfig(raster_sources=[
        SubRasterSourceConfig(raster_source=vh_source, target_channels=[0]),
        SubRasterSourceConfig(raster_source=vv_source, target_channels=[1]),
        SubRasterSourceConfig(raster_source=hand_source, target_channels=[2]),
    ])

    return raster_source


def make_scenes_from_item(item: Item, channel_order: [int]) -> [SceneConfig]:
    # get all links to labels
    label_items = [
        link.resolve_stac_object().target for link in item.links
        if link.rel == "labels"
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
            raster_label_source = RasterioSourceConfig(uris=[label_asset.href
                                                             ], )
        else:
            vector_label_source = GeoJSONVectorSourceConfig(
                uri=label_uri, default_class_id=0, ignore_crs_field=True)
            raster_label_source = RasterizedSourceConfig(
                vector_source=vector_label_source,
                rasterizer_config=RasterizerConfig(background_class_id=0),
            )

        label_source = SemanticSegmentationLabelSourceConfig(
            raster_source=raster_label_source)

        scene_configs.append(
            SceneConfig(id=item.id,
                        raster_source=image_source,
                        label_source=label_source))
    return scene_configs


def make_scenes(collection: Collection, channel_order: [int]):
    scene_groups = [
        make_scenes_from_item(item, channel_order)
        for item in collection.get_items()
    ]
    scenes = []
    for group in scene_groups:
        for scene in group:
            scenes.append(scene)
    return scenes


def build_dataset_from_catalog(catalog: Catalog, channel_order: [int],
                               class_config: ClassConfig) -> DatasetConfig:

    # Read taining scenes from STAC
    train_collection = catalog.get_child(id="train")  # ???
    # train_collection = catalog.get_child(id="training_imagery")
    train_scenes = make_scenes(train_collection, channel_order)

    # Read validation scenes from STAC
    validation_collection = catalog.get_child(id="validation")
    validation_scenes = make_scenes(validation_collection, channel_order)

    # Read testing scenes from STAC
    test_collection_0 = catalog.get_child(id="test")
    test_scenes_0 = make_scenes(test_collection_0, channel_order)
    # test_collection_1 = catalog.get_child(id="test")
    # test_scenes_1 = make_scenes(test_collection_1, channel_order)

    return DatasetConfig(
        class_config=class_config,
        train_scenes=train_scenes,
        test_scenes=test_scenes_0,
        validation_scenes=validation_scenes,
        img_channels=3,
    )


def get_config(runner, root_uri, catalog_root, hours='4'):
    import pdb ; pdb.set_trace()

    # Read STAC catalog
    catalog: Catalog = Catalog.from_file(catalog_root)

    # TODO: pull desired channels from root collection properties
    channel_ordering: [int] = [0, 1, 1]

    # TODO: pull ClassConfig info from root collection properties
    class_config: ClassConfig = ClassConfig(names=["not water", "water"],
                                            colors=["white", "blue"])

    dataset = build_dataset_from_catalog(catalog, channel_ordering,
                                         class_config)

    chip_sz = 512
    backend = PyTorchSemanticSegmentationConfig(
        model=SemanticSegmentationModelConfig(backbone=Backbone.resnet50),
        solver=SolverConfig(
            lr=1e-4,
            num_epochs=
            1,  #(int(hours) * 4 * 60 * 60) // len(dataset.train_scenes),
            batch_sz=8),
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.sliding,
        chips_per_scene=1,
        stride=chip_sz)

    return SemanticSegmentationConfig(
        root_uri=root_uri,
        dataset=dataset,
        backend=backend,
        train_chip_sz=chip_sz,
        predict_chip_sz=chip_sz,
        chip_options=chip_options,
    )
