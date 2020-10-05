from collections import namedtuple
from datetime import datetime, timedelta, timezone
from itertools import groupby, zip_longest
import logging
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse, urlunparse
from urllib.request import urlretrieve
import xml.etree.ElementTree as ET

import geopandas as gpd
import pystac
from shapely.geometry import GeometryCollection, Polygon, mapping, shape

from sentinel_hub import get_session, stac_search

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


EventProduct = namedtuple(
    "EventProduct",
    [
        "product_id",
        "event_id",
        "event_country",
        "aoi_id",
        "event_time",
        "geometry",
        "data_type",
        "product_type",
        "monitoring_type",
        "revision",
        "version",
        "product_link",
    ],
)


def grouper(iterable, n, fillvalue=None):
    """ Collect data into fixed-length chunks or blocks.

    Example: grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"

    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def main():
    """ Pull Copernicus EU Rapid Mapping Activations data from the GeoRSS feed """
    sentinel_oauth_id = os.environ.get("SENTINELHUB_OAUTH_ID")
    sentinel_oauth_secret = os.environ.get("SENTINELHUB_OAUTH_SECRET")
    if sentinel_oauth_id is None:
        raise ValueError("Must set SENTINELHUB_OAUTH_ID")
    if sentinel_oauth_secret is None:
        raise ValueError("Must set SENTINELHUB_OAUTH_SECRET")

    events_xml_url = "https://emergency.copernicus.eu/mapping/activations-rapid/feed"
    events_xml_file = Path("./data/copernicus-rapid-mapping-activations.xml")
    if not events_xml_file.is_file():
        logger.info("Pulling {}...".format(events_xml_url))
        urlretrieve(events_xml_url, str(events_xml_file))

    event_xml_dir = Path("./data/event-xml")
    os.makedirs(event_xml_dir, exist_ok=True)

    # Generate a list of all unique CEMS products (combination of event, aoi,
    # monitoring type, revision and version) for all flood events in 2019 and 2020
    products = []
    events_root = ET.parse(events_xml_file).getroot()
    for event in events_root.iter("item"):
        category = event.find("category").text.strip().lower()
        if category != "flood":
            continue

        event_id = event.find("guid").text
        title = event.find("title").text
        rss_url = event.find("{http://www.iwg-sem.org/}activationRSS").text
        logger.info(title)

        description = event.find("description").text
        event_dts = re.findall(
            r"Date\/Time of Event \(UTC\):[</b>\s]*?(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2})",
            description,
            flags=re.MULTILINE,
        )
        if len(event_dts) != 1:
            logger.warning("{}: Available event date times {}".format(title, event_dts))
            raise AssertionError()
        event_datetime = datetime.strptime(event_dts[0], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        if event_datetime < datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc):
            continue

        event_country = event.find(
            "{http://www.iwg-sem.org/}activationAffectedCountries"
        ).text

        event_xml_file = Path(event_xml_dir, event_id).with_suffix(".xml")
        if not event_xml_file.is_file():
            logger.info("\tPulling {} GeoRSS: {}...".format(event_id, event_xml_file))
            urlretrieve(rss_url, event_xml_file)

        event_root = ET.parse(event_xml_file).getroot()

        for item in event_root.iter("item"):
            try:
                data_type = item.find("{http://www.gdacs.org/}cemsctype").text
            except AttributeError:
                data_type = ""
            try:
                product_type = item.find("{http://www.gdacs.org/}cemsptype").text
            except AttributeError:
                product_type = ""

            # Only care about downloading VECTOR data for Delineation product
            # More info at https://emergency.copernicus.eu/mapping/ems/rapid-mapping-portfolio
            if not (
                data_type == "VECTOR"
                and (product_type == "DEL" or product_type == "GRA")
            ):
                continue

            item_url = urlparse(item.find("link").text)
            _, _, product_id, version_id = item_url.path.lstrip("/").split("/")
            (
                product_event_id,
                aoi_id,
                product_type_id,
                monitoring_type,
                revision_id,
                data_type_id,
            ) = product_id.split("_")

            # Some sanity checks to ensure we've parsed our product id string correctly
            assert event_id == product_event_id
            assert product_type_id == product_type
            assert data_type_id == "VECTORS"

            georss_polygon = item.find("{http://www.georss.org/georss}polygon").text
            # Split string, group number pairs, convert to float and swap pairs to lon first
            polygon = Polygon(
                map(
                    lambda x: (float(x[1]), float(x[0])),
                    grouper(georss_polygon.split(" "), 2),
                )
            )

            event_product = EventProduct(
                # Rebuild product_id from scratch because we need to include version
                "_".join(
                    [
                        event_id,
                        aoi_id,
                        product_type_id,
                        monitoring_type,
                        revision_id,
                        version_id,
                        data_type_id,
                    ]
                ),
                event_id,
                event_country,
                aoi_id,
                event_datetime.timestamp(),
                polygon,
                data_type_id,
                product_type_id,
                monitoring_type,
                revision_id,
                version_id,
                urlunparse(item_url),
            )
            products.append(event_product)

    df = gpd.GeoDataFrame(products)
    geojson_file = "./data/cems-rapid-mapping-flood-products-2019-2020.geojson"
    logger.info("Writing GeoJSON of flood event products to {}".format(geojson_file))
    df.to_file(geojson_file, driver="GeoJSON")

    sentinel_session = get_session(sentinel_oauth_id, sentinel_oauth_secret)

    catalog = pystac.Catalog(
        "copernicus-rapid-mapping-floods-2019-2020",
        "Copernicus Rapid Mapping provisions geospatial information within hours or days from the activation in support of emergency management activities immediately following a disaster. Standardised mapping products are provided: e.g. to ascertain the situation before the event (reference product), to roughly identify and assess the most affected locations (first estimate product), assess the geographical extent of the event (delineation product) or to evaluate the intensity and scope of the damage resulting from the event (grading product). This catalog contains a subset of products for flood events from 2019-2020 that intersect with Sentinel 2 L2A Chips.",
        title="Copernicus Rapid Mapping Floods 2019-2020",
    )
    s2_collection = pystac.Collection(
        "Sentinel-2-L2A",
        "Sentinel 2 L2A images corresponding to CEMS rapid mapping floods",
        pystac.Extent(
            pystac.SpatialExtent([None, None, None, None]),
            pystac.TemporalExtent(
                [
                    (
                        # TODO: Make this more specific by looping actual dts
                        #       after ingest
                        datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                        datetime(2020, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                    )
                ]
            ),
        ),
    )
    catalog.add_child(s2_collection)

    # Loop Products grouped by event id, lookup Sentinel 2 matches for each
    # Product, and create STAC Items in catalog for any matches
    sorted_products = sorted(products, key=lambda x: x.event_id)
    for event_id, event_products in groupby(sorted_products, key=lambda x: x.event_id):
        for p in event_products:
            event_datetime = datetime.fromtimestamp(p.event_time, tz=timezone.utc)

            # Check for sentinel 2 results before anything else, so we
            # don't do unnecessary work. We'll use these results later
            # after we've created our STAC Item
            response = stac_search(
                p.geometry.bounds,
                "sentinel-2-l2a",
                event_datetime - timedelta(hours=12),
                event_datetime + timedelta(hours=12),
                sentinel_session,
            ).json()

            if len(response["features"]) < 1:
                logger.debug("No Sentinel 2 results for {}".format(p.product_id))
                continue

            event_collection = catalog.get_child(event_id)
            if event_collection is None:
                event_collection = pystac.Collection(
                    event_id,
                    "",
                    pystac.Extent(
                        pystac.SpatialExtent([None, None, None, None]),
                        pystac.TemporalExtent([(event_datetime, None)]),
                    ),
                )
                catalog.add_child(event_collection)

            pystac_item = pystac.Item(
                p.product_id,
                mapping(p.geometry),
                p.geometry.bounds,
                event_datetime,
                properties={
                    "aoi_id": p.aoi_id,
                    "country": p.event_country,
                    "event_id": p.event_id,
                    "product_type": p.product_type,
                    "data_type": p.data_type,
                    "monitoring_type": p.monitoring_type,
                    "revision": p.revision,
                    "version": p.version,
                },
            )
            event_collection.add_item(pystac_item)
            url_link = pystac.Link("alternate", p.product_link, media_type="text/html")
            pystac_item.add_link(url_link)

            # Get or create Item in S2 collection for each match from
            # SentinelHub and add as links to our Product Item
            for feature in response["features"]:
                s2_item = s2_collection.get_item(feature["id"])
                if s2_item is None:
                    s2_item = pystac.Item.from_dict(feature)
                    s2_collection.add_item(s2_item)

                s2_link = pystac.Link(
                    "data", s2_item, link_type=pystac.LinkType.RELATIVE
                ).set_owner(pystac_item)
                pystac_item.add_link(s2_link)

            logger.info(
                "Created STAC Item {} with {} Sentinel 2 links".format(
                    p.product_id, len(response["features"])
                )
            )

    # Set spatial extents
    for collection in catalog.get_children():
        if not isinstance(collection, pystac.Collection):
            continue
        bounds = GeometryCollection(
            [shape(s.geometry) for s in collection.get_all_items()]
        ).bounds
        collection.extent.spatial = pystac.SpatialExtent(bounds)

    catalog_root = "./data/catalog"
    logger.info("Writing STAC Catalog to {}...".format(catalog_root))
    catalog.normalize_and_save(catalog_root, pystac.CatalogType.SELF_CONTAINED)


if __name__ == "__main__":
    main()
