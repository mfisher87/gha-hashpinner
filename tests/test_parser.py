"""Tests for the parser module.

TODO: Reduce distance between mock data and expected values.
"""

from pathlib import Path

import pytest

from gha_hashpinner.parser import (
    _parse_action_specifier,
    _parse_workflow_file,
    find_all_mutable_actions,
)

from .mock_workflows import (
    COMPLEX_WORKFLOW,
    WORKFLOW_WITH_BORDERLINE_YAML,
    WORKFLOW_WITH_COMMENTS,
    WORKFLOW_WITH_IMMUTABLE_PATH_PIN,
    WORKFLOW_WITH_IMMUTABLE_PINS,
    WORKFLOW_WITH_INVALID_YAML,
    WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS,
    WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS,
    WORKFLOW_WITH_MUTABLE_PATH_PIN,
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
                    ("actions", "checkout", None, "v4", "actions/checkout@v4", 8),
                    (
                        "actions",
                        "setup-python",
                        None,
                        "v5",
                        "actions/setup-python@v5",
                        9,
                    ),
                ],
                id="workflow-with-mutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_MUTABLE_PATH_PIN,
                1,
                [
                    (
                        "jupyterlab",
                        "maintainer-tools",
                        "/.github/actions/enforce-label",
                        "v1",
                        "jupyterlab/maintainer-tools/.github/actions/enforce-label@v1",
                        7,
                    )
                ],
                id="workflow-with-immutable-path-pin",
            ),
            pytest.param(
                WORKFLOW_WITH_IMMUTABLE_PINS, 0, [], id="workflow-with-immutable-pins"
            ),
            pytest.param(
                WORKFLOW_WITH_IMMUTABLE_PATH_PIN,
                0,
                [],
                id="workflow-with-immutable-path-pin",
            ),
            pytest.param(
                WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [("actions", "setup-python", None, "v5", "actions/setup-python@v5", 9)],
                id="workflow-with-mutable-and-immutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [("actions", "setup-python", None, "v5", "actions/setup-python@v5", 8)],
                id="workflow-with-quoted-mutable-and-immutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS,
                1,
                [("actions", "checkout", None, "v4", "actions/checkout@v4", 9)],
                id="workflow-with-local-and-docker-actions",
            ),
            pytest.param(
                WORKFLOW_WITH_COMMENTS,
                2,
                [
                    ("actions", "checkout", None, "v4", "actions/checkout@v4", 7),
                    (
                        "actions",
                        "setup-python",
                        None,
                        "v5",
                        "actions/setup-python@v5",
                        8,
                    ),
                ],
                id="workflow-with-comments",
            ),
            pytest.param(
                COMPLEX_WORKFLOW,
                5,
                [
                    ("actions", "checkout", None, "v4", "actions/checkout@v4", 9),
                    ("actions", "setup-node", None, "v3", "actions/setup-node@v3", 12),
                    ("actions", "checkout", None, "v4", "actions/checkout@v4", 20),
                    (
                        "codecov",
                        "codecov-action",
                        None,
                        "v3",
                        "codecov/codecov-action@v3",
                        22,
                    ),
                    ("actions", "deploy", None, "main", "actions/deploy@main", 28),
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
        expected_actions: list[tuple[str, str, str | None, str, str, int]],
    ) -> None:
        """Test each mock workflow is parsed as expected."""
        workflow_file = make_workflow_file(content=workflow_content)
        actions = _parse_workflow_file(workflow_file)

        assert len(actions) == expected_workflow_count
        for index, (owner, repo, subpath, ref, full_string, line_number) in enumerate(
            expected_actions
        ):
            assert actions[index].owner == owner
            assert actions[index].repo == repo
            assert actions[index].subpath == subpath
            assert actions[index].ref == ref
            assert actions[index].full_string == full_string
            assert actions[index].line_number == line_number

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

        actions = _parse_workflow_file(workflow_file)
        assert actions == []


class TestFindAllMutableActions:
    """Test the high-level function that handles both files and directories."""

    def test_find_from_single_file(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
    ) -> None:
        """Should handle a single workflow file."""
        workflow_file = make_workflow_file(content=WORKFLOW_WITH_MUTABLE_PINS)
        result = find_all_mutable_actions(workflow_file)

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

        result = find_all_mutable_actions(mock_root)

        assert len(result) == 2
        assert all(path.parent.name == "workflows" for path in result)

    def test_find_excludes_files_with_no_mutable_actions(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should only return files that have mutable actions."""
        mock_root = make_workflows_dir(
            {
                "mutable.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "immutable.yaml": WORKFLOW_WITH_IMMUTABLE_PINS,
            }
        )

        result = find_all_mutable_actions(mock_root)

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
            find_all_mutable_actions(Path("/nonexistent/path"))


class TestParseActionSpecifier:
    """Test the _parse_action_specifier function."""

    @pytest.mark.parametrize(
        "uses_str",
        [
            pytest.param(
                "owner/repo",
                marks=[
                    pytest.mark.xfail(
                        reason="Specifiers with no pinunsupported (issue #7)",
                    )
                ],
            ),
            "owner/repo@v1",
            "owner/repo/.github/actions/custom@v2",
            "owner/repo/action@some-branch",
            "owner/repo/path/to/custom/action@v1.2.3",
        ],
    )
    def test_parse_uses_str(self, uses_str: str) -> None:
        """Should parse without error."""
        action = _parse_action_specifier(uses_str, line_no=1)
        assert action is not None
        assert action.full_string == uses_str
