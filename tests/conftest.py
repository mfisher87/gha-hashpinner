"""Pytest magic config -- implicitly provides fixtures to tests."""

from pathlib import Path

import pytest

from .types import MakeWorkflowsDirFunc


@pytest.fixture
def make_workflows_dir(tmp_path: Path) -> MakeWorkflowsDirFunc:
    """Create .github/workflows directory with multiple files.

    Usage:
        workflows = make_workflows_dir({
            "test1.yml": WORKFLOW_WITH_MUTABLE_PINS,
            "test2.yml": COMPLEX_WORKFLOW,
        })

    Returns:
        "Project" root directory

    """

    def _make_dir(workflow_files: dict[str, str]) -> Path:
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        for filename, content in workflow_files.items():
            workflow_path = workflows_dir / filename
            workflow_path.write_text(content)

        return tmp_path

    return _make_dir
