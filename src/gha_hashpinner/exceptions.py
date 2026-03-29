"""Custom exceptions for this package."""


class CheckFailedError(Exception):
    """The program was run in "check" mode and found issues."""


class NoWorkflowsFoundError(Exception):
    """The program found no workflow files."""
