"""Resolves mutable pins to immutable pins by querying the GitHub API."""

from github import Github, UnknownObjectException
from github.Repository import Repository

from gha_hashpinner.action import ImmutableAction, MutableAction
from gha_hashpinner.exceptions import NoGitRefFoundError, NoGitRepoFoundError


class Resolver:
    """Resolves mutable actions to immutable actions using GitHub API.

    Caches resolution results on `(owner, repo, ref)` to limit GH API calls and make
    best effort to avoid rate limiting.

    """

    token: str | None
    _cache: dict[tuple[str, str, str], str]
    _client: Github | None
    _gh_api_requests_count: int

    def __init__(self, *, token: str | None = None) -> None:
        """Initiatilize a resolver with an optional token."""
        self.token = token
        self._cache = {}
        self._client = None
        self._gh_api_requests_count = 0

    @property
    def client(self) -> Github:
        """Lazy-instantiated `pygithub.Github` client."""
        if self._client is None:
            self._client = Github(self.token) if self.token else Github()
        return self._client

    @property
    def gh_api_requests_count(self) -> int:
        """The number of requests against the GitHub API that were performed."""
        return self._gh_api_requests_count

    def resolve(self, mutable_action: MutableAction) -> ImmutableAction:
        """Resolve a `MutableAction` to an `ImmutableAction`.

        Args:
            mutable_action: A `MutableAction` to resolve

        Returns:
            A resolved `ImmutableAction`

        """
        sha = self._resolve_to_commit_sha(
            owner=mutable_action.owner,
            repo=mutable_action.repo,
            ref=mutable_action.ref,
        )

        return ImmutableAction(
            mutable_origin=mutable_action,
            sha=sha,
        )

    def _resolve_to_commit_sha(
        self,
        *,
        owner: str,
        repo: str,
        ref: str,
    ) -> str:
        """Look up a mutable Git ref in GitHub and return a corresponding immutable ref.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Mutable Git ref

        Returns:
            An immutable commit SHA

        Raises:
            GitHubException: API error, e.g. rate limit
            NoGitRefFoundError: The provided Git ref wasn't found on GitHub as a tag or
                branch
            NoGitRepoFoundError: The provided Git repository wasn't found on GitHub

        """
        cache_key = (owner, repo, ref)

        cached = self._cache.get(cache_key, None)
        if cached is not None:
            return cached

        try:
            repo_obj = self._get_repo(owner=owner, repo=repo)
        except UnknownObjectException as e:
            raise NoGitRepoFoundError(
                f"Git repository {owner}/{repo} not found on GitHub.",
            ) from e

        if sha := self._resolve_branch(repo=repo_obj, branch_name=ref):
            self._cache[cache_key] = sha
            return sha

        if sha := self._resolve_tag(repo=repo_obj, tag_name=ref):
            self._cache[cache_key] = sha
            return sha

        raise NoGitRefFoundError(
            f"The Git ref '{ref}' was not found on GitHub as a tag or branch."
        )

    def _get_repo(
        self,
        *,
        owner: str,
        repo: str,
    ) -> Repository:
        repo_obj = self.client.get_repo(f"{owner}/{repo}")
        self._gh_api_requests_count += 1
        return repo_obj

    def _resolve_branch(self, *, repo: Repository, branch_name: str) -> str | None:
        """Attempt to resolve a Git ref as a branch.

        Args:
            repo: GitHub repository object
            branch_name: A Git ref that will be treated as a branch name

        Returns:
            Corresponding commit SHA if branch exists, otherwise None

        """
        try:
            sha = repo.get_branch(branch_name).commit.sha
            self._gh_api_requests_count += 1
        except UnknownObjectException:
            return None

        return sha

    def _resolve_tag(self, *, repo: Repository, tag_name: str) -> str | None:
        """Attempt to resolve a Git ref as a tag.

        Args:
            repo: GitHub repository object
            tag_name: A Git ref that will be treated as a tag name

        Returns:
            Corresponding commit SHA if tag exists, otherwise None

        """
        try:
            ref = repo.get_git_ref(f"tags/{tag_name}")
            self._gh_api_requests_count += 1

            if ref.object.type == "tag":
                # Annotated tag: These are separate git objects. We need to get the tag
                # object before dereferencing.
                # The ref.object.sha seems to be a magic string "tag_object_sha" here:
                sha = repo.get_git_tag(ref.object.sha).object.sha
                self._gh_api_requests_count += 1
            else:
                # Lightweight tag: Simple pointer. We just need to dereference it.
                sha = ref.object.sha
        except UnknownObjectException:
            return None

        return sha
