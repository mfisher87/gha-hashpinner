"""Discovers GitHub Actions workflow files in a given directory."""

from pathlib import Path


def discover_workflow_files(directory: Path) -> list[Path]:
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
