"""End-to-end tests of the pinning behavior."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gha_hashpinner.exceptions import CheckFailedError
from gha_hashpinner.pinner import pin

from .helpers import make_repo_mock
from .mock_workflows import (
    WORKFLOW_WITH_IMMUTABLE_PINS,
    WORKFLOW_WITH_MUTABLE_PINS,
)
from .types import MakeWorkflowsDirFunc

patch_gh_client = patch("gha_hashpinner.resolver.Github")


class TestPinEndToEnd:
    """End-to-end tests for the pin function."""

    @patch_gh_client
    def test_pin_single_workflow_file(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should update a single workflow file with hash pins."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_MUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"

        sha_checkout = "abc1111111111111111111111111111111111111111"
        sha_python = "def2222222222222222222222222222222222222222"
        mock_gh_cls.return_value.get_repo.side_effect = [
            make_repo_mock(branch_sha=sha_checkout),
            make_repo_mock(branch_sha=sha_python),
        ]

        pin(path=project_root, token="fake-token", dry_run=False, check=False)

        actual = workflow_file.read_text()
        assert f"actions/checkout@{sha_checkout}  # v4" in actual
        assert f'"actions/setup-python@{sha_python}"  # v5' in actual

    @patch_gh_client
    def test_pin_multiple_workflow_files(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should update multiple workflow files."""
        project_root = make_workflows_dir(
            {
                "test1.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "test2.yml": WORKFLOW_WITH_MUTABLE_PINS,
            }
        )

        sha = "fedcba12" * 5
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        pin(path=project_root, token="fake-token", dry_run=False, check=False)

        workflows_dir = project_root / ".github" / "workflows"
        for filename in ["test1.yml", "test2.yml"]:
            actual = (workflows_dir / filename).read_text()
            assert f'@{sha}"  # v' in actual
            assert f"@{sha}  # v" in actual

    @patch_gh_client
    def test_pin_dry_run_no_changes(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should not modify files in dry-run mode."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_MUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"
        expected = workflow_file.read_text()

        mock_repo = make_repo_mock(branch_sha="abcd1234" * 5)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        pin(path=project_root, token="fake-token", dry_run=True, check=False)

        assert workflow_file.read_text() == expected

    def test_pin_no_mutable_actions_succeeds(
        self,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should not raise when no mutable actions found."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_IMMUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"
        expected = workflow_file.read_text()

        pin(path=project_root, token="fake-token", dry_run=False, check=False)

        assert workflow_file.read_text() == expected

    @patch_gh_client
    def test_pin_check_mode_raises(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should modify the file and raise CheckFailedError in check mode when mutable actions found."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_MUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"
        original_content = workflow_file.read_text()

        mock_repo = make_repo_mock(branch_sha="abcd1234" * 5)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        with pytest.raises(CheckFailedError):
            pin(path=project_root, token="fake-token", dry_run=False, check=True)

        assert workflow_file.read_text() != original_content

    @patch_gh_client
    def test_pin_dry_run_and_check_mode_raise_no_changes(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should raise CheckFailedError without modifying in check+dry-run mode when mutable actions found."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_MUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"
        expected = workflow_file.read_text()

        mock_repo = make_repo_mock(branch_sha="abcd1234" * 5)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        with pytest.raises(CheckFailedError):
            pin(path=project_root, token="fake-token", dry_run=True, check=True)

        assert workflow_file.read_text() == expected

    @patch_gh_client
    def test_pin_specific_workflow_file(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should only modify single requested workflow file."""
        project_root = make_workflows_dir(
            {
                "target.yml": WORKFLOW_WITH_MUTABLE_PINS,
                "other.yml": WORKFLOW_WITH_MUTABLE_PINS,
            }
        )
        target_file = project_root / ".github" / "workflows" / "target.yml"
        other_file = project_root / ".github" / "workflows" / "other.yml"
        original_other_content = other_file.read_text()
        sha = "abcd1234" * 5

        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        pin(path=target_file, token="fake-token", dry_run=False, check=False)

        assert f"@{sha}" in target_file.read_text()
        assert other_file.read_text() == original_other_content

    def test_pin_invalid_path_raises(self) -> None:
        """Should raise FileNotFoundError for invalid path."""
        with pytest.raises(FileNotFoundError):
            pin(
                path=Path("/nonexistent/path"),
                token="fake-token",
                dry_run=False,
                check=False,
            )

    @patch_gh_client
    def test_pin_without_token(
        self,
        mock_gh_cls: Mock,
        make_workflows_dir: MakeWorkflowsDirFunc,
    ) -> None:
        """Should work without authentication token."""
        project_root = make_workflows_dir({"test.yml": WORKFLOW_WITH_MUTABLE_PINS})
        workflow_file = project_root / ".github" / "workflows" / "test.yml"

        sha = "abcd1234" * 5
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        pin(path=project_root, token=None, dry_run=False, check=False)

        assert f"@{sha}" in workflow_file.read_text()
