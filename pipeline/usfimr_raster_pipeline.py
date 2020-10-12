# flake8: noqa

import os
from os.path import join
from typing import Generator

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


def noop_write_method(uri, txt):
    pass


def pystac_workaround(uri):
    if uri.startswith('/vsizip/') and not uri.startswith('/vsizip//'):
        uri = uri.replace('/vsizip/', '/vsizip//')
    if uri.startswith(
            '/vsitar/vsigzip/') and not uri.startswith('/vsitar/vsigzip//'):
        uri = uri.replace('/vsitar/vsigzip/', '/vsitar/vsigzip//')
    uri = uri.replace('/usfimr_sar_labels/', '/usfimr_sar_labels_tif/')

    return uri

STAC_IO.read_text_method = \
    lambda uri: VsiFileSystem.read_str(pystac_workaround(uri))
STAC_IO.write_text_method = noop_write_method


def image_sources(item: Item, use_hand: bool):
    vh_keys = [key for key in item.assets.keys() if key.startswith("VH")]
    vh_keys.sort()
    vh_uris = [item.assets[key].href for key in vh_keys]

    vv_keys = [key for key in item.assets.keys() if key.startswith("VV")]
    vv_keys.sort()
    vv_uris = [item.assets[key].href for key in vv_keys]

    hand_keys = [key for key in item.assets.keys() if key.startswith("HAND")]
    hand_keys.sort()
    hand_uris = [item.assets[key].href for key in hand_keys]

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
        )

    return raster_source


def make_scenes_from_item(item: Item, use_hand: bool,
                          three_class: bool) -> [SceneConfig]:

    # get all links to labels
    label_items = [
        link.resolve_stac_object().target for link in item.links
        if link.rel == "labels"
    ]

    # image source configs
    image_source = image_sources(item, use_hand)

    scene_configs = []
    # iterate through links, building a scene config per link
    for label_item in label_items:
        label_asset = label_item.assets["labels"]
        label_uri = label_asset.href.replace('s3://', '/vsis3/')

        if three_class:
            raster_label_source = RasterioSourceConfig(uris=[label_asset.href])
        else:
            raster_label_source = RasterioSourceConfig(
                uris=[label_asset.href],
                transformers=[ReclassTransformerConfig(mapping={2: 1})],
            )

        label_source = SemanticSegmentationLabelSourceConfig(
            raster_source=raster_label_source)

        scene_configs.append(
            SceneConfig(id=item.id,
                        raster_source=image_source,
                        label_source=label_source))

    return scene_configs


def make_scenes(collection: Collection, use_hand: bool, three_class: bool):
    scene_groups = [
        make_scenes_from_item(item, use_hand, three_class)
        for item in collection.get_items()
    ]
    scenes = []
    for group in scene_groups:
        for scene in group:
            scenes.append(scene)
    return scenes


def build_dataset_from_catalog(catalog: Catalog, class_config: ClassConfig,
                               use_hand: bool,
                               three_class: bool) -> DatasetConfig:

    # Read taining scenes from STAC
    train_collection = catalog.get_child(id="train")
    train_scenes = make_scenes(train_collection, use_hand, three_class)

    # Read validation scenes from STAC
    validation_collection = catalog.get_child(id="validation")
    validation_scenes = make_scenes(validation_collection, use_hand,
                                    three_class)

    # Read test scenes from STAC
    test_collection = catalog.get_child(id="test")
    test_scenes = make_scenes(test_collection, use_hand, three_class)

    return DatasetConfig(
        class_config=class_config,
        train_scenes=train_scenes,
        validation_scenes=validation_scenes,
    )


def get_config(runner,
               root_uri,
               catalog_root,
               epochs=20,
               batch_size=16,
               gamma=0,
               use_hand=False,
               three_class=False):

    use_hand = (use_hand != False) and (use_hand != 'False')
    three_class = (three_class != False) and (three_class != 'False')

    # Read STAC catalog
    catalog: Catalog = Catalog.from_file(pystac_workaround(catalog_root))

    if three_class:
        class_config: ClassConfig = ClassConfig(
            names=["background", "water", "flood"],
            colors=["brown", "blue", "purple"])
        target_class_ids = [1, 2]
        alphas = [0.1, 0.4, 0.5, 0.0]
    else:
        class_config: ClassConfig = ClassConfig(names=["background", "water"],
                                                colors=["brown", "blue"])
        target_class_ids = [1]
        alphas = [0.1, 0.9, 0.0]

    dataset = build_dataset_from_catalog(catalog, class_config, use_hand,
                                         three_class)

    external_loss_def = ExternalModuleConfig(
        github_repo='jamesmcclain/pytorch-multi-class-focal-loss:ignore',
        name='focal_loss',
        entrypoint='focal_loss',
        force_reload=False,
        entrypoint_kwargs={
            'alpha': alphas,
            'gamma': int(gamma),
            'ignore_index': 2 if not three_class else 3,
        })

    chip_size = 300
    backend = PyTorchSemanticSegmentationConfig(
        model=SemanticSegmentationModelConfig(backbone=Backbone.resnet50),
        solver=SolverConfig(lr=1e-4,
                            num_epochs=int(epochs),
                            batch_sz=int(batch_size),
                            one_cycle=True,
                            ignore_last_class='force',
                            external_loss_def=external_loss_def),
        log_tensorboard=False,
        run_tensorboard=False,
        predict_normalize=False,
        num_workers=0,
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.sliding,
        negative_survival_prob=0.0,
        target_class_ids=target_class_ids,
        target_count_threshold=int(0.05 * chip_size**2),
        stride=chip_size // 2)

    return SemanticSegmentationConfig(
        root_uri=root_uri,
        dataset=dataset,
        backend=backend,
        train_chip_sz=chip_size,
        predict_chip_sz=chip_size,
        chip_options=chip_options,
        img_format='npy',
        label_format='png',
    )
