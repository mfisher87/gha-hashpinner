"""Provides regex patterns and helpers."""

import re

from gha_hashpinner.models import MutableAction

# Match a github-style action specifier, but not local actions (`./<...>`) or docker
# actions (`docker://<...>`)
ACTION_PATTERN = re.compile(
    r"^(?P<owner>[a-zA-Z0-9_-]+)"
    r"/(?P<repo>[a-zA-Z0-9_-]+)"
    r"(?P<subpath>/[^@]+)?"
    r"@(?P<ref>[a-zA-Z0-9./_-]+)$"
)

# A Git commit sha is 40 hexadecimal characters
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_USES_PATTERN_KEY = r"^\s*-?\s*uses:\s+"  # with leading and trailing whitespace
_USES_PATTERN_OPTIONAL_QUOTE = r"[\"']?"
_USES_PATTERN_SPEC_CAPTURE = r"([^\"'#\s]+)"

# Extract the action specifier from a line containing a "uses: ..." key
USES_PATTERN = re.compile(
    _USES_PATTERN_KEY + _USES_PATTERN_OPTIONAL_QUOTE + _USES_PATTERN_SPEC_CAPTURE
)


def action_updater_regex(mutable_action: MutableAction) -> re.Pattern[str]:
    """Generate a regex to be used for updating an action specifier to immutable."""
    # TODO: Named groups
    return re.compile(
        rf"({_USES_PATTERN_KEY})"  # Group 1
        rf"({_USES_PATTERN_OPTIONAL_QUOTE})"  # Group 2
        + re.escape(mutable_action.full_string)  # The original action specifier string
        + rf"({_USES_PATTERN_OPTIONAL_QUOTE})"  # Group 3
        r"[ \t]*"  # Trailing whitespace after specifier value
        r"#*[^\r\n]*"  # Optional comment
        r"(\r?\n?)$"  # Group 4: Line ending
    )
