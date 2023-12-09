from datetime import datetime
import os.path as osp
from pathlib import Path
import re
import string
import typing as t

import pynvim

from progirl.buffer import ProGirlBuffer
from progirl.globals import config
from progirl.markdown import add_ref_link as md_add_ref_link
from progirl.path import get_context_pwd
from progirl.path import resolve_path_with_context
from progirl.path import touch_with_mkdir
from progirl.uri import URI
from progirl.utils import AttrDict

from progirl.pkbm.exceptions import CollectionError
from progirl.pkbm.utils import get_current_c_id
from progirl.pkbm.utils import get_c_id_by_path
from progirl.pkbm.utils import get_collection_by_c_id
from progirl.pkbm.utils import get_dir_auto_id

TITLE_LEGAL_CHARACTERS = string.ascii_lowercase + string.digits + "._"
TAG_LEGAL_CHARACTERS = string.ascii_lowercase + string.digits + "-"
PATTERN_TAGS_LINE = re.compile(r"^[<>!-\\#/* \t]*@tags: *(?P<TAGS>.*)$")
PATTERN_TITLE_LINE = re.compile(r"^#(?P<TITLE>[^#].*)$")
TEMP_PROJECT_CARD_TEMPLATE = '${AUTO_ID}-${TITLE_CLEAN}'
TEMP_PATTERN_IS_PROJECT_CARD = re.compile(r"^.*projects/.*cards/?$")


class NoteInfo:
    path_str: str
    path_uri: URI
    title: str
    base_filename: str
    extension: str
    filename: str
    _c_id: str
    _dir_path_str: str
    _title_words: list[str]
    _use_cb: bool
    _vim: pynvim.Nvim

    def __init__(self, vim: pynvim.Nvim, title_args: list[str], use_cb: bool):
        self._vim = vim
        self._title_args = title_args
        self._use_cb = use_cb
        self._parse_uri_arg()
        self._resolve_collection()
        self._extract_extension()
        self._resolve_dir_path()
        self._resolve_extension()
        self._create_title()
        self._create_filename()
        self._create_path_str()
        self._create_path_uri()

    @property
    def collection(self) -> AttrDict:
        return get_collection_by_c_id(self._c_id)

    def _parse_uri_arg(self):
        if len(self._title_args) == 0:
            self._c_id = ""
            self._dir_path_str = ""
            return

        uri = URI(self._title_args[0])
        c_id = uri.protocol
        dir_path_str = uri.body

        if (c_id != "") and (c_id not in config.collections):
            raise CollectionError(f"not a pkb collection: {c_id}")
        if (c_id == "") and ("/" not in dir_path_str):
            dir_path_str = ""
        if (dir_path_str != "") or (c_id != ""):
            self._title_args = self._title_args[1:]
        if (c_id != "") and (dir_path_str == ""):
            dir_path_str = "/"

        self._c_id = c_id
        self._dir_path_str = dir_path_str

    def _resolve_collection(self):
        if self._c_id == "":
            self._c_id = get_current_c_id(self._vim, check_cb=self._use_cb)

    def _extract_extension(self):
        if (  # yapf hack
                (len(self._title_args) > 0)
                and (self._title_args[-1].find(".") == 0)):
            self.extension = self._title_args.pop()
        else:
            self.extension = ""

    def _resolve_dir_path(self):
        c_notes_path = self.collection.notes_path

        if self._use_cb:
            buffer = self._vim.current.buffer
            buf_dir = get_context_pwd(buffer=buffer)
            buf_c_id = (
                    get_c_id_by_path(buf_dir) if buf_dir is not None else None
            )
            context_pwd = buf_dir if buf_c_id == self._c_id else c_notes_path
        else:
            context_pwd = c_notes_path

        self._dir_path_str = resolve_path_with_context(
                self._dir_path_str,
                context_pwd=context_pwd,
                context_root=c_notes_path
        )

    def _resolve_extension(self):
        if self.extension == "":
            self.extension = self.collection.extension
        self.extension = clean_title(self.extension.lstrip("."))

    def _create_title(self):
        self.title = " ".join(self._title_args)

    def _create_filename(self):
        if TEMP_PATTERN_IS_PROJECT_CARD.match(self._dir_path_str):
            template_str = TEMP_PROJECT_CARD_TEMPLATE
        else:
            template_str = self.collection.filename_template

        template_str = datetime.strftime(datetime.now(), template_str)
        template = string.Template(template_str)

        use_auto_id = "${AUTO_ID}" in template_str
        params = self._create_filename_params(use_auto_id=use_auto_id)
        self.base_filename = template.substitute(params)
        self.filename = ".".join((self.base_filename, self.extension))

    def _create_path_str(self):
        self.path_str = resolve_path_with_context(
                self.filename, context_pwd=self._dir_path_str
        )

    def _create_filename_params(self, use_auto_id: bool) -> dict[str, str]:
        params = {}
        params["TITLE_CLEAN"] = clean_title(self.title)
        if use_auto_id:
            # params["AUTO_ID"] = get_collection_auto_id(self._c_id)
            params["AUTO_ID"] = get_dir_auto_id(self._dir_path_str)

        return params

    def _create_path_uri(self):
        prefix = osp.commonpath((self.collection.notes_path, self.path_str))
        path_str = self.path_str[len(prefix):]
        self.path_uri = URI(self._c_id, path_str)

    @property
    def id_(self) -> str:
        return self.path_uri.body


def clean_tag(name: str) -> str:
    return _clean_string(
            name=name,
            valid_chars=TAG_LEGAL_CHARACTERS,
            filler_char="-",
            preprocessor=lambda s: s.lower()
    )


def clean_title(name: str) -> str:
    return _clean_string(
            name=name,
            valid_chars=TITLE_LEGAL_CHARACTERS,
            filler_char="_",
            preprocessor=lambda s: s.lower()
    )


def _clean_string(
        name: str, valid_chars: str, filler_char: str,
        preprocessor: t.Callable | None
) -> str:
    if preprocessor is not None:
        name = preprocessor(name)

    last_char = ""
    cleaned_chars = []
    for char in name:
        cleaned_char = char if char in valid_chars else filler_char
        if not (cleaned_char == filler_char and last_char == filler_char):
            cleaned_chars.append(cleaned_char)
            last_char = cleaned_char

    return "".join(cleaned_chars).strip(filler_char)


def create_note(
        vim: pynvim.Nvim,
        title_args: list[str],
        use_cb: bool,
) -> NoteInfo | None:
    try:
        note_info = NoteInfo(vim, title_args, use_cb)
    except CollectionError as err:
        vim.api.echo([err.args], True, {})
        return None

    if osp.exists(note_info.path_str):
        return note_info
    if touch_with_mkdir(note_info.path_str) is None:
        vim.api.echo([[f"can not create file {note_info.path_str}"]], True, {})
        return None

    initial_content = create_initial_content(vim, note_info, use_cb)
    Path(note_info.path_str).write_text(initial_content)

    return note_info


def create_initial_content(
        vim: pynvim.Nvim, note_info: NoteInfo, use_cb: bool, **kwargs
) -> str:
    template_path = note_info.collection.default_template
    if osp.exists(template_path):
        with open(template_path) as f:
            template_str = f.read()
    else:
        template_str = ""
    template = string.Template(template_str)
    params = create_initial_content_params(vim, note_info, use_cb, **kwargs)
    initial_content = template.safe_substitute(params)
    return initial_content


def create_initial_tags(note_info: NoteInfo) -> list[str]:
    tags = []

    id_dir = osp.dirname(note_info.id_)
    while id_dir != "/":
        tags.append(clean_tag(osp.basename(id_dir)))
        id_dir = osp.dirname(id_dir)
    tags.reverse()

    parent_dir_name = osp.basename(osp.dirname(note_info.path_str))
    if parent_dir_name == note_info.base_filename:
        tags.append("index")

    return tags


def create_initial_content_params(
        vim: pynvim.Nvim, note_info: NoteInfo, use_cb: bool, **kwargs
) -> dict[str, str]:
    params: dict[str, str] = {}

    # if use_cb:
    #     # copy initial params from current buffer
    #     progirl_buffer = ProGirlBuffer(vim)
    #     params["TITLE"] = (
    #             note_info.title if note_info.title != "" else
    #             progirl_buffer.re(PATTERN_TITLE_LINE).group("TITLE")
    #     )
    #     params["TAGS"] = progirl_buffer.re(PATTERN_TAGS_LINE).group("TAGS")
    # else:
    #     params["TITLE"] = note_info.title
    #     params["TAGS"] = ""

    params["TITLE"] = note_info.title
    params["TAGS"] = ", ".join(create_initial_tags(note_info))
    params["TITLE_UPPER"] = params["TITLE"].upper()
    params["NOTE_ID"] = note_info.id_

    params.update(kwargs)
    return params


def edit_note(vim: pynvim.Nvim, title_args: list[str]):
    note_info = create_note(vim, title_args, use_cb=True)
    if note_info is None:
        vim.api.echo([["can not create/edit note from args: "], title_args],
                     True, {})
        return

    command = f"edit {note_info.path_str}"
    vim.command(command)


def add_note_ref_link(vim: pynvim.Nvim, title_args: list[str]):
    note_info = create_note(vim, title_args, use_cb=True)
    progirl_buffer = ProGirlBuffer(vim)
    if note_info is None:
        vim.api.echo([["can not create/find note from args: "], title_args],
                     True, {})
        return

    buffer_c_id = get_c_id_by_path(
            resolve_path_with_context(progirl_buffer.buffer.name)
    )
    if note_info._c_id == buffer_c_id:
        link_target = note_info.path_uri.body
    else:
        link_target = str(note_info.path_uri)
    md_add_ref_link(progirl_buffer, note_info.title, link_target)
