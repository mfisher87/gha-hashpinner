"""Provides regex patterns and helpers."""

import re

# Match a github-style action ref, but not local actions (`./<...>`) or docker actions
# (`docker://<...>`)
ACTION_PATTERN = re.compile(
    r"^(?P<owner>[a-zA-Z0-9_-]+)/(?P<repo>[a-zA-Z0-9_-]+)@(?P<ref>[a-zA-Z0-9./_-]+)$"
)
# A Git commit sha is 40 hexadecimal characters
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# USES_PATTERN_KEY = r"^\s*uses:\s+"
# USES_PATTERN_QUOTE = r"[\"']?"
# USES_PATTERN_REF_CAPTURE = r"([^\"'#\s]+)"
# USES_PATTERN = re.compile(
#     USES_PATTERN_KEY
#     + USES_PATTERN_QUOTE
#     + USES_PATTERN_REF_CAPTURE
# )

USES_PATTERN = re.compile(r"uses:\s+[\"']?([^\"'#\s]+)")

# USES_PATTERN = re.compile(r"^\s*uses:\s+[\"']?([^\"'#\s]+)")
#                           key             qt          ref                               qt       end
#                         r"^(\s*uses:\s+)([\"']?)" + re.escape(mutable.full_string) + r"([\"']?)(\s*#.*)?$"
