import pynvim


@pynvim.plugin
class PKBMPlugin:

    def __init__(self, vim: pynvim.Nvim):
        self._vim = vim
