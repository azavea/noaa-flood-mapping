# flake8: noqa

import os
from os.path import join
from typing import Generator

from pystac import STAC_IO, Catalog, Collection, Item, MediaType
from rastervision.core.backend import *
from rastervision.core.data import *
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

    return uri

STAC_IO.read_text_method = \
    lambda uri: VsiFileSystem.read_str(pystac_workaround(uri))
STAC_IO.write_text_method = noop_write_method


def image_sources(item: Item, channel_order: [int]):
    image_keys = [key for key in item.assets.keys() if key.startswith("image")]
    image_keys.sort()
    image_uris = [
        VsiFileSystem.uri_to_vsi_path(item.assets[key].href)
        for key in image_keys
    ]
    return RasterioSourceConfig(
        uris=image_uris,
        channel_order=channel_order,
        transformers=[
            NanTransformerConfig(),
            StatsTransformerConfig(),
        ],
    )


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
        raster_label_source = RasterioSourceConfig(uris=[label_asset.href], )
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
        validation_scenes=(test_scenes_0 + test_scenes_1),
    )


def get_config(runner,
               root_uri,
               catalog_root,
               epochs=20,
               batch_size=8,
               gamma=0.0,
               chip_uri=None,
               analyze_uri=None):

    # Read STAC catalog
    catalog: Catalog = Catalog.from_file(pystac_workaround(catalog_root))

    # TODO: pull desired channels from root collection properties
    channel_ordering: [int] = [0, 1]

    # TODO: pull ClassConfig info from root collection properties
    class_config: ClassConfig = ClassConfig(names=["background", "water"],
                                            colors=["brown", "blue"])

    dataset = build_dataset_from_catalog(catalog, channel_ordering,
                                         class_config)

    external_loss_def = ExternalModuleConfig(
        github_repo='AdeelH/pytorch-multi-class-focal-loss',
        name='focal_loss',
        entrypoint='focal_loss',
        force_reload=False,
        entrypoint_kwargs={
            'alpha': [0.1, 0.9],
            'gamma': float(gamma),
            'ignore_index': 2,
        })

    chip_size = 512
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
        predict_normalize=True,
        num_workers=0,
    )
    chip_options = SemanticSegmentationChipOptions(
        window_method=SemanticSegmentationWindowMethod.sliding,
        stride=chip_size)

    if analyze_uri is not None and chip_uri is not None:
        return SemanticSegmentationConfig(
            analyze_uri=analyze_uri,
            chip_uri=chip_uri,
            root_uri=root_uri,
            dataset=dataset,
            backend=backend,
            train_chip_sz=chip_size,
            predict_chip_sz=chip_size,
            chip_options=chip_options,
            img_format='npy',
            label_format='png',
        )
    elif analyze_uri is not None and chip_uri is None:
        return SemanticSegmentationConfig(
            analyze_uri=analyze_uri,
            root_uri=root_uri,
            dataset=dataset,
            backend=backend,
            train_chip_sz=chip_size,
            predict_chip_sz=chip_size,
            chip_options=chip_options,
            img_format='npy',
            label_format='png',
        )
    else:
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
