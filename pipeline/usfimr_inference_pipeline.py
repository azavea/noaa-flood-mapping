# flake8: noqa

import os
from os.path import join
from typing import List

import numpy as np
from pystac import STAC_IO, Catalog, Collection, Item
from rastervision.core.backend import *
from rastervision.core.data import *
from rastervision.core.data.raster_source.multi_raster_source_config import (
    MultiRasterSourceConfig, SubRasterSourceConfig)
from rastervision.core.data.raster_transformer import *
from rastervision.core.rv_pipeline import *
from rastervision.gdal_vsi.vsi_file_system import VsiFileSystem
from rastervision.pytorch_backend import *
from rastervision.pytorch_learner import *


def image_source(prefix: str, use_hand: bool):
    vh_uris = [prefix + '/VH.tiff']
    vv_uris = [prefix + '/VV.tiff']
    hand_uris = [prefix + '/HAND.tiff']

    vh_source = RasterioSourceConfig(
        uris=vh_uris,
        transformers=[
            NanTransformerConfig(),
            CastTransformerConfig(to_dtype='np.float32')
        ],
        channel_order=[0])
    vv_source = RasterioSourceConfig(
        uris=vv_uris,
        transformers=[
            NanTransformerConfig(),
            CastTransformerConfig(to_dtype='np.float32')
        ],
        channel_order=[0])
    hand_source = RasterioSourceConfig(
        uris=hand_uris,
        transformers=[
            NanTransformerConfig(),
            CastTransformerConfig(to_dtype='np.float32')
        ],
        channel_order=[0])

    if use_hand:
        raster_source = MultiRasterSourceConfig(
            raster_sources=[
                SubRasterSourceConfig(raster_source=vh_source,
                                      target_channels=[0]),
                SubRasterSourceConfig(raster_source=vv_source,
                                      target_channels=[1]),
                SubRasterSourceConfig(raster_source=hand_source,
                                      target_channels=[2]),
            ],
            force_same_dtype=True,
            allow_different_extents=True,
            transformers=[StatsTransformerConfig()],
        )
    elif not use_hand:
        raster_source = MultiRasterSourceConfig(
            raster_sources=[
                SubRasterSourceConfig(raster_source=vh_source,
                                      target_channels=[0]),
                SubRasterSourceConfig(raster_source=vv_source,
                                      target_channels=[1]),
            ],
            force_same_dtype=True,
            allow_different_extents=True,
            transformers=[StatsTransformerConfig()],
        )

    return raster_source


def make_scenes_from_prefix(prefix: str, use_hand: bool) -> [SceneConfig]:

    src = image_source(prefix, use_hand)
    scene_configs = [SceneConfig(id=prefix.split('/')[-1], raster_source=src)]

    return scene_configs


def make_scenes(prefixes: List[str], use_hand: bool):

    scene_groups = [
        make_scenes_from_prefix(prefix, use_hand) for prefix in prefixes
    ]

    scenes = []
    for group in scene_groups:
        for scene in group:
            scenes.append(scene)
    return scenes


def build_dataset_from_prefixes(prefixes: List[str], class_config: ClassConfig,
                                use_hand: bool) -> DatasetConfig:

    validation_scenes = make_scenes(prefixes, use_hand)

    return DatasetConfig(
        class_config=class_config,
        train_scenes=validation_scenes[0:1],
        validation_scenes=validation_scenes,
    )


def get_config(runner,
               root_uri,
               analyze_uri,
               train_uri,
               prefixes,
               use_hand,
               three_class):

    with open(prefixes, 'r') as f:
        prefixes = json.load(f)

    if three_class:
        class_config: ClassConfig = ClassConfig(
            names=["background", "water", "flood"],
            colors=["brown", "blue", "purple"])
    else:
        class_config: ClassConfig = ClassConfig(
            names=["background", "water"],
            colors=["brown", "blue"])

    dataset = build_dataset_from_prefixes(prefixes, class_config, use_hand)

    chip_size = 300
    backend = PyTorchSemanticSegmentationConfig(
        model=SemanticSegmentationModelConfig(backbone=Backbone.resnet50),
        solver=SolverConfig(lr=1e-4, num_epochs=1, batch_sz=1),
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.sliding, )

    return SemanticSegmentationConfig(
        root_uri=root_uri,
        analyze_uri=analyze_uri,
        train_uri=train_uri,
        dataset=dataset,
        backend=backend,
        train_chip_sz=chip_size,
        predict_chip_sz=chip_size,
        chip_options=chip_options,
    )
