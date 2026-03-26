"""Modifies workflow files to replace mutable pins with immutable ones."""

from pathlib import Path

from gha_hashpinner.models import HashPinnedActionReference


def update_workflow_file(
    workflow_file: Path,
    refs: list[HashPinnedActionReference],
) -> None:
    """Change each ref in `workflow_file` from a mutable ref to an immutable ref."""
