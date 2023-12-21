import os.path as osp
from pathlib import Path
import re
from typing import Pattern

from pynvim.api import Buffer

VALID_PATH_PATTERN: Pattern = re.compile(r"^[\w./-]+$")


def get_context_pwd(
        buffer: Buffer = None, allow_pwd_context=False
) -> str | None:
    context_pwd = None
    if buffer is not None:
        if ((buffer.options["buftype"] == "") and (buffer.name != "")):
            context_pwd = str(Path(buffer.name).parent.resolve())
    if allow_pwd_context and (context_pwd is None):
        context_pwd = str(Path.cwd())
    return context_pwd


def expand_path(path_str: str) -> str:
    return osp.expanduser(osp.expandvars(path_str))


def norm_expand_path(path_str: str) -> str:
    return osp.normpath(osp.expanduser(osp.expandvars(path_str)))


def resolve_path_with_context(
        path_str: str,
        context_pwd: str | None = None,
        context_root: str | None = None,
        real=True
) -> str:
    path_str = norm_expand_path(path_str)
    if osp.isabs(path_str) and (context_root is not None):
        context_root = norm_expand_path(context_root)
        path_str = osp.join(context_root, path_str.lstrip("/"))
    elif not osp.isabs(path_str) and (context_pwd is not None):
        context_pwd = norm_expand_path(context_pwd)
        path_str = osp.join(context_pwd, path_str)
    path_str = osp.abspath(path_str)
    if real:
        path_str = osp.realpath(path_str)
    return path_str


def is_valid_path(path_str: str) -> bool:
    return osp.exists(path_str) or bool(VALID_PATH_PATTERN.match(path_str))


def validate_path(path_str: str) -> str | None:
    return osp.realpath(path_str) if is_valid_path(path_str) else None


def touch_with_mkdir(path_str: str) -> str | None:
    path = Path(path_str)
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        except OSError:
            path_str = None  # type: ignore
    return path_str
