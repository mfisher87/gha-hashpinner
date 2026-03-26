"""Tests for the parser module.

TODO: Reduce distance between mock data and expected values.
"""

from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import NotRequired, TypedDict, Unpack

import pytest

from gha_hashpinner.parser import (
    ACTION_PATTERN,
    SHA_PATTERN,
    _discover_workflow_files,
    _parse_workflow_file,
    find_all_mutable_action_references,
)

WORKFLOW_WITH_MUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                # One quoted, one not
                - uses: actions/checkout@v4
                - uses: "actions/setup-python@v5"
""").strip()

WORKFLOW_WITH_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                # One quoted, one not
                - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
                - uses: "actions/setup-python@deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"  #v5
""").strip()


WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
                - uses: actions/setup-python@v5
""").strip()


WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: 'actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3'  # v4
                - uses: 'actions/setup-python@v5'
""").strip()


WORKFLOW_WITH_COMMENTS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: actions/checkout@v4  # Checkout
                - uses: "actions/setup-python@v5" # Setup Python
""").strip()


WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
            - uses: "./local-action"
            - uses: docker://alpine:latest
            - uses: actions/checkout@v4
""").strip()


COMPLEX_WORKFLOW = dedent("""
    name: "Complex Test"
    on: [push, pull_request]

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
            - name: "Checkout"
              uses: actions/checkout@v4

            - name: "Setup Node"
              uses: actions/setup-node@v3

            - name: "Local action"
              uses: ./github/actions/custom

      test:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
            - uses: docker://node:18
            - uses: codecov/codecov-action@v3

      deploy:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
            - uses: actions/deploy@main
""").strip()


WORKFLOW_WITH_NO_JOBS = dedent("""
    name: Test
    on: push
    jobs: {}
""").strip()


WORKFLOW_WITH_BORDERLINE_YAML = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        steps:
          - uses:actions/checkout@v4
""").strip()


WORKFLOW_WITH_INVALID_YAML = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        steps:
          - uses: actions/checkout@v4
        invalid: [unclosed list
""").strip()


class MakeWorkflowFileArgs(TypedDict):
    content: str
    name: NotRequired[str]


# Ugh
type MakeWorkflowFileFunc = Callable[[Unpack[MakeWorkflowFileArgs]], Path]


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


# Ugh
type MakeWorkflowsDirFunc = Callable[[dict[str, str]], Path]


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


class TestPatterns:
    """Test regex patterns."""

    @pytest.mark.parametrize(
        "uses_str",
        [
            "actions/checkout@v4",
            "astral-sh/setup-uv@v7",
            "owner/repo@main",
            "owner/repo@v1.2.3",
            "my-org/my-action@release-branch",
        ],
    )
    def test_action_pattern_matches_valid_action(self, uses_str: str) -> None:
        """ACTION_PATTERN should match "uses:" values matching actions on GitHub."""
        assert ACTION_PATTERN.match(uses_str)

    def test_action_patern_captures_groups(self) -> None:
        """ACTION_PATTERN should capture groups from "uses:" value."""
        match = ACTION_PATTERN.match("actions/checkout@v4")
        assert match is not None
        assert match.group("owner") == "actions"
        assert match.group("repo") == "checkout"
        assert match.group("ref") == "v4"

    @pytest.mark.parametrize(
        "uses_str",
        [
            "./local-action",
            "docker://alpine:latest",
            "just-a-string",
            "actions/checkout",
        ],
    )
    def test_action_pattern_rejects(self, uses_str: str) -> None:
        """ACTION_PATTERN should reject local, docker, and invalid "uses" values."""
        assert not ACTION_PATTERN.match(uses_str)

    @pytest.mark.parametrize(
        "sha",
        [
            "8f4b7f84864484a7bf31766abe9204da3cbe65b3",
            "0123456789abcdef0123456789abcdef01234567",
            "baddadbaddadbaddadbaddadbaddadbaddadbadd",
            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        ],
    )
    def test_sha_pattern_matches_valid_sha(self, sha: str) -> None:
        """SHA_PATTERN should match 40-character hexadecimal strings."""
        assert SHA_PATTERN.match(sha)

    @pytest.mark.parametrize(
        "sha",
        [
            "v4",
            "main",
            "8f4b7f8",  # Too short
            "8f4b7f84864484a7bf31766abe9204da3cbe65b3a",  # Too long
            "gggggggggggggggggggggggggggggggggggggggg",  # "g" is not valid hexadecimal
        ],
    )
    def test_sha_pattern_rejects_invalid(self, sha: str) -> None:
        """SHA_PATTERN should reject non-SHA strings."""
        assert not SHA_PATTERN.match(sha)


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
                    ("actions", "setup-python", "v5", "actions/setup-python@v5", 8),
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
