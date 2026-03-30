"""Tests for the workflow module.

This module tests the WorkflowFile class's ability to parse workflow files
and extract mutable actions.
"""

from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from gha_hashpinner.workflow import WorkflowFile, _replace_action_in_line

from .helpers import make_immutable_action, make_mutable_action
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


@pytest.fixture
def make_workflow(tmp_path: Path) -> Callable[[str], WorkflowFile]:
    """Make `WorkflowFile` instances from content."""

    def _create(content: str) -> WorkflowFile:
        path = tmp_path / "workflow.yml"
        path.write_text(content)
        return WorkflowFile(path)

    return _create


class TestWorkflowFileMutableActions:
    """Test WorkflowFile.mutable_actions property with various workflow patterns."""

    @pytest.mark.parametrize(
        ("workflow_content", "expected_count", "expected_actions"),
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
                id="mutable-pins",
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
                id="mutable-path-pin",
            ),
            pytest.param(
                WORKFLOW_WITH_IMMUTABLE_PINS,
                0,
                [],
                id="immutable-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_IMMUTABLE_PATH_PIN,
                0,
                [],
                id="immutable-path-pin",
            ),
            pytest.param(
                WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [("actions", "setup-python", None, "v5", "actions/setup-python@v5", 9)],
                id="mixed-mutable-and-immutable",
            ),
            pytest.param(
                WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS,
                1,
                [("actions", "setup-python", None, "v5", "actions/setup-python@v5", 8)],
                id="quoted-mixed-pins",
            ),
            pytest.param(
                WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS,
                1,
                [("actions", "checkout", None, "v4", "actions/checkout@v4", 9)],
                id="local-and-docker-actions",
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
                id="inline-comments",
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
                id="complex-multi-job",
            ),
            pytest.param(
                WORKFLOW_WITH_NO_JOBS,
                0,
                [],
                id="no-jobs",
            ),
            pytest.param(
                WORKFLOW_WITH_BORDERLINE_YAML,
                0,
                [],
                id="borderline-yaml-no-space-after-colon",
            ),
        ],
    )
    def test_parse_workflows(
        self,
        make_workflow: Callable[[str], WorkflowFile],
        workflow_content: str,
        expected_count: int,
        expected_actions: list[tuple[str, str, str | None, str, str, int]],
    ) -> None:
        """Should correctly parse various workflow patterns and extract mutable actions."""
        wf = make_workflow(workflow_content)
        actions = wf.mutable_actions

        assert len(actions) == expected_count

        for index, (owner, repo, subpath, ref, full_string, line_number) in enumerate(
            expected_actions
        ):
            assert actions[index].owner == owner
            assert actions[index].repo == repo
            assert actions[index].subpath == subpath
            assert actions[index].ref == ref
            assert actions[index].full_string == full_string
            assert actions[index].line_number == line_number

    def test_raises_for_invalid_yaml(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should raise ValueError when workflow file contains invalid YAML."""
        with pytest.raises(ValueError, match="Invalid YAML"):
            make_workflow(WORKFLOW_WITH_INVALID_YAML)


class TestWorkflowFileUpdateActions:
    """Test WorkflowFile.update_actions() method."""

    def test_updates_single_action(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should replace mutable pin with immutable SHA and comment."""
        wf = make_workflow(
            dedent("""
                name: Test
                on: push
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@v4
                      - run: echo "Hello"
                      - run: yes
        """).strip()
        )

        sha = "abcd1234" * 5
        immutable = make_immutable_action(
            mutable_origin=make_mutable_action(line_number=7),
            sha=sha,
        )
        wf.update_actions(immutable_actions=[immutable])

        actual = wf.path.read_text()
        expected = dedent(f"""
            name: Test
            on: push
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@{sha}  # v4
                  - run: echo "Hello"
                  - run: yes
        """).strip()

        assert actual == expected

    def test_updates_multiple_actions(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should replace multiple mutable pins in single workflow."""
        wf = make_workflow(
            dedent("""
                name: Test
                on: push
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: "actions/checkout@v4"
                      - uses: actions/setup-python@v5
                      - run: echo "Hello"
                      - run: yes
        """).strip()
        )

        checkout_sha = "abcd1234" * 5
        checkout = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="actions",
                repo="checkout",
                ref="v4",
                line_number=7,
            ),
            sha=checkout_sha,
        )
        python_sha = "defg5678" * 5
        python = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="actions",
                repo="setup-python",
                ref="v5",
                line_number=8,
            ),
            sha=python_sha,
        )

        wf.update_actions(immutable_actions=[checkout, python])

        actual = wf.path.read_text()
        expected = dedent(f"""
            name: Test
            on: push
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: "actions/checkout@{checkout_sha}"  # v4
                  - uses: actions/setup-python@{python_sha}  # v5
                  - run: echo "Hello"
                  - run: yes
        """).strip()
        assert actual == expected

    def test_preserves_various_formatting(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should maintain quotes, indentation, blank lines, and spacing."""
        wf = make_workflow(
            dedent("""
                jobs:
                  test:

                    steps:
                      - uses: "actions/checkout@v4"

                      - uses:   'actions/setup-python@v5'
        """).strip()
        )

        checkout_sha = "abcd1234" * 5
        checkout = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="actions",
                repo="checkout",
                ref="v4",
                line_number=5,
            ),
            sha=checkout_sha,
        )
        python_sha = "defg5678" * 5
        python = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="actions",
                repo="setup-python",
                ref="v5",
                line_number=7,
            ),
            sha=python_sha,
        )

        wf.update_actions(immutable_actions=[checkout, python])

        actual = wf.path.read_text()
        expected = dedent(f"""
            jobs:
              test:

                steps:
                  - uses: "actions/checkout@{checkout_sha}"  # v4

                  - uses:   'actions/setup-python@{python_sha}'  # v5
        """).strip()

        assert actual == expected
        assert len(wf.path.read_text().splitlines(keepends=True)) == len(
            actual.splitlines(keepends=True)
        )

    def test_replaces_existing_comments(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should replace existing inline comments with version comment."""
        wf = make_workflow(
            dedent("""
                jobs:
                  test:
                    steps:
                      - uses: actions/checkout@v4  # Get the code
        """).strip()
        )

        sha = "abcd1234" * 5
        immutable = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="actions",
                repo="checkout",
                ref="v4",
                line_number=4,
            ),
            sha=sha,
        )

        wf.update_actions(immutable_actions=[immutable])

        actual = wf.path.read_text()
        expected = dedent(f"""
            jobs:
              test:
                steps:
                  - uses: actions/checkout@{sha}  # v4
        """).strip()
        assert actual == expected

    def test_noop_with_empty_list(
        self,
        make_workflow: Callable[[str], WorkflowFile],
    ) -> None:
        """Should not modify file when given empty immutable actions list."""
        original = dedent("""
            jobs:
              test:
                steps:
                  - uses: actions/checkout@v4
        """)

        wf = make_workflow(original)
        wf.update_actions(immutable_actions=[])

        assert wf.path.read_text() == original


class TestReplaceActionInLine:
    """Test the `_replace_action_in_line` function."""

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (
                "      - uses: actions/checkout@v4\n",
                "      - uses: actions/checkout@abc123def456abc123def456abc123def456abc1  # v4\n",
            ),
            (
                "  - uses: actions/checkout@v4\n",
                "  - uses: actions/checkout@abc123def456abc123def456abc123def456abc1  # v4\n",
            ),
            (
                "- uses: actions/checkout@v4\n",
                "- uses: actions/checkout@abc123def456abc123def456abc123def456abc1  # v4\n",
            ),
            (
                "    - uses: actions/checkout@v4\n",
                "    - uses: actions/checkout@abc123def456abc123def456abc123def456abc1  # v4\n",
            ),
            (
                "  - uses:   actions/checkout@v4\n",
                "  - uses:   actions/checkout@abc123def456abc123def456abc123def456abc1  # v4\n",
            ),
            (
                '  - uses:   "actions/checkout@v4"\n',
                '  - uses:   "actions/checkout@abc123def456abc123def456abc123def456abc1"  # v4\n',
            ),
            (
                '  - uses: "actions/checkout@v4"\n',
                '  - uses: "actions/checkout@abc123def456abc123def456abc123def456abc1"  # v4\n',
            ),
            (
                "  - uses: 'actions/checkout@v4'\n",
                "  - uses: 'actions/checkout@abc123def456abc123def456abc123def456abc1'  # v4\n",
            ),
            (
                "  - uses: 'actions/checkout@v4'  # old comment\n",
                "  - uses: 'actions/checkout@abc123def456abc123def456abc123def456abc1'  # v4\n",
            ),
        ],
    )
    def test_replace(
        self,
        line: str,
        expected: str,
    ) -> None:
        """Should successfully replace the mutable pin with an immutable one.

        Comments should be replaced. Formatting (i.e. indentation and leading spaces)
        should be unaltered.
        """
        actual = _replace_action_in_line(
            line,
            immutable_action=make_immutable_action(),
        )
        assert actual == expected

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (
                "  - uses: 'jupyterlab/maintainer-tools/.github/actions/enforce-label@v1'\n",
                "  - uses: 'jupyterlab/maintainer-tools/.github/actions/enforce-label@abc123def456abc123def456abc123def456abc1'  # v1\n",
            ),
        ],
    )
    def test_replace_with_subpath(
        self,
        line: str,
        expected: str,
    ) -> None:
        """Should successfully replace mutable pins for actions with subpaths."""
        immutable = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="jupyterlab",
                repo="maintainer-tools",
                subpath="/.github/actions/enforce-label",
                ref="v1",
            ),
            sha="abc123def456abc123def456abc123def456abc1",
        )

        actual = _replace_action_in_line(line, immutable_action=immutable)
        assert actual == expected
