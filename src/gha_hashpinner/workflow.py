"""Behaviors for interacting with individual workflow files."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml

from gha_hashpinner.action import ImmutableAction, MutableAction
from gha_hashpinner.regex.updater import action_updater_regex
from gha_hashpinner.regex.uses import USES_PATTERN


@dataclass
class WorkflowFile:
    """Interface for interacting with a GitHub Actions workflow config file."""

    path: Path

    def __post_init__(self) -> None:
        """Validate the workflow file."""
        self._validate_yaml()

    @cached_property
    def content(self) -> str:
        """The string content of the workflow file."""
        return self.path.read_text()

    @cached_property
    def mutable_actions(self) -> list[MutableAction]:
        """Parse the workflow file and extract action specifiers with mutable pins.

        Returns:
            List of `MutableAction`s

        """
        # TODO: Consider getting all actions, and only updating the mutable ones.

        actions: list[MutableAction] = []

        for line_number, line in enumerate(self.content.splitlines(), start=1):
            if "uses:" not in line:
                continue

            match = USES_PATTERN.search(line)
            if not match:
                # TODO: Warn?
                continue

            action_specifier = match.group("action_spec").strip()
            action = MutableAction.parse(action_specifier, line_number=line_number)

            if action is not None:
                actions.append(action)

        return actions

    def update_actions(self, *, immutable_actions: list[ImmutableAction]) -> None:
        """Change each mutable action specifier in the file to immutable.

        Updates the workflow file in-place. Includes a comment at the end of each
        immutable specifier for Dependabot compatibility.

        Args:
            immutable_actions: List of hash-pinned action specifiers to apply

        """
        if not immutable_actions:
            return

        content = self.path.read_text()
        lines = content.splitlines(keepends=True)

        for immutable in immutable_actions:
            line_number = immutable.mutable_origin.line_number
            lines[line_number - 1] = self._replace_action_in_line(
                lines[line_number - 1],
                immutable_action=immutable,
            )

        self.path.write_text("".join(lines))

    def _replace_action_in_line(
        self,
        line: str,
        *,
        immutable_action: ImmutableAction,
    ) -> str:
        """Replace a single line's mutable action specifier with an immutable one.

        Includes a comment with the intended mutable Git ref for dependabot.

        Preserves indentation and quote style. Does not preserve existing comments.

        Args:
            line: The original line containing the original action specifier
            immutable_action: The hash-pinned action specifier to replace the original

        Returns:
            Updated line with immutable specifier and comment

        Raises:
            ValueError: When regex matching fails to parse the file content

        """
        return _replace_action_in_line(line, immutable_action=immutable_action)

    def _validate_yaml(self) -> None:
        """Ensure the workflow file is valid YAML."""
        try:
            yaml.safe_load(self.content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {self.path}: {e}") from e


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
        immutable_action: The hash-pinned action specifier to replace the original

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
        f"{match.group('key')}"
        f"{match.group('quote_open')}"
        f"{immutable_action.full_string}"
        f"{match.group('quote_close')}"
        f"  # {immutable_action.comment}"
        f"{match.group('line_ending')}"
    )
