import pynvim

from progirl.uri import URI
from progirl.markdown.links import generate_ref_targets_map
from progirl.goto import goto_file_at_cursor
from progirl.goto import goto_ex_at_cursor
from progirl.pkbm import load_config
from progirl.pkbm import add_note_ref_link
from progirl.pkbm import edit_note


@pynvim.plugin
class ProGirlPlugin(object):

    def __init__(self, vim: pynvim.Nvim):
        self._vim = vim
        load_config(vim)

    # @pynvim.command(name: str, nargs: Union[str, int] = 0, complete:
    # Optional[str, None] = None, range: Union[str, int, None] = None, count:
    # Optional[int, None] = None, bang: bool = False, register: bool = False,
    # sync: bool = False, allow_nested: bool = False, eval: Optional[str, None]
    # = None)
    # def test_command(self, args, range):
    @pynvim.command(
            name='ProGirlTestCommand',
            range='',
            nargs='*',
            sync=True,
            # count=2,
            # register=True,
    )
    def test_command(self, *args, **kwargs):
        self._vim.current.buffer.append([str(args), str(kwargs)])
        self._vim.current.buffer.append(str(URI("abc", "def")))

    @pynvim.command(name='ProGirlGenMdBufRefMap', sync=True)
    def _cmd_gen_md_buf_ref_map(self):
        generate_ref_targets_map(self._vim.current.buffer)

    @pynvim.command(name='ProGirlGoToFile', nargs='*', sync=True)
    def _cmd_go_to_file(self, args):
        if args:
            pass
        else:
            goto_file_at_cursor(self._vim)

    @pynvim.command(name='ProGirlGoToEx', nargs='*', sync=True)
    def _cmd_go_to_ex(self, args):
        if args:
            pass
        else:
            goto_ex_at_cursor(self._vim)

    @pynvim.command(name='ProGirlEditNote', nargs='*', sync=True)
    def _cmd_edit_note(self, args):
        edit_note(self._vim, args)

    @pynvim.command(name='ProGirlAddNoteRefLink', nargs='*', sync=True)
    def _cmd_add_note_ref_link(self, args):
        add_note_ref_link(self._vim, args)
