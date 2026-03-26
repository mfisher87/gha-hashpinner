"""Resolves mutable pins to immutable pins by querying the GitHub API."""

from gha_hashpinner.models import ActionReference, HashPinnedActionReference


def resolve_action_references(
    action_refs: list[ActionReference],
    *,
    token: str | None = None,
) -> list[HashPinnedActionReference]:
    """Resolve `ActionReferences` to `HashPinnedActionReferences`.

    Look up immutable refs using the GitHub API.
    """
