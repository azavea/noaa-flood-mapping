from geopandas import GeoDataFrame
from pandas import Series
from shapely.geometry import shape


def pystac_item_to_series(item):
    """ Convert pystac.Item to pandas.Series """
    item_dict = item.to_dict()
    item_id = item_dict["id"]

    # Convert geojson geom into shapely.Geometry
    item_dict["geometry"] = shape(item_dict["geometry"])

    return Series(item_dict, name=item_id)


def pystac_catalog_to_dataframe(catalog, crs="EPSG:4326"):
    series = [pystac_item_to_series(item) for item in catalog.get_all_items()]
    return GeoDataFrame(series, crs=crs)
