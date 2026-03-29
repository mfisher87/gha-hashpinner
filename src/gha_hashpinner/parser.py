"""Functions for parsing mutable action specifiers from workflow files."""

from pathlib import Path

import yaml

from gha_hashpinner.discoverer import discover_workflow_files
from gha_hashpinner.models import MutableAction
from gha_hashpinner.regex import ACTION_PATTERN, SHA_PATTERN, USES_PATTERN


def find_all_mutable_actions(path: Path) -> dict[Path, list[MutableAction]]:
    """Find all mutable action specifiers in workflow file(s).

    Args:
        path: A directory containing `.github/workflows/` or a single workflow file

    Returns:
        A dictionary mapping workflow file `Path`s to `list`s of `MutableAction`s

    """
    if path.is_file():
        return {path: _parse_workflow_file(path)}

    if path.is_dir():
        return {
            workflow_file: _parse_workflow_file(workflow_file)
            for workflow_file in discover_workflow_files(path)
        }

    raise FileNotFoundError(f"Path '{path}' is not a file or directory.")


def _parse_workflow_file(workflow_path: Path) -> list[MutableAction]:
    """Parse a workflow file and extract action specifiers with mutable pins.

    Args:
        workflow_path: Path to a workflow YAML file

    Returns:
        List of `MutableAction`s with mutable pins

    """
    # TODO: Use ruamel_yaml to avoid iterating line-by-line?

    content = workflow_path.read_text()
    _validate_yaml(content=content, path=workflow_path)

    actions: list[MutableAction] = []
    lines = content.splitlines()

    for line_no, line in enumerate(lines, start=1):
        if "uses:" not in line:
            continue

        match = USES_PATTERN.search(line)
        if not match:
            # TODO: Warn?
            continue

        action_uses_str = match.group("action_spec").strip()

        action = _parse_uses_str(action_uses_str, line_no=line_no)
        if action is None:
            continue

        actions.append(action)

    return actions


# TODO: Support multi-line values if they are present for whatever reason...
def _parse_uses_str(action_uses_str: str, *, line_no: int) -> MutableAction | None:
    """Parse a mutable `MutableAction` from the value of a `uses:` key.

    Args:
        action_uses_str: A string value of a YAML `uses:` key from a GitHub Actions
            workflow definition
        line_no: The line number the `uses:` value was found on

    Returns:
        `None` if no mutable action specifier found, otherwise a `MutableAction`

    """
    # TODO: We're already eliminating these with the regex below, right?
    if action_uses_str.startswith(("./", "docker://")):
        # TODO: Log (debug?)?
        return None

    action_match = ACTION_PATTERN.match(action_uses_str)
    if not action_match:
        # TODO: Warn
        return None

    action = MutableAction(
        owner=action_match.group("owner"),
        repo=action_match.group("repo"),
        subpath=action_match.group("subpath"),
        ref=action_match.group("ref"),
        line_number=line_no,
        full_string=action_uses_str,
    )

    if SHA_PATTERN.match(action.ref):
        # TODO: debug log
        return None

    return action


def _validate_yaml(*, content: str, path: Path) -> None:
    """Validate that YAML content can be successfully parsed."""
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e
