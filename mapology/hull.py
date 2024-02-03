"""Determine hull curves from point sets."""

import copy
import functools
from typing import no_type_check

from mapology import log

THE_HULLS = {
    'type': 'FeatureCollection',
    'name': 'Prefix Region Convex Hulls',
    'crs': {
        'type': 'name',
        'properties': {
            'name': 'urn:ogc:def:crs:OGC:1.3:CRS84',
        },
    },
    'features': [],
}
HULL_TEMPLATE = {
    'type': 'Feature',
    'id': '',
    'properties': {'name': ''},
    'geometry': {'type': 'Polygon', 'coordinates': []},
}


@no_type_check
def convex(coords):
    """Executes scan to return points in counter-clockwise order that are on the convex hull (Graham)."""
    turn_left, turn_right, turn_none = 1, -1, 0  # noqa

    def compare(a, b):
        return float(a > b) - float(a < b)

    def turn(p, q, r):
        return compare((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]), 0)

    def keep_left(hull, r):
        while len(hull) > 1 and turn(hull[-2], hull[-1], r) != turn_left:
            hull.pop()
        if not len(hull) or hull[-1] != r:
            hull.append(r)
        return hull

    points = sorted(coords)
    lower_hull = functools.reduce(keep_left, points, [])
    upper_hull = functools.reduce(keep_left, reversed(points), [])
    return lower_hull.extend(upper_hull[i] for i in range(1, len(upper_hull) - 1)) or lower_hull


@no_type_check
def extract_prefix_hull(prefix, region_name, coords):
    prefix_hull = copy.deepcopy(HULL_TEMPLATE)
    prefix_hull['id'] = prefix
    prefix_hull['properties']['name'] = region_name

    hull_coords = [[lon, lat] for lat, lon in convex(coords)]

    lon_min = min(lon for lon, _ in hull_coords)
    lon_max = max(lon for lon, _ in hull_coords)
    if lon_min < -120 and +120 < lon_max:
        log.info('Problematic region found (convex hull crossing the outer sign change of longitudes): %s' % prefix)
        lon_sign = tuple(+1 if lon > 0 else -1 for lon, _ in hull_coords)
        lon_neg_count = sum(-datum for datum in lon_sign if datum < 0)
        lon_pos_count = sum(datum for datum in lon_sign if datum > 0)
        if lon_pos_count and lon_neg_count:  # Does the polygon cross the longitude sign change?
            log.info('- (%d positive / %d negative) longitudes: %s' % (lon_pos_count, lon_neg_count, prefix))
            patch_me_up = lon_neg_count > lon_pos_count
            add_me = +360 if patch_me_up else -360
            if patch_me_up:
                log.info('- patching upwards (adding 360 degrees to longitude where negative): %s' % prefix)
                hull_coords = [[lon + add_me, lat] if lon < 0 else [lon, lat] for lon, lat in hull_coords]
            else:
                log.info('- patching downwards (adding 360 degrees to longitude where positive): %s' % prefix)
                hull_coords = [[lon + add_me, lat] if lon > 0 else [lon, lat] for lon, lat in hull_coords]

    if prefix == 'ET':
        log.info('Patching a North-Eastern ear onto the hull: %s' % prefix)

        @no_type_check
        def et_earify(pair):
            """Monkey patch the ET region to offer an ear to select outside of ED."""
            lon_ne = 12.27  # 9333333333334,
            lat_ne = 53.91  # 8166666666664
            magic_lon = 13.648875
            magic_lat = 54.551359
            lon, lat = pair
            return [magic_lon, magic_lat] if lon > lon_ne and lat > lat_ne else [lon, lat]

        hull_coords = [et_earify(pair) for pair in hull_coords]

    # problem regions A1, NZ, NF, PA, UH,
    prefix_hull['geometry']['coordinates'].append(hull_coords)
    return prefix_hull


@no_type_check
def update_hull_store(hull_store, prefix_hull):
    """DRY."""
    hull_store['features'].append(copy.deepcopy(prefix_hull))
