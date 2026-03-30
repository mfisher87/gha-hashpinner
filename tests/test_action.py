"""Tests for the action module."""

import pytest

from gha_hashpinner.action import MutableAction

from .helpers import make_immutable_action, make_mutable_action


class TestMutableActionParse:
    """Test MutableAction.parse() classmethod."""

    @pytest.mark.parametrize(
        "action_spec",
        [
            pytest.param(
                "owner/repo",
                marks=[
                    pytest.mark.xfail(
                        reason="Specifiers with no pin unsupported (issue #7)",
                    )
                ],
            ),
            "actions/checkout@v4",
            "owner/repo@main",
            "owner/repo/.github/actions/custom@v1",
            "owner/repo/action@some-branch",
            "owner/repo/path/to/custom/action@v1.2.3",
        ],
    )
    def test_parse_valid_mutable_actions(self, action_spec: str) -> None:
        """Should successfully parse valid mutable action specifiers."""
        action = MutableAction.parse(action_spec, line_number=10)

        assert action is not None
        assert action.full_string == action_spec
        assert action.line_number == 10

    @pytest.mark.parametrize(
        "action_spec",
        [
            "./local-action",
            "docker://alpine:latest",
            "actions/checkout@abc123def456abc123def456abc123def456abc1",  # Already immutable
        ],
    )
    def test_parse_returns_none_for_immutable_or_local(self, action_spec: str) -> None:
        """Should return None for local, docker, or already-pinned actions."""
        action = MutableAction.parse(action_spec, line_number=10)

        assert action is None

    @pytest.mark.parametrize(
        ("specifier", "expected"),
        [
            (
                "jupyterlab/maintainer-tools/.github/actions/enforce-label@v1",
                "/.github/actions/enforce-label",
            ),
            ("owner/repo/.github/actions/custom@v1", "/.github/actions/custom"),
            ("owner/repo/action@some-branch", "/action"),
            ("owner/repo/path/to/custom/action@v1.2.3", "/path/to/custom/action"),
        ],
    )
    def test_parse_extracts_subpath(self, specifier: str, expected: str) -> None:
        """Should extract subpath from actions with path components."""
        action = MutableAction.parse(specifier, line_number=5)

        assert action is not None
        assert action.subpath == expected


class TestMutableActionProperties:
    """Test MutableAction cached properties."""

    def test_full_string_without_ref(self) -> None:
        """Should generate action specifier without ref."""
        action = make_mutable_action(owner="foo", repo="bar", ref="v1")

        assert action.full_string_without_ref == "foo/bar"

    def test_full_string_without_ref_with_subpath(self) -> None:
        """Should include subpath in generated string."""
        action = make_mutable_action(
            owner="foo",
            repo="bar",
            ref="v1",
            subpath="/.github/actions/custom",
        )

        assert action.full_string_without_ref == "foo/bar/.github/actions/custom"


class TestImmutableActionProperties:
    """Test ImmutableAction cached properties."""

    def test_full_string_generates_immutable_specifier(self) -> None:
        """Should generate full action specifier with SHA."""
        sha = "abcd1234" * 5
        immutable = make_immutable_action(
            mutable_origin=make_mutable_action(
                owner="foo",
                repo="bar",
                ref="v1",
            ),
            sha=sha,
        )

        assert immutable.full_string == f"foo/bar@{sha}"

    def test_short_string_truncates_sha(self) -> None:
        """Should truncate SHA to 8 characters for display."""
        immutable = make_immutable_action(sha="abcd1234" + "x" * 32)

        assert immutable.short_string.endswith("@abcd1234")
        assert len(immutable.sha) == 40
