"""Tests for the discoverer module."""

from pathlib import Path

import pytest

from gha_hashpinner.discoverer import _discover_workflow_files

from .mock_workflows import WORKFLOW_WITH_MUTABLE_PINS
from .types import MakeWorkflowsDirFunc


class TestDiscoverWorkflowFiles:
    """Test _discover_workflow_files function."""

    def test_discover_yml_and_yaml_files(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should find both .yml and .yaml files."""
        mock_root = make_workflows_dir(
            {
                "test1.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "test2.yaml": WORKFLOW_WITH_MUTABLE_PINS,
                "test3.yml": WORKFLOW_WITH_MUTABLE_PINS,
            }
        )

        files = _discover_workflow_files(mock_root)

        assert len(files) == 3
        assert all(f.path.suffix in [".yml", ".yaml"] for f in files)

    def test_discover_returns_sorted_paths(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should return sorted list of workflow files."""
        mock_root = make_workflows_dir(
            {
                "z.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "a.yaml": WORKFLOW_WITH_MUTABLE_PINS,
                "m.yml": WORKFLOW_WITH_MUTABLE_PINS,
            }
        )

        files = _discover_workflow_files(mock_root)

        assert files[0].path.name == "a.yaml"
        assert files[1].path.name == "m.yml"
        assert files[2].path.name == "z.yml"

    def test_discover_ignores_non_workflow_files(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should ignore non-YAML files in workflows directory."""
        mock_root = make_workflows_dir(
            {
                "test.yml": "name: Test",
                "README.md": "# README",
                "script.sh": "#!/bin/bash\necho foo",
            }
        )

        files = _discover_workflow_files(mock_root)

        assert len(files) == 1
        assert files[0].path.name == "test.yml"

    def test_discover_returns_empty_if_workflows_dir_empty(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should return an empty list if .github/workflows is empty."""
        mock_root = make_workflows_dir({})

        files = _discover_workflow_files(mock_root)
        assert files == []

    def test_discover_raises_if_nonexistent_path(self) -> None:
        """Should raise if a nonexistent path is used."""
        with pytest.raises(FileNotFoundError):
            _discover_workflow_files(Path("/nonexistent/path"))

    def test_discover_raises_if_no_workflows_dir(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError if .github/workflows doesn't exist."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            _discover_workflow_files(tmp_path)

    def test_discover_raises_if_no_github_dir(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError if .github/workflows doesn't exist."""
        with pytest.raises(FileNotFoundError):
            _discover_workflow_files(tmp_path)

    def test_discover_raises_if_workflows_is_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError if .github/workflows is not a directory."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "workflows").write_text("not a directory")

        with pytest.raises(FileNotFoundError):
            _discover_workflow_files(tmp_path)
