from importlib import import_module

import pynvim

from progirl.path import validate_path
from progirl.path import resolve_path_with_context
from progirl.uri import URI

DEFAULT_RESOLVER_PROTOCOLS: list[str] = ["file", "local", ""]


def default_resolver(uri: URI, context_pwd: str | None) -> str | None:
    if uri.protocol in DEFAULT_RESOLVER_PROTOCOLS:
        path = resolve_path_with_context(uri.body, context_pwd)
        return validate_path(path)
    return None


def try_resolve(
        vim: pynvim.Nvim, resolver: str, uri: URI, context_pwd: str | None
) -> str | None:
    resolver_module_name, resolver_function_name = \
            resolver.rsplit(".", maxsplit=1)
    resolver_module = import_module(resolver_module_name)
    resolver_function = getattr(resolver_module, resolver_function_name)
    return resolver_function(vim, uri, context_pwd)


def resolve_uri_as_path(
        vim: pynvim.Nvim,
        uri: URI,
        context_pwd: str | None = None
) -> str | None:
    path = None
    uri_resolvers = vim.vars.get("progirl_uri_resolvers", [])
    for resolver in uri_resolvers:
        path = try_resolve(vim, resolver, uri, context_pwd)
        if path is not None:
            break
    if path is None:
        path = default_resolver(uri, context_pwd)
    return path
