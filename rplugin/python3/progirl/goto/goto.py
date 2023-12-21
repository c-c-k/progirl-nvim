from enum import auto
from enum import Enum

import pynvim

from progirl.goto.handle import handle_uri
from progirl.goto.resolve import resolve_uri_as_path
from progirl.markdown import get_uri_at_cursor
from progirl.path import get_context_pwd
from progirl.path import touch_with_mkdir
from progirl.uri import URI


class _GotoMethod(Enum):
    EDIT = auto()
    EX = auto()


def _edit_file_at_uri(vim: pynvim.Nvim, uri: URI, context_pwd: str | None):
    path_str = resolve_uri_as_path(vim, uri, context_pwd=context_pwd)
    if path_str is None:
        vim.api.echo([[f"'{uri!s}' not found"]], True, {})
        return
    path_str = touch_with_mkdir(path_str)
    if path_str is None:
        vim.api.echo([[f"'can't create {uri!s}'",]], True, {})
        return
    command = f"edit {path_str}"
    vim.command(command)


def _ex_uri(vim: pynvim.Nvim, uri: URI, context_pwd: str | None):
    # The logic here is meant to potentially deal with a URI like
    # e.g. "print:pkb-notes:/note_to_print"
    if uri.protocol == "":
        path_str = resolve_uri_as_path(vim, uri, context_pwd=context_pwd)
    else:
        nested_uri = URI(uri.body)
        if nested_uri.protocol == "":
            path_str = resolve_uri_as_path(vim, uri, context_pwd)
            if path_str is None:
                path_str = resolve_uri_as_path(vim, nested_uri, context_pwd)
        else:
            path_str = resolve_uri_as_path(vim, nested_uri, context_pwd)

    if path_str is not None:
        uri.body = path_str

    handle_uri(vim, uri)


def _goto_uri(vim: pynvim.Nvim, goto_method: _GotoMethod):
    uri_string = get_uri_at_cursor(vim)
    if uri_string is None:
        vim.api.echo([["No URI/file under cursor"]], True, {})
        return

    uri = URI(uri_string)
    # raise Exception(str((uri, str(type(uri)))))
    context_dir = get_context_pwd()

    if goto_method is _GotoMethod.EX:
        _ex_uri(vim, uri, context_dir)
    else:
        _edit_file_at_uri(vim, uri, context_dir)


def goto_file_at_cursor(vim: pynvim.Nvim):
    _goto_uri(vim, goto_method=_GotoMethod.EDIT)


def goto_ex_at_cursor(vim: pynvim.Nvim):
    _goto_uri(vim, goto_method=_GotoMethod.EX)
