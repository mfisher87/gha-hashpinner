"""Custom exceptions for this package."""


class CheckFailedError(Exception):
    """The program was run in "check" mode and found issues."""


class NoWorkflowsFoundError(Exception):
    """The program found no workflow files."""


class NoGitRefFoundError(Exception):
    """Could not find requested Git ref in GitHub API."""


class NoGitRepoFoundError(Exception):
    """Could not find requested Git repository in GitHub API."""
