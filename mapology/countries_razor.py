"""Occam's razor for countries data set of the natural earth project."""

import copy
import json
import logging
import os
import pathlib
import sys
from typing import List, Union, no_type_check

ENCODING = 'utf-8'

APP_ALIAS = 'mapology'
APP_ENV = APP_ALIAS.upper()
DEBUG = bool(os.getenv(f'{APP_ENV}_DEBUG', ''))
log = logging.getLogger()  # Temporary refactoring: module level logger
LOG_FOLDER = pathlib.Path('logs')
LOG_FILE = f'{APP_ALIAS}.log'
LOG_PATH = pathlib.Path(LOG_FOLDER, LOG_FILE) if LOG_FOLDER.is_dir() else pathlib.Path(LOG_FILE)
LOG_LEVEL = logging.INFO


@no_type_check
def init_logger(name=None, level=None):
    """Initialize module level logger"""
    global log  # pylint: disable=global-statement

    log_format = {
        'format': '%(asctime)s.%(msecs)03d %(levelname)s [%(name)s]: %(message)s',
        'datefmt': '%Y-%m-%dT%H:%M:%S',
        # 'filename': LOG_PATH,
        'level': LOG_LEVEL if level is None else level,
    }
    logging.basicConfig(**log_format)
    log = logging.getLogger(APP_ENV if name is None else name)
    log.propagate = True


init_logger(name=APP_ENV, level=logging.DEBUG if DEBUG else None)

COUNTRY_STORE = pathlib.Path('country-store.json')
COUNTRY_GEOJSON_FRAME = {
    'type': 'FeatureCollection',
    'name': 'ne_110m_ad_0_ctrs',
    'crs': {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}},
    'features': [],
}

KEPT_PROPS = (
    'featurecla',
    'TYPE',
    'ADMIN',
    'NAME',
    'NAME_LONG',
    'ABBREV',
    'FORMAL_EN',
    'NAME_SORT',
    'POP_EST',
    'POP_YEAR',
    'GDP_MD',
    'GDP_YEAR',
    'ECONOMY',
    'INCOME_GRP',
    'ISO_A2_EH',
    'ISO_A3_EH',
    'ISO_N3_EH',
    'CONTINENT',
    'REGION_UN',
    'SUBREGION',
    'WIKIDATAID',
    'NAME_DE',
    'NAME_EN',
    'NAME_ES',
    'NAME_FR',
    'NAME_IT',
)


def main(argv: Union[List[str], None] = None) -> int:
    """Drive the shaving."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print('usage: mapology shave countries-to-be-shaved-geo.json-file')
        return 2

    rococo_path = argv[0]
    log.info('Shaving country level data of %s' % rococo_path)
    country_store = copy.deepcopy(COUNTRY_GEOJSON_FRAME)
    with open(rococo_path, 'rt', encoding=ENCODING) as handle:
        rococo = json.load(handle)

    log.info('Loaded %d countries' % len(rococo['features']))
    for feature_complete in rococo['features']:
        feature = copy.deepcopy(feature_complete)
        kept_props = {k: v for k, v in feature['properties'].items() if k in KEPT_PROPS}
        feature['properties'] = kept_props
        country_store['features'].append(feature)  # type: ignore

    with open(COUNTRY_STORE, 'wt', encoding=ENCODING) as handle:
        json.dump(country_store, handle, indent=1)

    log.info('Wrote shaved country level data to conuntry store at %s' % COUNTRY_STORE)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
