"""Tests for the resolver module."""

from unittest.mock import Mock, patch

import pytest
from github import GithubException, UnknownObjectException

from gha_hashpinner.models import MutableAction
from gha_hashpinner.resolver import (
    _resolve_ref_to_commit_sha,
    resolve_action_references,
)

from .helpers import make_repo_mock

patch_gh_client = patch("gha_hashpinner.resolver.Github")


class TestResolveMutableActions:
    """Test the main resolve_action_references function."""

    @patch_gh_client
    def test_resolve_single_action(
        self,
        mock_gh_cls: Mock,
        mock_action_ref_checkout: MutableAction,
    ) -> None:
        """Should resolve a single action reference."""
        sha = "abc123def456abc123def456abc123def456abc1"
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        results = resolve_action_references(
            [mock_action_ref_checkout],
            token="fake-token",
        )

        assert len(results) == 1
        assert results[0].sha == sha
        assert results[0].comment == mock_action_ref_checkout.ref
        assert results[0].mutable_origin == mock_action_ref_checkout

    @patch_gh_client
    def test_resolve_multiple_actions(
        self,
        mock_gh_cls: Mock,
        mock_action_ref_checkout: MutableAction,
        mock_action_ref_python: MutableAction,
    ) -> None:
        """Should resolve multiple action references."""
        sha1 = "sha1111111111111111111111111111111111111111"
        sha2 = "sha2222222222222222222222222222222222222222"
        mock_repo1 = make_repo_mock(branch_sha=sha1)
        mock_repo2 = make_repo_mock(branch_sha=sha2)

        # FIXME: Shouldn't this be .return_value?
        mock_gh_cls.return_value.get_repo.side_effect = [mock_repo1, mock_repo2]

        results = resolve_action_references(
            [mock_action_ref_checkout, mock_action_ref_python],
            token="fake-token",
        )

        # Assert
        assert len(results) == 2
        assert results[0].sha == sha1
        assert results[0].mutable_origin == mock_action_ref_checkout
        assert results[1].sha == sha2
        assert results[1].mutable_origin == mock_action_ref_python

    @patch_gh_client
    def test_resolve_with_cache(
        self,
        mock_gh_cls: Mock,
        mock_action_ref_checkout: MutableAction,
    ) -> None:
        """Should cache duplicate repo/ref combinations."""
        sha = "cached123456789012345678901234567890123456"
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_instance = mock_gh_cls.return_value
        mock_gh_instance.get_repo.return_value = mock_repo

        results = resolve_action_references(
            [mock_action_ref_checkout, mock_action_ref_checkout],
            token="fake-token",
        )

        assert len(results) == 2
        mock_gh_instance.get_repo.assert_called_once()

    @patch_gh_client
    def test_resolve_skips_failures(
        self,
        mock_gh_cls: Mock,
        mock_action_ref_checkout: MutableAction,
        mock_action_ref_python: MutableAction,
    ) -> None:
        """Should skip actions that fail to resolve."""
        sha = "success1234567890123456789012345678901234"
        mock_repo = make_repo_mock(branch_sha=sha)

        # First repo exists, second doesn't
        mock_gh_cls.return_value.get_repo.side_effect = [
            mock_repo,
            UnknownObjectException(404, "NotFound"),
        ]

        with pytest.raises(UnknownObjectException):
            resolve_action_references(
                [mock_action_ref_checkout, mock_action_ref_python],
                token="fake-token",
            )

    @patch_gh_client
    def test_resolve_without_token(
        self,
        mock_gh_cls: Mock,
        mock_action_ref_checkout: MutableAction,
    ) -> None:
        """Should work without authentication token."""
        sha = "notoken1234567890123456789012345678901234"
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        results = resolve_action_references([mock_action_ref_checkout])

        mock_gh_cls.assert_called_once_with()
        assert len(results) == 1
        assert results[0].sha == sha


class TestResolveRefToCommitSha:
    """Test the _resolve_ref_to_commit_sha helper function."""

    def test_resolve_branch(self, mock_action_ref_checkout: MutableAction) -> None:
        """Should resolve a branch reference."""
        sha = "branch1234567890123456789012345678901234"
        mock_gh = Mock()
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh.get_repo.return_value = mock_repo

        result_sha = _resolve_ref_to_commit_sha(
            gh=mock_gh,
            owner=mock_action_ref_checkout.owner,
            repo=mock_action_ref_checkout.repo,
            ref=mock_action_ref_checkout.ref,
        )

        assert result_sha == "branch1234567890123456789012345678901234"
        mock_gh.get_repo.assert_called_once_with(
            f"{mock_action_ref_checkout.owner}/{mock_action_ref_checkout.repo}"
        )
        mock_repo.get_branch.assert_called_once_with("v4")

    def test_resolve_tag(self, mock_action_ref_checkout: MutableAction) -> None:
        """Should resolve a tag reference."""
        sha = "tag1231234567890123456789012345678901234"
        mock_gh = Mock()
        mock_repo = make_repo_mock(
            branch_error=UnknownObjectException(404, "Not Found"),
            tag_sha=sha,
        )
        mock_gh.get_repo.return_value = mock_repo

        result_sha = _resolve_ref_to_commit_sha(
            gh=mock_gh,
            owner=mock_action_ref_checkout.owner,
            repo=mock_action_ref_checkout.repo,
            ref=mock_action_ref_checkout.ref,
        )

        assert result_sha == sha
        mock_repo.get_git_ref.assert_called_once_with("tags/v4")

    def test_resolve_annotated_tag(
        self, mock_action_ref_checkout: MutableAction
    ) -> None:
        """Should handle annotated tags that point to tag objects."""
        sha = "annotatedtag7890123456789012345678901234"
        mock_gh = Mock()
        mock_repo = make_repo_mock(
            branch_error=UnknownObjectException(404, "Not Found"),
            annotated_tag_sha=sha,
        )
        mock_gh.get_repo.return_value = mock_repo

        result_sha = _resolve_ref_to_commit_sha(
            gh=mock_gh,
            owner=mock_action_ref_checkout.owner,
            repo=mock_action_ref_checkout.repo,
            ref=mock_action_ref_checkout.ref,
        )

        assert result_sha == sha
        # FIXME: What is this string??
        mock_repo.get_git_tag.assert_called_once_with("tag_object_sha")

    def test_resolve_nonexistent_repo(
        self, mock_action_ref_checkout: MutableAction
    ) -> None:
        """Should raise UnknownObjectException for nonexistent repository."""
        mock_gh = Mock()
        mock_gh.get_repo.side_effect = UnknownObjectException(404, "Not Found")

        with pytest.raises(UnknownObjectException):
            _resolve_ref_to_commit_sha(
                gh=mock_gh,
                owner=mock_action_ref_checkout.owner,
                repo=mock_action_ref_checkout.repo,
                ref=mock_action_ref_checkout.ref,
            )

    def test_resolve_api_error(self, mock_action_ref_checkout: MutableAction) -> None:
        """Should raise GithubException on GitHub API errors."""
        mock_gh = Mock()
        mock_gh.get_repo.side_effect = GithubException(429, "Rate limit exceeded")

        with pytest.raises(GithubException):
            _resolve_ref_to_commit_sha(
                gh=mock_gh,
                owner=mock_action_ref_checkout.owner,
                repo=mock_action_ref_checkout.repo,
                ref=mock_action_ref_checkout.ref,
            )

    def test_resolve_nonexistent_ref(
        self, mock_action_ref_checkout: MutableAction
    ) -> None:
        """Should raise ValueError when ref doesn't exist as branch or tag."""
        mock_gh = Mock()
        not_found = UnknownObjectException(404, "Not Found")
        mock_repo = make_repo_mock(
            branch_error=not_found,
            tag_error=not_found,
        )
        mock_gh.get_repo.return_value = mock_repo

        with pytest.raises(ValueError, match="was not found on GitHub"):
            _resolve_ref_to_commit_sha(
                gh=mock_gh,
                owner=mock_action_ref_checkout.owner,
                repo=mock_action_ref_checkout.repo,
                ref=mock_action_ref_checkout.ref,
            )
