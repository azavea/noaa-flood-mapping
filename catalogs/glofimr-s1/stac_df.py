from geopandas import GeoDataFrame
from pandas import Series
import pystac
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry


STAC_ITEM_FIELDS = set([
    'id',
    'assets',
    'bbox',
    'collection',
    'geometry',
    'links',
    'stac_extensions',
    'stac_version',
    'type',
])


def series_to_pystac_item(series):
    """ Convert pandas.Series to pystac.Item """
    columns = set(series.index.tolist())
    if not STAC_ITEM_FIELDS < columns:
        raise ValueError("geo_dataframe does not contain STAC Items: {}".format(STAC_ITEM_FIELDS - columns))
    item_dict = {
        key: value
        if not isinstance(value, BaseGeometry) else mapping(value)
        for key, value in series.loc[columns].items()
    }

    return pystac.Item.from_dict(item_dict)


def pystac_item_to_series(item):
    """ Convert pystac.Item to pandas.Series """
    item_dict = item.to_dict()
    item_id = item_dict['id']

    # Convert geojson geom into shapely.Geometry
    item_dict['geometry'] = shape(item_dict['geometry'])

    return Series(item_dict, name=item_id)


def pystac_catalog_to_dataframe(catalog, crs="EPSG:4326"):
    series = [pystac_item_to_series(item) for item in catalog.get_all_items()]
    return GeoDataFrame(series, crs=crs)


def pystac_catalog_add_dataframe(catalog, dataframe):
    """ Add Items in dataframe to catalog: pystac.Catalog """
    items = [series_to_pystac_item(series) for _, series in dataframe.iterrows()]
    catalog.add_items(items)
