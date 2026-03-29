"""Data models for this package."""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class MutableAction:
    """A GitHub Action specifier (value of a `uses: ...` key) in a workflow."""

    owner: str
    repo: str
    ref: str
    line_number: int
    full_string: str

    # Some repos contain multiple actions, using a subpath to differentiate. E.g.:
    #     jupyterlab/maintainer-tools/.github/actions/enforce-label@v1
    subpath: str | None = None

    @property
    def full_string_without_ref(self) -> str:
        """Full action specifier string without ref."""
        string = f"{self.owner}/{self.repo}"
        if self.subpath:
            string += self.subpath
        return string

    def __post_init__(self) -> None:
        """Validate."""
        if self.subpath and not self.subpath.startswith("/"):
            raise ValueError(
                f"subpath attribute must start with '/'. Received {self.subpath}"
            )


@dataclass(frozen=True, kw_only=True)
class ImmutableAction:
    """A MutableAction enriched with an immutable SHA & comment.

    The comment represents the original mutable pin, e.g. "v4", and enables Dependabot
    to do automated upgrades.
    """

    mutable_origin: MutableAction
    sha: str
    comment: str

    @property
    def full_string(self) -> str:
        """Generate a full immutable action specifier string.

        Does not include a comment, this is just the value for the `uses:` key.
        """
        return f"{self.mutable_origin.full_string_without_ref}@{self.sha}"

    @property
    def short_string(self) -> str:
        """A short string representation of `full_string` for console output.

        The commit sha is truncated to 8 chars.
        """
        return f"{self.mutable_origin.full_string_without_ref}@{self.sha[:8]}"
