from copy import deepcopy
import re

import pynvim

from pkbm.globals import config
from pkbm.path import resolve_path_with_context
from pkbm.utils import AttrDict
from .exceptions import CollectionError

_DEFAULT_COLLECTION = {
        "name": "default",
        "path": "~/pkb/default",
        "use_path_as_root": True,
        "notes_path": "/notes",
        "extension": ".md",
        "filename_template": "%s-${TITLE_CLEAN}${EXTENSION}",
        "templates_path": "/templates",
        "default_template": "/templates/note.tpl",
}
_CONTEXTED_PATH_KEYS = [
        "notes_path", "templates_path", "default_template"
]
_PATTERN_VALID_COLLECTION_NAME = re.compile(r"[a-z0-9_]+")


def load_config(vim: pynvim.Nvim):
    config.clear()

    config.pkb_prefix = vim.vars.get("pkbm_pkb_prefix", "pkb-")
    load_collections_config(vim)

    return config


def load_c_config(raw_collection: dict) -> AttrDict:
    collection = AttrDict(deepcopy(_DEFAULT_COLLECTION))
    collection.update(raw_collection)

    collection._id = get_c_id(collection)

    path = resolve_path_with_context(collection.path, real=True)
    collection.path = path

    if collection.use_path_as_root:
        context_pwd = None
        context_root = path
    else:
        context_pwd = path
        context_root = None

    for key in _CONTEXTED_PATH_KEYS:
        collection[key] = resolve_path_with_context(
                collection[key],
                context_pwd=context_pwd,
                context_root=context_root,
                real=True
        )

    return collection


def set_active_c_id(c_name: str):
    collections = config.collections
    active_c_id = None

    if c_name in collections.keys():
        active_c_id = c_name
    else:
        for collecion in collections.values():
            if collecion.name == c_name:
                active_c_id = collecion._id
                break

    if active_c_id is None:
        raise CollectionError(f"collection not found: {c_name}")

    config.active_c_id = active_c_id


def get_c_id(collection: AttrDict) -> str:
    if "_id" in collection.keys():
        return collection._id

    c_name = collection.name
    if not _PATTERN_VALID_COLLECTION_NAME.match(c_name):
        raise CollectionError(
                f"Invalid collection name '{c_name}', "
                "collenction name must match '[a-z0-9_]+'"
        )

    return config.pkb_prefix + c_name


def load_collections_config(vim: pynvim.Nvim):
    collections_list = vim.vars.get("pkbm_collections", [])

    if collections_list != []:
        collections = {
                collection._id: collection
                for collection in (
                        load_c_config(raw_collection)
                        for raw_collection in collections_list
                )
        }
        active_c_name = collections_list[0]["name"]
    else:
        default_collection = load_c_config({})
        collections = {default_collection._id: default_collection}
        active_c_name = default_collection["name"]

    config.collections = AttrDict(collections)
    set_active_c_id(active_c_name)
