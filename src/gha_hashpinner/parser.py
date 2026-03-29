"""Functions for parsing mutable action specifiers from workflow files."""

from gha_hashpinner.models import MutableAction
from gha_hashpinner.regex import ACTION_PATTERN, SHA_PATTERN


# TODO: Support multi-line values if they are present for whatever reason...
def parse_action_specifier(
    action_specifier: str,
    *,
    line_number: int,
) -> MutableAction | None:
    """Parse a `MutableAction` from a mutable action specifier.

    Args:
        action_specifier: A string value of a YAML `uses:` key from a GitHub Actions
            workflow definition
        line_number: The line number the `action_specifier` was found on

    Returns:
        `None` if no mutable action specifier found, otherwise a `MutableAction`

    """
    # TODO: We're already eliminating these with the regex below, right?
    if action_specifier.startswith(("./", "docker://")):
        # TODO: Log (debug?)?
        return None

    action_match = ACTION_PATTERN.match(action_specifier)
    if not action_match:
        # TODO: Warn
        return None

    action = MutableAction(
        owner=action_match.group("owner"),
        repo=action_match.group("repo"),
        subpath=action_match.group("subpath"),
        ref=action_match.group("ref"),
        line_number=line_number,
        full_string=action_specifier,
    )

    if SHA_PATTERN.match(action.ref):
        # TODO: debug log
        return None

    return action
