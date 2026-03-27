"""Pytest magic config -- implicitly provides fixtures to tests."""

from pathlib import Path

import pytest

from gha_hashpinner.models import ActionReference

from .types import MakeWorkflowFileFunc, MakeWorkflowsDirFunc


@pytest.fixture
def make_workflow_file(tmp_path: Path) -> MakeWorkflowFileFunc:
    """Create a single workflow file from YAML content.

    Usage:
        workflow_file = make_workflow_file(content=WORKFLOW_WITH_MUTABLE_PINS)
        workflow_file = make_workflow_file(content=COMPLEX_WORKFLOW, name="custom.yml")

    Returns:
        Path to created workflow file.

    """

    def _make_file(*, content: str, name: str = "test.yml") -> Path:
        workflow_file = tmp_path / name
        workflow_file.write_text(content)
        return workflow_file

    return _make_file


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


@pytest.fixture
def mock_action_ref_checkout() -> ActionReference:
    """Mock action reference for 'actions/checkout@v4'."""
    return ActionReference(
        owner="actions",
        repo="checkout",
        ref="v4",
        line_number=10,
        full_string="actions/checkout@v4",
    )


@pytest.fixture
def mock_action_ref_python() -> ActionReference:
    """Mock action reference for 'actions/setup-python@v5'."""
    return ActionReference(
        owner="actions",
        repo="setup-python",
        ref="v5",
        line_number=11,
        full_string="actions/setup-python@v5",
    )
