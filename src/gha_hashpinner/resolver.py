"""Resolves mutable pins to immutable pins by querying the GitHub API."""

from github import Github, UnknownObjectException
from github.Repository import Repository

from gha_hashpinner.models import ImmutableAction, MutableAction

type GhResolutionCache = dict[tuple[str, str, str], str]


def resolve_mutable_actions(
    mutable_actions: list[MutableAction],
    *,
    token: str | None = None,
) -> list[ImmutableAction]:
    """Resolve `MutableAction`s to `ImmutableAction`s using GitHub API.

    Actions that fail to resolve are skipped.

    Args:
        mutable_actions: List of mutable `MutableAction`s to resolve
        token: Optional GitHub token for API access (recommended to avoid rate limits)

    Returns:
        List of resolved `ImmutableAction`s (n <= `len(mutable_actions)`)

    """
    gh = Github(token) if token else Github()
    gh_resolution_cache: GhResolutionCache = {}

    resolved: list[ImmutableAction] = []
    for mutable_action in mutable_actions:
        sha = _resolve_ref_to_commit_sha(
            gh=gh,
            owner=mutable_action.owner,
            repo=mutable_action.repo,
            ref=mutable_action.ref,
            cache=gh_resolution_cache,
        )
        resolved.append(
            ImmutableAction(
                mutable_origin=mutable_action,
                sha=sha,
                comment=mutable_action.ref,
            )
        )

    return resolved


def _resolve_ref_to_commit_sha(
    *,
    gh: Github,
    owner: str,
    repo: str,
    ref: str,
    cache: GhResolutionCache | None = None,
) -> str:
    """Look up a mutable Git ref in GitHub and return a corresponding immutable ref.

    Caches results on `(owner, repo, ref)` to limit GH API calls and make best effort to
    avoid rate limiting.

    Args:
        gh: An instance of a `pygithub.Github` client
        owner: Repository owner
        repo: Repository name
        ref: Mutable Git ref
        cache: A cache to use to limit GH API usage

    Returns:
        An immutable commit SHA

    Raises:
        UnknownObjectException: Repo doesn't exist or is inaccessible
        GitHubException: API error, e.g. rate limit
        ValueError: The provided Git ref wasn't found as a tag or branch

    """
    if cache is not None:
        cache_key = (owner, repo, ref)
        cached = cache.get(cache_key, None)
        if cached is not None:
            return cached

    repo_obj = gh.get_repo(f"{owner}/{repo}")

    if sha := _resolve_branch(repo=repo_obj, branch_name=ref):
        if cache is not None:
            cache[cache_key] = sha
        return sha

    if sha := _resolve_tag(repo=repo_obj, tag_name=ref):
        if cache is not None:
            cache[cache_key] = sha
        return sha

    raise ValueError(f"The Git ref '{ref}' was not found on GitHub as a tag or branch.")


def _resolve_branch(*, repo: Repository, branch_name: str) -> str | None:
    """Attempt to resolve a Git ref as a branch.

    Args:
        repo: GitHub repository object
        branch_name: A Git ref that will be treated as a branch name

    Returns:
        Corresponding commit SHA if branch exists, otherwise None

    """
    try:
        return repo.get_branch(branch_name).commit.sha
    except UnknownObjectException:
        return None


def _resolve_tag(*, repo: Repository, tag_name: str) -> str | None:
    """Attempt to resolve a Git ref as a tag.

    Args:
        repo: GitHub repository object
        tag_name: A Git ref that will be treated as a tag name

    Returns:
        Corresponding commit SHA if tag exists, otherwise None

    """
    try:
        ref = repo.get_git_ref(f"tags/{tag_name}")

        if ref.object.type == "tag":
            # Annotated tag: These are separate git objects. We need to get the tag
            # object before dereferencing.
            # The ref.object.sha seems to be a magic string "tag_object_sha" here:
            sha = repo.get_git_tag(ref.object.sha).object.sha
        else:
            # Lightweight tag: Simple pointer. We just need to dereference it.
            sha = ref.object.sha
    except UnknownObjectException:
        return None

    return sha
