"""Discovers GitHub Actions workflow files in a given directory."""

from pathlib import Path

from gha_hashpinner.workflow import WorkflowFile


def scan_path(path: Path) -> list[WorkflowFile]:
    """Return a `WorkflowFile` for each GitHub Actions workflow in `path`.

    If `Path` is a file, return a list of size 1.
    """
    if path.is_file():
        return [WorkflowFile(path)]

    if path.is_dir():
        return _discover_workflow_files(path)

    raise FileNotFoundError(f"Path '{path}' is not a file or directory.")


def _discover_workflow_files(directory: Path) -> list[WorkflowFile]:
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

    return [WorkflowFile(wf_path) for wf_path in sorted(workflow_files)]
