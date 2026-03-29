"""Regular expressions for parsing action specifiers."""

import re

# Match a github-style action specifier, not local actions (`./<...>`) or docker
# actions (`docker://<...>`)
ACTION_PATTERN = re.compile(
    r"^(?P<owner>[a-zA-Z0-9_-]+)"
    r"/(?P<repo>[a-zA-Z0-9_-]+)"
    r"(?P<subpath>/[^@]+)?"
    r"@(?P<ref>[a-zA-Z0-9./_-]+)$"
)
