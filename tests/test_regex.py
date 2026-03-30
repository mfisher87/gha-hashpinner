"""Tests of the regex module."""

import pytest

from gha_hashpinner.regex.action import ACTION_PATTERN
from gha_hashpinner.regex.sha import SHA_PATTERN
from gha_hashpinner.regex.uses import USES_PATTERN


class TestPatterns:
    """Test regex patterns."""

    @pytest.mark.parametrize(
        "action_spec",
        [
            "actions/checkout@v4",
            "astral-sh/setup-uv@v7",
            "owner/repo@main",
            "owner/repo@v1.2.3",
            "my-org/my-action@release-branch",
        ],
    )
    def test_action_pattern_matches_valid_action(self, action_spec: str) -> None:
        """ACTION_PATTERN should match specifiers matching actions on GitHub."""
        assert ACTION_PATTERN.match(action_spec)

    def test_action_patern_captures_groups(self) -> None:
        """ACTION_PATTERN should capture groups from specifiers."""
        match = ACTION_PATTERN.match("actions/checkout@v4")
        assert match is not None
        assert match.group("owner") == "actions"
        assert match.group("repo") == "checkout"
        assert match.group("ref") == "v4"

    @pytest.mark.parametrize(
        "action_spec",
        [
            "./local-action",
            "docker://alpine:latest",
            "just-a-string",
            "actions/checkout",
        ],
    )
    def test_action_pattern_rejects(self, action_spec: str) -> None:
        """ACTION_PATTERN should reject local, docker, and invalid specifiers."""
        assert not ACTION_PATTERN.match(action_spec)

    @pytest.mark.parametrize(
        "sha",
        [
            "8f4b7f84864484a7bf31766abe9204da3cbe65b3",
            "0123456789abcdef0123456789abcdef01234567",
            "baddadbaddadbaddadbaddadbaddadbaddadbadd",
            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        ],
    )
    def test_sha_pattern_matches_valid_sha(self, sha: str) -> None:
        """SHA_PATTERN should match 40-character hexadecimal strings."""
        assert SHA_PATTERN.match(sha)

    @pytest.mark.parametrize(
        "sha",
        [
            "v4",
            "main",
            "8f4b7f8",  # Too short
            "8f4b7f84864484a7bf31766abe9204da3cbe65b3a",  # Too long
            "gggggggggggggggggggggggggggggggggggggggg",  # "g" is not valid hexadecimal
        ],
    )
    def test_sha_pattern_rejects_invalid(self, sha: str) -> None:
        """SHA_PATTERN should reject non-SHA strings."""
        assert not SHA_PATTERN.match(sha)

    @pytest.mark.parametrize(
        ("uses", "expected"),
        [
            ("     uses: 'actions/checkout@v4' # comment", "actions/checkout@v4"),
            ('   uses: "foo/bar@baz"     # comment', "foo/bar@baz"),
            ('uses: "foo/bar"', "foo/bar"),
            ('uses:     "foo/bar"', "foo/bar"),
            (" - uses: 'foo/bar@baz' # comment", "foo/bar@baz"),
            ('   -   uses: "foo/bar@baz" # comment', "foo/bar@baz"),
        ],
    )
    def test_uses_pattern_matches(self, uses: str, expected: str) -> None:
        """USES_PATTERN should match valid strings."""
        match = USES_PATTERN.match(uses)
        assert match is not None
        assert match.group("action_spec") == expected

    @pytest.mark.parametrize(
        "uses",
        [
            "   fuses: 'actions/checkout@v4' # comment",
            "   uses:'actions/checkout@v4' # comment",
            "uses:actions/checkout@v4 # comment",
            pytest.param(
                " uses: 1  # comment",
                marks=[
                    pytest.mark.xfail(
                        reason="Incorrectly accepts digit value as action specifier"
                    )
                ],
            ),
            pytest.param(
                " uses: 'docker://foo'",
                marks=[
                    pytest.mark.xfail(
                        reason="Incorrectly accepts docker action specifier"
                    )
                ],
            ),
            pytest.param(
                " uses: './foo/bar'",
                marks=[
                    pytest.mark.xfail(
                        reason="Incorrectly accepts local action specifier"
                    )
                ],
            ),
        ],
    )
    def test_uses_pattern_rejects(self, uses: str) -> None:
        """USES_PATTERN should reject invalid strings."""
        assert not USES_PATTERN.match(uses)
