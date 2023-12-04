import pynvim

from progirl.path import validate_path
from progirl.path import resolve_path_with_context
from progirl.uri import URI
from progirl.globals import config

from .utils import get_current_collection


def resolve_uri_as_path(
        vim: pynvim.Nvim,
        uri: URI,
        context_pwd: str | None = None
) -> str | None:
    if (uri.protocol != "") and (uri.protocol
                                 not in config.collections.keys()):
        return None

    if uri.protocol == "":
        collection = get_current_collection(vim, check_cb=True)
    else:
        collection = config.collections[uri.protocol]

    c_notes_path = collection.notes_path
    path_str = resolve_path_with_context(
            uri.body, context_pwd=context_pwd, context_root=c_notes_path
    )

    return validate_path(path_str)
