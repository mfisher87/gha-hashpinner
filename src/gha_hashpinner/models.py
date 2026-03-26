"""Data models for this package."""

from dataclasses import dataclass


@dataclass
class ActionReference:
    """A GitHub Action reference (`uses: ...`) in a workflow."""

    owner: str
    repo: str
    ref: str
    line_number: int
    full_string: str


@dataclass
class HashPinnedActionReference:
    """An ActionReference enriched with an immutable SHA & comment.

    The comment represents the original mutable pin, e.g. "v4", and enables Dependabot
    to do automated upgrades.
    """

    action_reference: ActionReference
    sha: str
    comment: str

    @property
    def full_string(self) -> str:
        """Generate the full string value of a `uses:` key for a GHA workflow."""
        return f"{self.action_reference.owner}/{self.action_reference.repo}@{self.sha}"

    @property
    def short_string(self) -> str:
        """A short string representation of `self.full_string` for console output."""
        return (
            f"{self.action_reference.owner}/{self.action_reference.repo}@{self.sha[:8]}"
        )
