from __future__ import annotations

from enum import auto
from enum import Enum
import re
from typing import NamedTuple
from typing import Pattern

import pynvim
from pynvim.api import Buffer

from progirl.buffer import ProGirlBuffer


class LinksError(Exception):
    pass


class LinkRefType(Enum):
    NON_REF = auto()
    REF_SOURCE = auto()
    REF_TARGET = auto()


class LinkPattern(NamedTuple):
    pattern: Pattern
    ref_type: LinkRefType
    target_group: str
    name_group: str | None
    full_line_link: bool = False


class Link:
    ref_type: LinkRefType
    target: str
    name: str
    start: int
    end: int

    def __init__(
            self,
            link_match: re.Match | None = None,
            link_pattern: LinkPattern | None = None,
            ref_source: Link | None = None,
            ref_target: str | None = None
    ):
        if (link_match is not None) and (link_pattern is not None):
            self._init_from_match(link_match, link_pattern)
        elif ref_source is not None and ref_target is not None:
            self._init_from_ref(ref_source, ref_target)
        else:
            raise ValueError(
                    "Link must be initated with either "
                    "link_match & link_pattern or ref_source & ref_target"
            )

    def _init_from_match(
            self, link_match: re.Match, link_pattern: LinkPattern
    ):
        self.ref_type = link_pattern.ref_type
        self.target = link_match.group(link_pattern.target_group)
        self.name = (
                link_match.group(link_pattern.name_group)
                if link_pattern.name_group is not None else ""
        )
        self.start = link_match.start()
        self.end = link_match.end()

    def _init_from_ref(self, ref_source: Link, ref_target: str):
        self.ref_type = LinkRefType.NON_REF
        self.target = ref_target
        self.name = ref_source.name
        self.start = ref_source.start
        self.end = ref_source.end

    def __len__(self):
        return self.end - self.start


_INVALID_LINK_DESCRIPTION_CHARS = "[]"
_LINK_PATTERNS: list[LinkPattern] = [
        # ref_target link ("^[name]: target")
        LinkPattern(
                pattern=re.compile(r"^\[(?P<name>[^]]+)\]: (?P<target>.*)"),
                ref_type=LinkRefType.REF_TARGET,
                target_group="target",
                name_group="name",
                full_line_link=True
        ),
        # normal link ("[name](target)")
        LinkPattern(
                pattern=re
                .compile(r"\[(?P<name>[^]]+)\]\((?P<target>[^)]*)\)"),
                ref_type=LinkRefType.NON_REF,
                target_group="target",
                name_group="name"
        ),
        # ref_source link ("[name][target]")
        LinkPattern(
                pattern=re
                .compile(r"\[(?P<name>[^]]+)\]\[(?P<target>[^]]*)\]"),
                ref_type=LinkRefType.REF_SOURCE,
                target_group="target",
                name_group="name"
        ),
        # name only ref_source link ("[name]")
        LinkPattern(
                pattern=re.compile(r"\[(?P<name>\d+|[^]]{2,})\]"),
                ref_type=LinkRefType.REF_SOURCE,
                target_group="name",
                name_group="name"
        ),
        # chevron http link ("<http[s]://...>")
        LinkPattern(
                pattern=re.compile(r"<(?P<target>https?://[^>]+)>"),
                ref_type=LinkRefType.NON_REF,
                target_group="target",
                name_group=None
        ),
        # simple http link ("http[s]://...")
        LinkPattern(
                pattern=re.compile(r"\b(?P<target>https?://\S+)"),
                ref_type=LinkRefType.NON_REF,
                target_group="target",
                name_group=None
        ),
]


def _find_link(line: str,
               link_patterns: list[LinkPattern]) -> tuple[Link | None, bool]:
    link = None
    for link_pattern in link_patterns:
        link_match = link_pattern.pattern.search(line)
        if link_match is not None:
            link = Link(link_match, link_pattern)
            break
    return link, link_pattern.full_line_link


def _replace_link_with_blanks(line: str, link: Link) -> str:
    new_line = line[:link.start] + ' ' * len(link)
    if link.end < len(line):
        new_line += line[link.end:]
    return new_line


def _extract_links_from_line(line: str) -> list[Link]:
    links = []
    while True:
        link, full_line_link_found = _find_link(line, _LINK_PATTERNS)

        if link is not None:
            links.append(link)
            if full_line_link_found:
                break
            else:
                line = _replace_link_with_blanks(line, link)
                continue

        break
    return links


def _get_ref_target(buffer: Buffer, src_target: str) -> str:
    ref_targets_map = buffer.vars.get("progirl_markdown_ref_targets", {})
    ref_target = ref_targets_map.get(src_target, None)
    if ref_target is None:
        ref_targets_map = generate_ref_targets_map(buffer)
        ref_target = ref_targets_map.get(src_target, None)
    return ref_target


def _resolve_link(buffer: Buffer, link: Link) -> Link | None:
    if link.ref_type is LinkRefType.REF_SOURCE:
        ref_target = _get_ref_target(buffer, link.target)
        if ref_target is None:
            resolved_link = None
        else:
            ref_source = link
            resolved_link = Link(ref_source=ref_source, ref_target=ref_target)
    else:
        resolved_link = link
    return resolved_link


def _get_link_at_cursor(vim: pynvim.Nvim) -> Link | None:
    line = vim.current.line
    links = _extract_links_from_line(line)
    link_at_cursor = None
    if links is not None:
        cursor_col = vim.current.window.cursor[1]
        for link in links:
            if link.start <= cursor_col < link.end:
                link_at_cursor = _resolve_link(vim.current.buffer, link)
                break
    return link_at_cursor


def generate_ref_targets_map(buffer: Buffer) -> dict[str, str]:
    # This function possibly needs to be refactored into separate functions
    # as it generates the ref_targets_map, applies it to the buffer var
    # and returns it, which can all be considered separate responsibilities.
    ref_targets_map = {}
    link_patterns = [
            link_pattern for link_pattern in _LINK_PATTERNS
            if link_pattern.ref_type == LinkRefType.REF_TARGET
    ]
    for line in buffer:
        link, _ = _find_link(line, link_patterns)
        if link is not None:
            ref_targets_map[link.name] = link.target
    buffer.vars["progirl_markdown_ref_targets"] = ref_targets_map
    return ref_targets_map


def get_uri_at_cursor(vim: pynvim.Nvim) -> str | None:
    link = _get_link_at_cursor(vim)
    if link is None:
        uri = None
    else:
        uri = link.target
    return uri


def _get_ref_trg_start(progirl_buffer: ProGirlBuffer) -> int:
    buffer = progirl_buffer.buffer
    try:
        return buffer[:].index("<!--LINK TARGETS-->") + 1
    except IndexError:
        raise LinksError("Link targets section missing")


def _add_ref_trg(progirl_buffer: ProGirlBuffer, description: str, target: str):
    buffer = progirl_buffer.buffer
    # ref_trg_start = get_ref_trg_start(progirl_buffer)
    try:
        ref_targets_map = buffer.vars["progirl_markdown_ref_targets"]
    except KeyError:
        ref_targets_map = generate_ref_targets_map(progirl_buffer.buffer)

    ref_trg_index = str(
            min(
                    index for index in range(len(ref_targets_map) + 1)
                    if str(index) not in ref_targets_map
            )
    )

    buffer.append(f"[{ref_trg_index}]: {target}")
    # buffer[ref_trg_start:] = sorted(buffer[ref_trg_start:])
    ref_targets_map[ref_trg_index] = str(target)
    buffer.vars["progirl_markdown_ref_targets"] = ref_targets_map
    return ref_trg_index


def _add_ref_src(
        progirl_buffer: ProGirlBuffer, description: str, ref_trg_index: str
):
    vim = progirl_buffer.vim
    link_str = f"[{description}][{ref_trg_index}]"
    vim.api.put([link_str], "c", True, True)


def _clean_description(description: str) -> str:
    return "".join(
            char for char in description
            if char not in _INVALID_LINK_DESCRIPTION_CHARS
    )


def add_ref_link(progirl_buffer: ProGirlBuffer, description: str, target: str):
    cleaned_description = _clean_description(description)
    ref_trg_index = _add_ref_trg(progirl_buffer, cleaned_description, target)
    _add_ref_src(progirl_buffer, cleaned_description, ref_trg_index)
