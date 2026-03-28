"""Provides regex patterns and helpers."""

import re

from gha_hashpinner.models import ActionReference

# Match a github-style action ref, but not local actions (`./<...>`) or docker actions
# (`docker://<...>`)
ACTION_PATTERN = re.compile(
    r"^(?P<owner>[a-zA-Z0-9_-]+)"
    r"/(?P<repo>[a-zA-Z0-9_-]+)"
    r"(?P<subpath>/[^@]+)?"
    r"@(?P<ref>[a-zA-Z0-9./_-]+)$"
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


def action_updater_regex(mutable_ref: ActionReference) -> re.Pattern[str]:
    """Generate a regex to be used for updating a ref to make it immutable."""
    # TODO: Named groups
    return re.compile(
        r"(\s*-?\s*uses:\s*)"  # Group 1: The key, with leading and trailing whitespace
        r"([\"']?)"  # Group 2: Optional opening quote
        + re.escape(mutable_ref.full_string)  # The original ref string
        + r"([\"']?)"  # Group 3: Optional closing quote
        r"[ \t]*"  # Trailing whitespace after ref
        r"#*[^\r\n]*"  # Optional comment
        r"(\r?\n?)$"  # Group 4: Line ending
    )
