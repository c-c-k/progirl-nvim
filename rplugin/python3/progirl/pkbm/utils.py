import os
from pathlib import Path
from time import sleep

import pynvim

from progirl.globals import config
from progirl.path import resolve_path_with_context
from progirl.pkbm.exceptions import CollectionError
from progirl.utils import AttrDict


def get_collection_auto_id(c_id: str) -> str:
    collection = get_collection_by_c_id(c_id)
    c_path = Path(collection.path)
    id_file_path = c_path.joinpath(".pkb/next_id")
    return _get_auto_id(id_file_path)


def get_dir_auto_id(dir_path_str: str) -> str:
    dir_path = Path(dir_path_str)
    id_file_path = dir_path.joinpath(".next_id")
    return _get_auto_id(id_file_path)


def _get_auto_id(id_file_path: Path) -> str:
    id_temp_file_path = Path(id_file_path.as_posix() + "~")

    if not id_file_path.exists() and not id_temp_file_path.exists():
        id_file_path.parent.mkdir(exist_ok=True, parents=True)
        id_file_path.write_text("0")

    for tries in range(10):
        try:
            id_file_path.rename(id_temp_file_path)
        except FileNotFoundError:
            sleep(0.01)
            continue
        break
    else:
        raise OSError(f"can't access {id_file_path!s} to get auto id")

    auto_id = id_temp_file_path.read_text().strip()
    next_id = str(hex(int(auto_id, 16) + 1)[2:])
    id_temp_file_path.write_text(next_id)
    id_temp_file_path.rename(id_file_path)

    return f"{auto_id:>04}"


def get_collection_by_c_id(c_id: str) -> AttrDict:
    collection = config.collections.get(c_id)
    if collection is None:
        raise CollectionError(f"Non-existent collection id: {c_id}")

    return collection


def get_c_id_by_path(path_str: str) -> str | None:
    for collection in config.collections.values():
        c_path = collection.path
        if path_str.startswith(c_path):
            c_id = collection._id
            break
    else:
        c_id = None

    return c_id


def get_collection_by_path(path_str: str) -> AttrDict | None:
    c_id = get_c_id_by_path(path_str)
    collection = get_collection_by_c_id(c_id) if c_id is not None else None

    return collection


def get_current_c_id(vim: pynvim.Nvim, check_cb=False, check_pwd=False) -> str:
    c_id = None

    if check_cb:
        buffer = vim.current.buffer
        path_str = resolve_path_with_context(buffer.name, real=True)
        c_id = get_c_id_by_path(path_str)

    if (c_id is None) and check_pwd:
        path_str = os.getcwd()
        c_id = get_c_id_by_path(path_str)

    if c_id is None:
        c_id = config.active_c_id

    return c_id


def get_current_collection(
        vim: pynvim.Nvim, check_cb=False, check_pwd=False
) -> AttrDict:
    c_id = get_current_c_id(vim, check_cb, check_pwd)
    collection = get_collection_by_c_id(c_id)

    return collection
