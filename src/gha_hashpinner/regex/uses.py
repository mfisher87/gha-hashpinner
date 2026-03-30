"""Provides regex patterns and helpers."""

import re

_USES_PATTERN_KEY = r"^\s*-?\s*uses:\s+"  # with leading and trailing whitespace
_USES_PATTERN_OPTIONAL_QUOTE = r"[\"']?"
_USES_PATTERN_SPEC_CAPTURE = r"(?P<action_spec>[^\"'#\s]+)"

# Extract the action specifier from a line containing a "uses: ..." key
USES_PATTERN = re.compile(
    _USES_PATTERN_KEY + _USES_PATTERN_OPTIONAL_QUOTE + _USES_PATTERN_SPEC_CAPTURE
)
