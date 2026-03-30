"""Unit test helpers."""

from unittest.mock import Mock

from gha_hashpinner.action import ImmutableAction, MutableAction


def make_branch_mock(*, sha: str) -> Mock:
    """Create a mock branch with the given SHA."""
    branch = Mock()
    branch.commit.sha = sha
    return branch


def make_tag_mock(*, sha: str, is_annotated: bool = False) -> Mock | tuple[Mock, str]:
    """Create a mock tag reference with the given SHA.

    Args:
        sha: The commit SHA
        is_annotated: If True, creates an annotated tag (tag object pointing to commit)
                      If False, creates a lightweight tag (ref pointing directly to commit)

    """
    ref = Mock()
    if is_annotated:
        ref.object.type = "tag"
        ref.object.sha = "tag_object_sha"
        return ref, sha  # Return both for annotated tags

    ref.object.type = "commit"
    ref.object.sha = sha
    return ref


def make_repo_mock(
    *,
    branch_sha: str | None = None,
    branch_error: Exception | None = None,
    tag_sha: str | None = None,
    annotated_tag_sha: str | None = None,
    tag_error: Exception | None = None,
) -> Mock:
    """Create a mock repository with specified behaviors.

    Args:
        branch_sha: SHA to return for branch lookups
        tag_sha: SHA to return for tag lookups
        annotated_tag_sha: SHA to return for annotated tag lookups
        branch_error: Exception to raise on branch lookup
        tag_error: Exception to raise on tag lookup

    """
    # TODO: This is kinda gross :X
    repo = Mock()

    if branch_sha is not None:
        repo.get_branch.return_value = make_branch_mock(sha=branch_sha)
    elif branch_error is not None:
        repo.get_branch.side_effect = branch_error

    # TODO: Handle branch request failing implicitly, no passed in Exception
    # TODO: Handle annotated / lightweight tag object
    if tag_sha is not None:
        repo.get_git_ref.return_value = make_tag_mock(sha=tag_sha)
    elif annotated_tag_sha is not None:
        ref, sha = make_tag_mock(sha=annotated_tag_sha, is_annotated=True)
        repo.get_git_ref.return_value = ref
        tag_object = Mock()
        tag_object.object.type = "commit"
        tag_object.object.sha = sha
        repo.get_git_tag.return_value = tag_object
    elif tag_error is not None:
        repo.get_git_ref.side_effect = tag_error

    return repo


def make_mutable_action(
    *,
    owner: str = "actions",
    repo: str = "checkout",
    ref: str = "v4",
    line_number: int = 10,
    subpath: str | None = None,
) -> MutableAction:
    """Build a MutableAction with sensible defaults."""
    full_string = f"{owner}/{repo}"
    if subpath:
        full_string += subpath
    full_string += f"@{ref}"

    return MutableAction(
        owner=owner,
        repo=repo,
        ref=ref,
        line_number=line_number,
        full_string=full_string,
        subpath=subpath,
    )


def make_immutable_action(
    *,
    mutable_origin: MutableAction | None = None,
    sha: str = "abc123def456abc123def456abc123def456abc1",
) -> ImmutableAction:
    """Build an ImmutableAction with sensible defaults."""
    if mutable_origin is None:
        mutable_origin = make_mutable_action()

    return ImmutableAction(
        mutable_origin=mutable_origin,
        sha=sha,
    )
