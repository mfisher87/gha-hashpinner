"""Provides regex patterns and helpers."""

import re

from gha_hashpinner.action import MutableAction
from gha_hashpinner.regex.uses import (
    _USES_PATTERN_KEY,
    _USES_PATTERN_OPTIONAL_QUOTE,
)


def action_updater_regex(mutable_action: MutableAction) -> re.Pattern[str]:
    """Generate a regex to be used for updating an action specifier to immutable."""
    return re.compile(
        rf"(?P<key>{_USES_PATTERN_KEY})"
        rf"(?P<quote_open>{_USES_PATTERN_OPTIONAL_QUOTE})"
        + re.escape(mutable_action.full_string)  # The original action specifier string
        + rf"(?P<quote_close>{_USES_PATTERN_OPTIONAL_QUOTE})"
        r"[ \t]*"  # Trailing whitespace after specifier value
        r"#*[^\r\n]*"  # Optional comment
        r"(?P<line_ending>\r?\n?)$"
    )
