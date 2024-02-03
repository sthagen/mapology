"""Loader function for templates."""

import importlib.resources
import pathlib
from typing import List, Union

ENCODING = 'utf-8'
RESOURCES = (
    'airport_page_template.html',
    'country_index_template.html',
    'country_page_template.html',
    'ndb_index_template.html',
    'prefix_index_template.html',
    'prefix_page_template.html',
    'search_index_template.html',
)


def load_html(resource: str, is_complete_path: bool = False) -> str:
    """Load the template either from the package resources or an external path."""
    if is_complete_path:
        with open(resource, 'rt', encoding=ENCODING) as handle:
            return handle.read()
    else:
        with importlib.resources.path(__package__, resource) as html_template_path:
            with open(html_template_path, 'rt', encoding=ENCODING) as handle:
                return handle.read()


def eject(argv: Union[List[str], None] = None) -> int:
    """Eject the templates into the folder given (default EJECTED) and create the folder if it does not exist."""
    argv = argv if argv else ['']
    into = argv[0]
    if not into.strip():
        into = 'EJECTED'
    into_path = pathlib.Path(into)
    into_path.mkdir(parents=True, exist_ok=True)
    for resource in RESOURCES:
        write_to = into_path / resource
        with importlib.resources.path(__package__, resource) as html_template_path:
            with open(html_template_path, 'rt', encoding=ENCODING) as handle:
                with open(write_to, 'wt', encoding=ENCODING) as target:
                    target.write(handle.read())

    return 0
