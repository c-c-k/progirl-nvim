from datetime import datetime
import os.path as osp
from pathlib import Path
import re
import string

import pynvim

from pkbm.buffer import PKBMBuffer
from pkbm.globals import config
from pkbm.markdown import add_ref_link as md_add_ref_link
from pkbm.path import get_context_pwd
from pkbm.path import resolve_path_with_context
from pkbm.path import touch_with_mkdir
from pkbm.uri import URI
from pkbm.utils import AttrDict

from pkbm.pkbm.exceptions import CollectionError
from pkbm.pkbm.utils import get_current_c_id
from pkbm.pkbm.utils import get_c_id_by_path
from pkbm.pkbm.utils import get_collection_by_c_id
from pkbm.pkbm.utils import get_auto_id

LEGAL_CHARACTERS = string.ascii_lowercase + string.digits + "._"
PATTERN_TAGS_LINE = re.compile(r"^[<>!-\\#/* \t]*@tags: *(?P<TAGS>.*)$")
PATTERN_TITLE_LINE = re.compile(r"^#(?P<TITLE>[^#].*)$")


class NoteInfo:
    path_str: str
    path_uri: URI
    title: str
    _c_id: str
    _dir_path_str: str
    _extension: str
    _filename: str
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
            self._extension = self._title_args.pop()
        else:
            self._extension = ""

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
        if self._extension == "":
            self._extension = self.collection.extension

    def _create_title(self):
        self.title = " ".join(self._title_args)

    def _create_filename(self):
        template_str = self.collection.filename_template

        template_str = datetime.strftime(datetime.now(), template_str)
        template = string.Template(template_str)

        use_auto_id = "${AUTO_ID}" in template_str
        params = self._create_filename_params(use_auto_id=use_auto_id)
        self._filename = template.substitute(params)

    def _create_path_str(self):
        self.path_str = resolve_path_with_context(
                self._filename, context_pwd=self._dir_path_str
        )

    def _create_filename_params(self, use_auto_id: bool) -> dict[str, str]:
        params = {}
        params["TITLE_CLEAN"] = _clean_name(self.title)
        params["EXTENSION"] = _clean_name(self._extension)
        if use_auto_id:
            params["AUTO_ID"] = get_auto_id(self._vim, self._c_id)

        return params

    def _create_path_uri(self):
        # TODO: delete commented out code if everything works
        # buffer_pwd = get_context_pwd()
        # c_notes_path = self.collection.notes_path

        # if buffer_pwd is not None:
        #     if (buffer_pwd.startswith(collection_path) and (osp.commonpath(
        #             (buffer_pwd, self._dir_path_str)) == buffer_pwd)):
        #         path_str = self.path_str.replace(buffer_pwd, ".")

        # if path_str is None:
        #     path_str = self.path_str.replace(collection_path, "")

        prefix = osp.commonpath((self.collection.notes_path, self.path_str))
        path_str = self.path_str[len(prefix):]
        self.path_uri = URI(self._c_id, path_str)


def _clean_name(name: str) -> str:
    last_char = ""
    cleaned_chars = []
    for char in name.lower():
        cleaned_char = char if char in LEGAL_CHARACTERS else "_"
        if not (cleaned_char == "_" and last_char == "_"):
            cleaned_chars.append(cleaned_char)
            last_char = cleaned_char
    return "".join(cleaned_chars).strip("_")


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


def create_initial_content_params(
        vim: pynvim.Nvim, note_info: NoteInfo, use_cb: bool, **kwargs
) -> dict[str, str]:
    params: dict[str, str] = {}

    if use_cb:
        pkbm_buffer = PKBMBuffer(vim)
        params["TITLE"] = (
                note_info.title if note_info.title != "" else
                pkbm_buffer.re(PATTERN_TITLE_LINE).group("TITLE")
        )
        params["TAGS"] = pkbm_buffer.re(PATTERN_TAGS_LINE).group("TAGS")
    else:
        params["TITLE"] = note_info.title
        params["TAGS"] = ""

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
    pkbm_buffer = PKBMBuffer(vim)
    if note_info is None:
        vim.api.echo([["can not create/find note from args: "], title_args],
                     True, {})
        return

    md_add_ref_link(pkbm_buffer, note_info.title, note_info.path_uri)
