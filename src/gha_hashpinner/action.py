"""Behaviors for interacting with individual action specifiers."""

from dataclasses import dataclass
from typing import Self

from gha_hashpinner.regex.action import ACTION_PATTERN
from gha_hashpinner.regex.sha import SHA_PATTERN


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

    @classmethod
    def parse(cls, action_specifier: str, *, line_number: int) -> Self | None:
        """Parse a mutable action specifier into a `MutableAction`.

        Args:
            action_specifier: A string value of a YAML `uses:` key from a GitHub Actions
                workflow definition
            line_number: The line number the `action_specifier` was found on

        Returns:
            A `MutableAction` if the action specifier is mutable, else `None`

        """
        # TODO: Make this a regular __init__ method?
        # TODO: We're already eliminating these with the regex below, right?
        if action_specifier.startswith(("./", "docker://")):
            # TODO: Log (debug?)?
            return None

        match = ACTION_PATTERN.match(action_specifier)
        if not match:
            # TODO: Warn
            return None

        ref = match.group("ref")
        if SHA_PATTERN.match(ref):
            # The action is immutable
            return None

        return cls(
            owner=match.group("owner"),
            repo=match.group("repo"),
            subpath=match.group("subpath"),
            ref=ref,
            line_number=line_number,
            full_string=action_specifier,
        )

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
