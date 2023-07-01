"""Render the prefix page apps from the prefix abd prefix table stores."""
import collections
import copy
import datetime as dti
import json
import operator
import os
import pathlib
import sys
from typing import List, Union

import mapology.country as cc
import mapology.db as db
import mapology.hull as hull
import mapology.template_loader as template
from mapology import BASE_URL, DEBUG, ENCODING, FOOTER_HTML, FS_PREFIX_PATH, LIB_PATH, PATH_NAV, country_blurb, log

THIS_YY_INT = int(dti.datetime.utcnow().strftime('%y'))

HTML_TEMPLATE = os.getenv('GEO_PREFIX_HTML_TEMPLATE', '')
HTML_TEMPLATE_IS_EXTERNAL = bool(HTML_TEMPLATE)
if not HTML_TEMPLATE:
    HTML_TEMPLATE = 'prefix_page_template.html'

AIRP = 'airport'
RUNW = 'runways'
FREQ = 'frequencies'
LOCA = 'localizers'
GLID = 'glideslopes'

CC_HINT = 'CC_HINT'
City = 'City'
CITY = City.upper()
ICAO = 'ICAO'
IC_PREFIX = 'IC_PREFIX'
IC_PREFIX_ICAO = f'{IC_PREFIX}_{ICAO}'
ITEM = 'ITEM'
KIND = 'KIND'
PATH = '/PATH'
BASE_URL_TARGET = 'BASE_URL'
ANCHOR = 'ANCHOR'
TEXT = 'TEXT'
URL = 'URL'
ZOOM = 'ZOOM'
DEFAULT_ZOOM = 4
FOOTER_HTML_KEY = 'FOOTER_HTML'
LIB_PATH_KEY = 'LIB_PATH'

icao = 'icao_lower'
LAT_LON = 'LAT_LON'
cc_page = 'cc_page'
Cc_page = 'Cc_page'

ATTRIBUTION = f'{KIND} {ITEM} of '

Point = collections.namedtuple('Point', ['label', 'lat', 'lon'])

# GOOGLE_MAPS_URL = f'https://www.google.com/maps/search/?api=1&query={{lat}}%2c{{lon}}'  # Map + pin Documented
GOOGLE_MAPS_URL = 'https://maps.google.com/maps?t=k&q=loc:{lat}+{lon}'  # Sat + pin Undocumented

REGION_COUNTRY_DATA = {
    'region': '',
    'url': '',
    'country': '',
}


def main(argv: Union[List[str], None] = None) -> int:
    """Drive the prefix renderings."""
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print('usage: mapology prefix')
        return 2

    store_index = db.load_index('store')
    table_index = db.load_index('table')
    hulls_index = db.load_index('hulls')
    region_country_index = db.load_index('region_country')

    prefix_hull_store = copy.deepcopy(hull.THE_HULLS)
    slash = '/'
    prefixes = sorted(store_index.keys())
    num_prefixes = len(prefixes)
    many = num_prefixes > 10  # tenfold magic
    numbers = ('latitude', 'longitude', 'elevation')
    for current, prefix in enumerate(sorted(prefixes), start=1):
        with open(store_index[prefix], 'rt', encoding=ENCODING) as handle:
            prefix_store = json.load(handle)

        with open(table_index[prefix], 'rt', encoding=ENCODING) as handle:
            table_store = json.load(handle)

        hulls_index[prefix] = db.hull_path(prefix)  # noqa

        region_name = table_store['name']
        cc_hint = cc.FROM_ICAO_PREFIX.get(prefix, 'No Country Entry Present')
        my_prefix_path = f'{FS_PREFIX_PATH}/{prefix}'

        region_country_index[prefix] = str(db.DB_FOLDER_PATHS['region_country'] / f'{prefix}.json')
        region_country_data = copy.deepcopy(REGION_COUNTRY_DATA)
        region_country_data['region'] = prefix
        region_country_data['url'] = f'{BASE_URL}/{FS_PREFIX_PATH}/{prefix}/'
        region_country_data['country'] = f'{cc_hint}'
        with open(region_country_index[prefix], 'wt', encoding=ENCODING) as handle:
            json.dump(region_country_data, handle, indent=2)
        log.info(str(region_country_data))

        airports = sorted(table_store['airports'], key=operator.itemgetter('icao'))

        message = f'processing {current :>3d}/{num_prefixes} {prefix} --> ({region_name}) ...'
        if not many or not current % 10 or current == num_prefixes:
            log.info(message)

        if DEBUG:
            log.debug('%s - %s' % (prefix, region_name))
        data_rows = []
        trial_coords = []
        for airport in airports:
            trial_coords.append((airport['latitude'], airport['longitude']))
            row = [str(cell) if key not in numbers else f'{round(cell, 3) :7.03f}' for key, cell in airport.items()]
            # monkey patching
            # ensure cycles are state with two digits zero left padded
            year, cyc = row[6].split(slash)
            row[6] = f'{year}/{int(cyc) :02d}'
            # create a link to the airport page on the ICAO cell of the airport in the table row
            # example: '<a href="AGAT/" class="nd" title="AGAT(Atoifi, Solomon Islands)">AGAT</a>'
            an_icao = row[2]
            a_name = row[8]
            row[2] = f'<a href="{an_icao}/" class="nd" title="{a_name}">{an_icao}</a>'
            if DEBUG:
                log.info('- | %s |' % (' | '.join(row)))
            data_rows.append(
                f'<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td>'
                f'<td class="ra">{row[3]}</td><td class="ra">{row[4]}</td><td class="ra">{row[5]}</td>'
                f'<td class="la">{row[6]}</td><td class="ra">{row[7]}</td>'
                f'<td class="la">{row[8]}</td></tr>'
            )

        prefix_hull = hull.extract_prefix_hull(prefix, region_name, trial_coords)
        hull.update_hull_store(prefix_hull_store, prefix_hull)

        min_lat, min_lon = 90, 180
        max_lat, max_lon = -90, -180
        ra_count = 0  # region_airports_count
        cc_count = 1  # HACK A DID ACK TODO: do not fix country count to wun
        for airport in airports:
            ra_count += 1
            # name has eg. "<a href='KLGA/' target='_blank' title='KLGA(La Guardia, New York, USA)'>KLGA</a>"
            # name_mix = airport['name']
            # name_mix has eg. "KLGA(La Guardia, New York, USA)'>KLGA</a>" LATER TODO
            # code, rest = name_mix.split('(', 1)
            # name = rest.split(')', 1)[0]
            # coords = airport["geometry"]["coordinates"]
            lon, lat = airport['longitude'], airport['latitude']
            min_lat = min(min_lat, lat)
            min_lon = min(min_lon, lon)
            max_lat = max(max_lat, lat)
            max_lon = max(max_lon, lon)

        prefix_lat = 0.5 * (max_lat + min_lat)
        prefix_lon = 0.5 * (max_lon + min_lon)
        bbox_disp = f'[({", ".join(f"{round(v, 3) :7.03f}" for v in (min_lat, min_lon,max_lat, max_lon))}]'
        log.debug('Identified bounding box lat, lon in %s for prefix %s' % (bbox_disp, prefix))
        log.debug(('Set center of prefix map to lat, lon = (%f, %f) for prefix %s' % (prefix_lat, prefix_lon, prefix)))
        prefix_root = pathlib.Path(FS_PREFIX_PATH)
        map_folder = pathlib.Path(prefix_root, prefix)
        map_folder.mkdir(parents=True, exist_ok=True)
        geojson_path = str(pathlib.Path(map_folder, f'{prefix.lower()}-geo.json'))
        with open(geojson_path, 'wt', encoding=ENCODING) as geojson_handle:
            json.dump(prefix_store, geojson_handle, indent=2)

        html_dict = {
            ANCHOR: f'prefix/{prefix}/',
            CC_HINT: cc_hint,
            cc_page: country_blurb(cc_hint),
            Cc_page: country_blurb(cc_hint).title(),
            LAT_LON: f'{prefix_lat},{prefix_lon}',
            LIB_PATH_KEY: LIB_PATH,
            PATH: PATH_NAV,
            BASE_URL_TARGET: BASE_URL,
            ZOOM: str(DEFAULT_ZOOM),
            IC_PREFIX: prefix,
            'IrealCAO': ICAO,
            'ic_prefix_lower-geo.json': f'{prefix.lower()}-geo.json',
            'REGION_AIRPORT_COUNT_DISPLAY': f'{ra_count} airport{"" if ra_count == 1 else "s"}',
            'COUNTRY_COUNT_DISPLAY': f'{cc_count} region{"" if cc_count == 1 else "s"}',
            'BBOX': f' contained in lat, lon bounding box {bbox_disp}',
            FOOTER_HTML_KEY: FOOTER_HTML,
            'DATA_ROWS': '\n'.join(data_rows) + '\n',
        }
        html_page = template.load_html(HTML_TEMPLATE, HTML_TEMPLATE_IS_EXTERNAL)
        for key, replacement in html_dict.items():
            html_page = html_page.replace(key, replacement)

        html_path = pathlib.Path(my_prefix_path, 'index.html')
        with open(html_path, 'wt', encoding=ENCODING) as html_handle:
            html_handle.write(html_page)

        with open(hulls_index[prefix], 'wt', encoding=ENCODING) as handle:
            json.dump(prefix_hull, handle, indent=2)

    db.dump_index('hulls', hulls_index)

    with open(pathlib.Path(FS_PREFIX_PATH) / 'region-hulls-geo.json', 'wt', encoding=ENCODING) as handle:
        json.dump(prefix_hull_store, handle, indent=2)

    db.dump_index('region_country', region_country_index)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
