"""Tests for the resolver module."""

from unittest.mock import Mock, patch

import pytest
from github import GithubException, UnknownObjectException

from gha_hashpinner.exceptions import NoGitRefFoundError, NoGitRepoFoundError
from gha_hashpinner.resolver import Resolver

from .helpers import make_mutable_action, make_repo_mock


@pytest.fixture
def resolver() -> Resolver:
    """Create a Resolver instance for testing."""
    return Resolver(token="fake-token")


class TestResolverResolve:
    """Test Resolver.resolve() method - the main public API."""

    @patch("gha_hashpinner.resolver.Github")
    def test_resolves_branch_to_sha(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should resolve a branch ref to its commit SHA."""
        sha = "abc123def456abc123def456abc123def456abc123"
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        mutable = make_mutable_action(ref="main")
        immutable = resolver.resolve(mutable)

        assert immutable.sha == sha
        assert immutable.comment == "main"
        assert immutable.mutable_origin == mutable

    @patch("gha_hashpinner.resolver.Github")
    def test_resolves_tag_to_sha(self, mock_gh_cls: Mock, resolver: Resolver) -> None:
        """Should resolve a tag ref when branch doesn't exist."""
        sha = "tag123def456abc123def456abc123def456abc123"
        mock_repo = make_repo_mock(
            branch_error=UnknownObjectException(404, "Not Found"),
            tag_sha=sha,
        )
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        mutable = make_mutable_action(ref="v1.0.0")
        immutable = resolver.resolve(mutable)

        assert immutable.sha == sha
        assert immutable.comment == "v1.0.0"
        assert immutable.mutable_origin == mutable

    @patch("gha_hashpinner.resolver.Github")
    def test_resolves_annotated_tag(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should handle annotated tags (tag objects that point to commits)."""
        sha = "annotated123abc123def456abc123def456abc123"
        mock_repo = make_repo_mock(
            branch_error=UnknownObjectException(404, "Not Found"),
            annotated_tag_sha=sha,
        )
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        mutable = make_mutable_action(ref="v2.0.0")
        immutable = resolver.resolve(mutable)

        assert immutable.sha == sha
        assert immutable.comment == "v2.0.0"
        assert immutable.mutable_origin == mutable

    @patch("gha_hashpinner.resolver.Github")
    def test_uses_cache_for_duplicate_refs(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should cache resolution results to minimize GitHub API calls."""
        sha = "cached123def456abc123def456abc123def456abc"
        mock_repo = make_repo_mock(branch_sha=sha)
        mock_gh_instance = mock_gh_cls.return_value
        mock_gh_instance.get_repo.return_value = mock_repo

        mutable = make_mutable_action()

        resolver.resolve(mutable)
        resolver.resolve(mutable)

        # Should only be called once, despite two resolutions above, thanks to cache:
        mock_gh_instance.get_repo.assert_called_once()

    @patch("gha_hashpinner.resolver.Github")
    def test_cache_key_includes_owner_repo_ref(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should cache separately for different owner/repo/ref combinations."""
        sha1 = "sha1111111111111111111111111111111111111111"
        sha2 = "sha2222222222222222222222222222222222222222"

        mock_repo1 = make_repo_mock(branch_sha=sha1)
        mock_repo2 = make_repo_mock(branch_sha=sha2)
        mock_gh_cls.return_value.get_repo.side_effect = [mock_repo1, mock_repo2]

        action1 = make_mutable_action(repo="checkout", ref="v4")
        action2 = make_mutable_action(repo="setup-python", ref="v5")

        result1 = resolver.resolve(action1)
        result2 = resolver.resolve(action2)

        assert result1.sha == sha1
        assert result2.sha == sha2

        # Should be called twice because the owner/repo/ref key differs
        assert mock_gh_cls.return_value.get_repo.call_count == 2

    @patch("gha_hashpinner.resolver.Github")
    def test_raises_on_nonexistent_repo(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should raise NoGitRepoFoundError for nonexistent repositories."""
        not_found = UnknownObjectException(404, "Not Found")
        mock_gh_cls.return_value.get_repo.side_effect = not_found

        mutable = make_mutable_action(owner="fake", repo="nonexistent")

        with pytest.raises(NoGitRepoFoundError, match="not found on GitHub"):
            resolver.resolve(mutable)

    @patch("gha_hashpinner.resolver.Github")
    def test_raises_on_nonexistent_ref(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should raise NoGitRefFoundError when ref doesn't exist as branch or tag."""
        not_found = UnknownObjectException(404, "Not Found")
        mock_repo = make_repo_mock(
            branch_error=not_found,
            tag_error=not_found,
        )
        mock_gh_cls.return_value.get_repo.return_value = mock_repo

        mutable = make_mutable_action(ref="nonexistent-ref")

        with pytest.raises(
            NoGitRefFoundError,
            match="not found on GitHub as a tag or branch",
        ):
            resolver.resolve(mutable)

    @patch("gha_hashpinner.resolver.Github")
    def test_propagates_github_api_errors(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should allow GitHub API errors (rate limit, etc.) to propagate."""
        mock_gh_cls.return_value.get_repo.side_effect = GithubException(
            429, "Rate limit exceeded"
        )

        mutable = make_mutable_action()

        with pytest.raises(GithubException, match="Rate limit"):
            resolver.resolve(mutable)


class TestResolverClient:
    """Test Resolver.client property (lazy loading behavior)."""

    @patch("gha_hashpinner.resolver.Github")
    def test_lazy_loads_client_with_token(self, mock_gh_cls: Mock) -> None:
        """Should instantiate GitHub client with token on first access."""
        resolver = Resolver(token="my-secret-token")
        assert resolver._client is None

        _ = resolver.client
        mock_gh_cls.assert_called_once_with("my-secret-token")

    @patch("gha_hashpinner.resolver.Github")
    def test_lazy_loads_client_without_token(self, mock_gh_cls: Mock) -> None:
        """Should instantiate anonymous GitHub client when no token provided."""
        resolver = Resolver()

        _ = resolver.client
        mock_gh_cls.assert_called_once_with()

    @patch("gha_hashpinner.resolver.Github")
    def test_client_reuses_instance(
        self,
        mock_gh_cls: Mock,
        resolver: Resolver,
    ) -> None:
        """Should return same client instance on repeated access."""
        client1 = resolver.client
        client2 = resolver.client

        assert client1 is client2
        mock_gh_cls.assert_called_once()
