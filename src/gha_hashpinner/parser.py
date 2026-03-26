"""Functions for parsing mutable action references from workflow files."""

import re
from pathlib import Path

import yaml

from gha_hashpinner.models import ActionReference

# Match a github-style action ref, but not local actions (`./<...>`) or docker actions
# (`docker://<...>`)
ACTION_PATTERN = re.compile(
    r"^(?P<owner>[a-zA-Z0-9_-]+)/(?P<repo>[a-zA-Z0-9_-]+)@(?P<ref>[a-zA-Z0-9./_-]+)$"
)
# A Git commit sha is 40 hexadecimal characters
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
USES_PATTERN = re.compile(r"uses:\s+[\"']?([^\"'#\s]+)")


def find_all_mutable_action_references(path: Path) -> dict[Path, list[ActionReference]]:
    """Find all mutable action references in workflow file(s).

    Args:
        path: A directory containing `.github/workflows/` or a single workflow file

    Returns:
        A dictionary mapping workflow file `Path`s to `list`s of `ActionReference`s

    """
    if path.is_file():
        return {path: _parse_workflow_file(path)}

    if path.is_dir():
        return {
            workflow_file: _parse_workflow_file(workflow_file)
            for workflow_file in _discover_workflow_files(path)
        }

    raise FileNotFoundError(f"Path '{path}' is not a file or directory.")


def _discover_workflow_files(directory: Path) -> list[Path]:
    """Find all workflow files in `{directory}/.github/workflows/`.

    Matches `.yaml` or `.yml` files.

    Args:
        directory: Root directory to search

    Returns:
        List of `Path`s to workflow files

    """
    workflows_dir = directory / ".github" / "workflows"

    if not (workflows_dir.exists() and workflows_dir.is_dir()):
        raise FileNotFoundError(f"No workflows directory found at {workflows_dir}")

    workflow_files: list[Path] = []
    for pattern in ("*.yml", "*.yaml"):
        workflow_files.extend(workflows_dir.glob(pattern))

    return sorted(workflow_files)


def _parse_workflow_file(workflow_path: Path) -> list[ActionReference]:
    """Parse a workflow file and extract action references with mutable pins.

    Args:
        workflow_path: Path to a workflow YAML file

    Returns:
        List of `ActionReference`s with mutable pins

    """
    # TODO: Use ruamel_yaml to avoid iterating line-by-line?

    content = workflow_path.read_text()
    _validate_yaml(content=content, path=workflow_path)

    action_refs: list[ActionReference] = []
    lines = content.splitlines()

    for line_no, line in enumerate(lines, start=1):
        if "uses:" not in line:
            continue

        match = USES_PATTERN.search(line)
        if not match:
            # TODO: Warn?
            continue

        action_uses_str = match.group(1).strip()

        action_ref = _parse_uses_str(action_uses_str, line_no=line_no)
        if action_ref is None:
            continue

        action_refs.append(action_ref)

    return action_refs


# TODO: Support multi-line values if they are present for whatever reason...
def _parse_uses_str(action_uses_str: str, *, line_no: int) -> ActionReference | None:
    """Parse a mutable `ActionReference` from the value of a `uses:` key.

    Args:
        action_uses_str: A string value of a YAML `uses:` key from a GitHub Actions
            workflow definition
        line_no: The line number the `uses:` value was found on

    Returns:
        `None` if no mutable ref found, otherwise a mutable `ActionReference`

    """
    # TODO: We're already eliminating these with the regex below, right?
    if action_uses_str.startswith(("./", "docker://")):
        # TODO: Log (debug?)?
        return None

    action_match = ACTION_PATTERN.match(action_uses_str)
    if not action_match:
        # TODO: Warn
        return None

    action_ref = ActionReference(
        owner=action_match.group("owner"),
        repo=action_match.group("repo"),
        ref=action_match.group("ref"),
        line_number=line_no,
        full_string=action_uses_str,
    )

    if SHA_PATTERN.match(action_ref.ref):
        # TODO: debug log
        return None

    return action_ref


def _validate_yaml(*, content: str, path: Path) -> None:
    """Validate that YAML content can be successfully parsed."""
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e
