"""Modifies workflow files to replace mutable pins with immutable ones."""

from pathlib import Path

from gha_hashpinner.models import ImmutableAction
from gha_hashpinner.regex import action_updater_regex


def update_workflow_file(
    workflow_file: Path,
    *,
    immutable_actions: list[ImmutableAction],
) -> None:
    """Change each mutable action specifier in `workflow_file` to immutable.

    Updates the workflow file in-place. Includes a comment at the end of each immutable
    specifier for Dependabot compatibility.

    Args:
        workflow_file: Path to the workflow YAML file to update
        immutable_actions: List of hash-pinned action specifiers to apply

    """
    if not immutable_actions:
        return

    content = workflow_file.read_text()
    lines = content.splitlines(keepends=True)

    for immutable in immutable_actions:
        line_number = immutable.mutable_origin.line_number
        lines[line_number - 1] = _replace_action_in_line(
            lines[line_number - 1],
            immutable_action=immutable,
        )

    workflow_file.write_text("".join(lines))


def _replace_action_in_line(
    line: str,
    *,
    immutable_action: ImmutableAction,
) -> str:
    """Replace a single line's mutable action specifier with an immutable one.

    Includes a comment with the intended mutable Git ref for dependabot.

    Preserves indentation and quote style. Does not preserve existing comments.

    Args:
        line: The original line containing the original action specifier
        immutable_action: The hash-pinned action specifier to replace the original with

    Returns:
        Updated line with immutable specifier and comment

    Raises:
        ValueError: When regex matching fails to parse the file content

    """
    pattern = action_updater_regex(immutable_action.mutable_origin)

    match = pattern.match(line)
    if match is None:
        raise ValueError(f"Failed to find 'uses:' key in line:\n  '{line}'")

    return (
        f"{match.group(1)}"
        f"{match.group(2)}"
        f"{immutable_action.full_string}"
        f"{match.group(3)}"
        f"  # {immutable_action.comment}"
        f"{match.group(4)}"
    )
