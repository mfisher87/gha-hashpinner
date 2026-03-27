"""Modifies workflow files to replace mutable pins with immutable ones."""

import re
from pathlib import Path

from gha_hashpinner.models import HashPinnedActionReference


def update_workflow_file(
    workflow_file: Path,
    *,
    refs: list[HashPinnedActionReference],
) -> None:
    """Change each ref in `workflow_file` from a mutable ref to an immutable ref.

    Updates the workflow file in-place. Includes a comment at the end of each immutable
    ref for Dependabot compatibility.

    Args:
        workflow_file: Path to the workflow YAML file to update
        refs: List of hash-pinned action references to apply

    """
    if not refs:
        return

    content = workflow_file.read_text()
    lines = content.splitlines(keepends=True)

    for ref in refs:
        line_number = ref.action_reference.line_number
        lines[line_number - 1] = _replace_action_in_line(
            lines[line_number - 1],
            ref=ref,
        )

    workflow_file.write_text("".join(lines))


def _replace_action_in_line(
    line: str,
    *,
    ref: HashPinnedActionReference,
) -> str:
    """Replace a single line's mutable action reference with an immutable one.

    Includes a comment with the intended mutable ref for dependabot.

    Preserves indentation and quote style. Does not preserve existing comments.

    Args:
        line: The original line containing the original action reference
        ref: The hash-pinned action reference to replace the original with

    Returns:
        Updated line with immutable reference and comment

    Raises:
        ValueError: When regex matching fails to parse the file content

    """
    mutable = ref.action_reference

    # TODO: Import!
    pattern = re.compile(
        r"(\s*-?\s*uses:\s*)"  # Group 1: The key, with leading and trailing whitespace
        r"([\"']?)"  # Group 2: Optional opening quote
        + re.escape(mutable.full_string)  # The original ref string
        + r"([\"']?)"  # Group 3: Optional closing quote
        r"[ \t]*"  # Trailing whitespace after ref
        r"#*[^\r\n]*"  # Optional comment
        r"(\r?\n?)$"  # Group 4: Line ending
    )

    match = pattern.match(line)
    if match is None:
        raise ValueError(f"Failed to find 'uses:' key in line:\n  '{line}'")

    return (
        f"{match.group(1)}"
        f"{match.group(2)}"
        f"{ref.full_string}"
        f"{match.group(3)}"
        f"  # {ref.comment}"
        f"{match.group(4)}"
    )
