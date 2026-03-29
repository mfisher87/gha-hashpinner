"""Tests for the updater module."""

from dataclasses import replace
from textwrap import dedent

import pytest

from gha_hashpinner.models import ImmutableAction
from gha_hashpinner.updater import _replace_action_in_line, update_workflow_file

from .types import MakeWorkflowFileFunc


class TestReplaceActionInLine:
    """Test the `_replace_action_in_line` function."""

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (
                "      - uses: actions/checkout@v4\n",
                "      - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4\n",
            ),
            (
                "  - uses: actions/checkout@v4\n",
                "  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4\n",
            ),
            (
                "- uses: actions/checkout@v4\n",
                "- uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4\n",
            ),
            (
                "    - uses: actions/checkout@v4\n",
                "    - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4\n",
            ),
            (
                "  - uses:   actions/checkout@v4\n",
                "  - uses:   actions/checkout@abc123def456abc123def456abc123def456abc123  # v4\n",
            ),
            (
                '  - uses:   "actions/checkout@v4"\n',
                '  - uses:   "actions/checkout@abc123def456abc123def456abc123def456abc123"  # v4\n',
            ),
            (
                '  - uses: "actions/checkout@v4"\n',
                '  - uses: "actions/checkout@abc123def456abc123def456abc123def456abc123"  # v4\n',
            ),
            (
                "  - uses: 'actions/checkout@v4'\n",
                "  - uses: 'actions/checkout@abc123def456abc123def456abc123def456abc123'  # v4\n",
            ),
            (
                "  - uses: 'actions/checkout@v4'  # old comment\n",
                "  - uses: 'actions/checkout@abc123def456abc123def456abc123def456abc123'  # v4\n",
            ),
        ],
    )
    def test_replace(
        self,
        mock_immutable_action_checkout: ImmutableAction,
        line: str,
        expected: str,
    ) -> None:
        """Should successfully replace the mutable pin with an immutable one.

        Comments should be replaced. Formatting (i.e. indentation and leading spaces)
        should be unaltered.
        """
        actual = _replace_action_in_line(
            line,
            immutable_action=mock_immutable_action_checkout,
        )
        assert actual == expected

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (
                "  - uses: 'jupyterlab/maintainer-tools/.github/actions/enforce-label@v1'\n",
                "  - uses: 'jupyterlab/maintainer-tools/.github/actions/enforce-label@123abc123abc123abc123abc123abc123abc123abc'  # v1\n",
            ),
        ],
    )
    def test_replace_with_subpath(
        self,
        mock_immutable_action_enforcelabel: ImmutableAction,
        line: str,
        expected: str,
    ) -> None:
        """Should successfully replace mutable pins for actions with subpaths."""
        actual = _replace_action_in_line(
            line,
            immutable_action=mock_immutable_action_enforcelabel,
        )
        assert actual == expected


class TestUpdateWorkflowFile:
    """Test the `update_workflow_file` function."""

    def test_update_single_action(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
    ) -> None:
        """Should update a single action specifier."""
        content = dedent("""
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

        workflow = make_workflow_file(content=content)
        update_workflow_file(
            workflow,
            immutable_actions=[mock_immutable_action_checkout],
        )

        actual = workflow.read_text()
        expected = dedent("""
            name: Test
            on: push
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4
                  - run: echo "Hello"
                  - run: yes
        """).strip()

        assert actual == expected

    def test_update_multiple_actions(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
        mock_immutable_action_python: ImmutableAction,
    ) -> None:
        """Should update multiple action specifiers."""
        content = dedent("""
            name: Test
            on: push
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                  - run: echo "Hello"
                  - run: yes
        """).strip()

        workflow = make_workflow_file(content=content)
        update_workflow_file(
            workflow,
            immutable_actions=[
                mock_immutable_action_checkout,
                mock_immutable_action_python,
            ],
        )

        actual = workflow.read_text()
        expected = dedent("""
            name: Test
            on: push
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4
                  - uses: actions/setup-python@def456abc123def456abc123def456abc123def456  # v5
                  - run: echo "Hello"
                  - run: yes
        """).strip()
        assert actual == expected

    def test_update_with_empty_specifiers_list(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
    ) -> None:
        """Should not modify file when immutable action specifiers list is empty."""
        content = dedent("""
            name: Test
            on: push
            jobs:
              test:
                steps:
                  - uses: actions/checkout@v4
        """).strip()

        workflow = make_workflow_file(content=content)
        original_content = workflow.read_text()

        update_workflow_file(workflow, immutable_actions=[])

        assert workflow.read_text() == original_content

    def test_update_with_quoted_actions(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
        mock_immutable_action_python: ImmutableAction,
    ) -> None:
        """Should handle differently-quoted action specifiers."""
        content = dedent("""
            name: Test
            jobs:
              test:
                steps:
                  - uses: "actions/checkout@v4"
                  - uses: 'actions/setup-python@v5'
        """).strip()
        mock_immutable_action_checkout = replace(
            mock_immutable_action_checkout,
            mutable_origin=replace(
                mock_immutable_action_checkout.mutable_origin,
                line_number=5,
            ),
        )
        mock_immutable_action_python = replace(
            mock_immutable_action_python,
            mutable_origin=replace(
                mock_immutable_action_python.mutable_origin,
                line_number=6,
            ),
        )

        workflow = make_workflow_file(content=content)

        update_workflow_file(
            workflow,
            immutable_actions=[
                mock_immutable_action_checkout,
                mock_immutable_action_python,
            ],
        )

        actual = workflow.read_text()
        expected = dedent("""
            name: Test
            jobs:
              test:
                steps:
                  - uses: "actions/checkout@abc123def456abc123def456abc123def456abc123"  # v4
                  - uses: 'actions/setup-python@def456abc123def456abc123def456abc123def456'  # v5
        """).strip()

        assert actual == expected

    def test_update_preserves_file_structure(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
    ) -> None:
        """Should preserve blank lines and overall file structure."""
        content = dedent("""
            name: Test

            on: push

            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4

                  - run: echo "test"
        """).strip()
        mock_immutable_action_checkout = replace(
            mock_immutable_action_checkout,
            mutable_origin=replace(
                mock_immutable_action_checkout.mutable_origin,
                line_number=9,
            ),
        )

        workflow = make_workflow_file(content=content)
        original_lines = content.splitlines(keepends=True)

        update_workflow_file(
            workflow,
            immutable_actions=[mock_immutable_action_checkout],
        )

        actual = workflow.read_text()
        actual_lines = actual.splitlines(keepends=True)
        expected = dedent("""
            name: Test

            on: push

            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4

                  - run: echo "test"
        """).strip()

        assert actual == expected
        assert len(actual_lines) == len(original_lines)

    def test_update_multiple_actions_same_workflow(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
        mock_immutable_action_python: ImmutableAction,
    ) -> None:
        """Should handle multiple different actions in same workflow."""
        content = dedent("""
            name: Complex
            jobs:
              build:
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
              test:
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
        """).strip()
        spec1 = replace(
            mock_immutable_action_checkout,
            mutable_origin=replace(
                mock_immutable_action_checkout.mutable_origin,
                line_number=5,
            ),
        )
        spec2 = replace(
            mock_immutable_action_python,
            mutable_origin=replace(
                mock_immutable_action_python.mutable_origin,
                line_number=6,
            ),
        )
        spec3 = replace(
            mock_immutable_action_checkout,
            mutable_origin=replace(
                mock_immutable_action_checkout.mutable_origin,
                line_number=9,
            ),
        )
        spec4 = replace(
            mock_immutable_action_python,
            mutable_origin=replace(
                mock_immutable_action_python.mutable_origin,
                line_number=10,
            ),
        )

        workflow = make_workflow_file(content=content)

        update_workflow_file(
            workflow,
            immutable_actions=[spec1, spec2, spec3, spec4],
        )

        actual = workflow.read_text()
        expected = dedent("""
            name: Complex
            jobs:
              build:
                steps:
                  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4
                  - uses: actions/setup-python@def456abc123def456abc123def456abc123def456  # v5
              test:
                steps:
                  - uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4
                  - uses: actions/setup-python@def456abc123def456abc123def456abc123def456  # v5
        """).strip()

        assert actual == expected

    def test_update_replaces_existing_comments(
        self,
        make_workflow_file: MakeWorkflowFileFunc,
        mock_immutable_action_checkout: ImmutableAction,
    ) -> None:
        """Should replace existing comments with version comment."""
        content = dedent("""
            name: Test
            jobs:
              test:
                steps:
                  - name: "Checkout"
                    uses: actions/checkout@v4  # Get the code
        """).strip()
        mock_immutable_action_checkout = replace(
            mock_immutable_action_checkout,
            mutable_origin=replace(
                mock_immutable_action_checkout.mutable_origin,
                line_number=6,
            ),
        )

        workflow = make_workflow_file(content=content)
        update_workflow_file(
            workflow,
            immutable_actions=[mock_immutable_action_checkout],
        )

        actual = workflow.read_text()
        expected = dedent("""
            name: Test
            jobs:
              test:
                steps:
                  - name: "Checkout"
                    uses: actions/checkout@abc123def456abc123def456abc123def456abc123  # v4
        """).strip()
        assert actual == expected
