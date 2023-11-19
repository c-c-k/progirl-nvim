from datetime import datetime
from time import sleep

import pynvim

from pkbm.uri import URI


def handle_uri(vim: pynvim.Nvim, uri: URI):
    temp_log_file = "/dev/shm/vim-gx.log"
    command = (
            'exe "silent !xdg-open " . shellescape("'
            f'{uri!s}") . " &>>{temp_log_file}"'
    )
    with open(temp_log_file, "a") as f:
        f.write(f"--- {datetime.now()}: {command}\n")
    vim.command(command)
    sleep(0.1)
    vim.command("redraw!")
