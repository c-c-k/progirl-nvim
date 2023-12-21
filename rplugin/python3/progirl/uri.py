import re
from typing import Pattern

_URI_PATTERN: Pattern = re.compile(r"^([\w-]*?):(.*)$")


class URI:
    protocol: str = ""
    body: str = ""

    def __init__(self, *uri: str):
        if len(uri) == 1:
            uri_match = _URI_PATTERN.match(uri[0])
            if uri_match:
                self.protocol, self.body = uri_match.groups()
            else:
                self.protocol, self.body = "", *uri
        elif len(uri) == 2:
            self.protocol, self.body = uri
        else:
            raise ValueError(
                    "URI class must be initialized"
                    "with exactly 1 or 2 arguments"
            )

    def __str__(self):
        return (
                f"{self.protocol}:{self.body}"
                if self.protocol != "" else self.body
        )
