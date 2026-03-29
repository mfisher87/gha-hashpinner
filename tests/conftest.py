"""Pytest magic config -- implicitly provides fixtures to tests."""

from pathlib import Path

import pytest

from gha_hashpinner.models import ImmutableAction, MutableAction

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
def mock_mutable_action_checkout() -> MutableAction:
    """Mock mutable action specifier for 'actions/checkout@v4'."""
    return MutableAction(
        owner="actions",
        repo="checkout",
        ref="v4",
        line_number=10,
        full_string="actions/checkout@v4",
    )


@pytest.fixture
def mock_mutable_action_python() -> MutableAction:
    """Mock mutable action specifier for 'actions/setup-python@v5'."""
    return MutableAction(
        owner="actions",
        repo="setup-python",
        ref="v5",
        line_number=11,
        full_string="actions/setup-python@v5",
    )


@pytest.fixture
def mock_immutable_action_checkout() -> ImmutableAction:
    """Sample immutable action specifier for 'actions/checkout@v4'."""
    return ImmutableAction(
        mutable_origin=MutableAction(
            owner="actions",
            repo="checkout",
            ref="v4",
            line_number=7,
            full_string="actions/checkout@v4",
        ),
        sha="abc123def456abc123def456abc123def456abc123",
        comment="v4",
    )


@pytest.fixture
def mock_immutable_action_python() -> ImmutableAction:
    """Sample immutable action specifier for 'actions/setup-python@v5'."""
    return ImmutableAction(
        mutable_origin=MutableAction(
            owner="actions",
            repo="setup-python",
            ref="v5",
            line_number=8,
            full_string="actions/setup-python@v5",
        ),
        sha="def456abc123def456abc123def456abc123def456",
        comment="v5",
    )


@pytest.fixture
def mock_immutable_action_enforcelabel() -> ImmutableAction:
    """Sample immutable action specifier for 'jupyterlab/maintainer-tools/.../enforce-label@v1'."""
    return ImmutableAction(
        mutable_origin=MutableAction(
            owner="jupyterlab",
            repo="maintainer-tools",
            subpath="/.github/actions/enforce-label",
            ref="v1",
            line_number=8,
            full_string="jupyterlab/maintainer-tools/.github/actions/enforce-label@v1",
        ),
        sha="123abc123abc123abc123abc123abc123abc123abc",
        comment="v1",
    )
