"""Tests for the parser module.

TODO: Reduce distance between mock data and expected values.
"""

from pathlib import Path

import pytest

from gha_hashpinner.parser import (
    _discover_workflow_files,
    _parse_workflow_file,
    find_all_mutable_action_references,
)

from .mock_workflows import (
    COMPLEX_WORKFLOW,
    WORKFLOW_WITH_BORDERLINE_YAML,
    WORKFLOW_WITH_COMMENTS,
    WORKFLOW_WITH_IMMUTABLE_PINS,
    WORKFLOW_WITH_INVALID_YAML,
    WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS,
    WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS,
    WORKFLOW_WITH_MUTABLE_PINS,
    WORKFLOW_WITH_NO_JOBS,
    WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS,
)
from .types import MakeWorkflowFileFunc, MakeWorkflowsDirFunc


class TestParseWorkflowFile:
    """Test parsing individual workflow files."""

    @pytest.mark.parametrize(
        ("workflow_content", "expected_workflow_count", "expected_actions"),
        [
            pytest.param(
                WORKFLOW_WITH_MUTABLE_PINS,
                2,
                [
                    ("actions", "checkout", "v4", "actions/checkout@v4", 8),
                    ("actions", "setup-python", "v5", "actions/setup-python@v5", 9),
                ],
                id="workflow-with-mutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_IMMUTABLE_PINS, 0, [], id="workflow-with-immutable-pins"
            ),
            pytest.param(
                WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [
                    ("actions", "setup-python", "v5", "actions/setup-python@v5", 9),
                ],
                id="workflow-with-mutable-and-immutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [
                    ("actions", "setup-python", "v5", "actions/setup-python@v5", 8),
                ],
                id="workflow-with-quoted-mutable-and-immutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS,
                1,
                [
                    ("actions", "checkout", "v4", "actions/checkout@v4", 9),
                ],
                id="workflow-with-local-and-docker-actions",
            ),
            pytest.param(
                WORKFLOW_WITH_COMMENTS,
                2,
                [
                    ("actions", "checkout", "v4", "actions/checkout@v4", 7),
                    ("actions", "setup-python", "v5", "actions/setup-python@v5", 8),
                ],
                id="workflow-with-comments",
            ),
            pytest.param(
                COMPLEX_WORKFLOW,
                5,
                [
                    ("actions", "checkout", "v4", "actions/checkout@v4", 9),
                    ("actions", "setup-node", "v3", "actions/setup-node@v3", 12),
                    ("actions", "checkout", "v4", "actions/checkout@v4", 20),
                    (
                        "codecov",
                        "codecov-action",
                        "v3",
                        "codecov/codecov-action@v3",
                        22,
                    ),
                    ("actions", "deploy", "main", "actions/deploy@main", 28),
                ],
                id="complex-workflow",
            ),
            pytest.param(WORKFLOW_WITH_NO_JOBS, 0, [], id="workflow-with-no-jobs"),
        ],
    )
    def test_parse_workflows(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        workflow_content: str,
        expected_workflow_count: int,
        expected_actions: list[tuple[str, str, str, str, int]],
    ) -> None:
        """Test each mock workflow is parsed as expected."""
        workflow_file = make_workflow_file(content=workflow_content)
        refs = _parse_workflow_file(workflow_file)

        assert len(refs) == expected_workflow_count
        for index, (owner, repo, ref, full_string, line_number) in enumerate(
            expected_actions
        ):
            assert refs[index].owner == owner
            assert refs[index].repo == repo
            assert refs[index].ref == ref
            assert refs[index].full_string == full_string
            assert refs[index].line_number == line_number

    def test_parse_invalid_yaml(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
    ) -> None:
        """Should raise ValueError for invalid YAML."""
        workflow_file = make_workflow_file(content=WORKFLOW_WITH_INVALID_YAML)

        with pytest.raises(ValueError, match="Invalid YAML"):
            _parse_workflow_file(workflow_file)

    def test_parse_borderline_yaml(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
    ) -> None:
        """Should fail to find a `uses:` key if it's not followed by a space.

        The YAML value `uses:foo` is read as a string.
        """
        workflow_file = make_workflow_file(content=WORKFLOW_WITH_BORDERLINE_YAML)

        refs = _parse_workflow_file(workflow_file)
        assert refs == []


class TestDiscoverWorkflowFiles:
    """Test discovering workflow files in a directory."""

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
        assert all(f.suffix in [".yml", ".yaml"] for f in files)

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

        assert files[0].name == "a.yaml"
        assert files[1].name == "m.yml"
        assert files[2].name == "z.yml"

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
        assert files[0].name == "test.yml"

    def test_discover_returns_empty_if_workflows_dir_empty(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should return an empty list if .github/workflows is empty."""
        mock_root = make_workflows_dir({})

        files = _discover_workflow_files(mock_root)
        assert files == []

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


class TestFindAllActionReferences:
    """Test the high-level function that handles both files and directories."""

    def test_find_from_single_file(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
    ) -> None:
        """Should handle a single workflow file."""
        workflow_file = make_workflow_file(content=WORKFLOW_WITH_MUTABLE_PINS)
        result = find_all_mutable_action_references(workflow_file)

        assert len(result) == 1
        assert workflow_file in result
        assert len(result[workflow_file]) == 2

    def test_find_from_directory(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should find all workflows in a directory."""
        mock_root = make_workflows_dir(
            {
                "simple.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "complex.yaml": COMPLEX_WORKFLOW,
            }
        )

        result = find_all_mutable_action_references(mock_root)

        assert len(result) == 2
        assert all(path.parent.name == "workflows" for path in result)

    def test_find_excludes_files_with_no_mutable_refs(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should only return files that have mutable references."""
        mock_root = make_workflows_dir(
            {
                "mutable.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "immutable.yaml": WORKFLOW_WITH_IMMUTABLE_PINS,
            }
        )

        result = find_all_mutable_action_references(mock_root)

        assert len(result) == 2

        immutable_path, immutable_items = list(result.items())[0]
        assert immutable_path.name == "immutable.yaml"
        assert immutable_items == []

        mutable_path, mutable_items = list(result.items())[1]
        assert mutable_path.name == "mutable.yml"
        assert len(mutable_items) == 2

    def test_find_raises_for_nonexistent_path(self) -> None:
        """Should raise FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            find_all_mutable_action_references(Path("/nonexistent/path"))
