"""Tests of the regex module."""

import pytest

from gha_hashpinner.regex import (
    ACTION_PATTERN,
    SHA_PATTERN,
)


class TestPatterns:
    """Test regex patterns."""

    @pytest.mark.parametrize(
        "uses_str",
        [
            "actions/checkout@v4",
            "astral-sh/setup-uv@v7",
            "owner/repo@main",
            "owner/repo@v1.2.3",
            "my-org/my-action@release-branch",
        ],
    )
    def test_action_pattern_matches_valid_action(self, uses_str: str) -> None:
        """ACTION_PATTERN should match "uses:" values matching actions on GitHub."""
        assert ACTION_PATTERN.match(uses_str)

    def test_action_patern_captures_groups(self) -> None:
        """ACTION_PATTERN should capture groups from "uses:" value."""
        match = ACTION_PATTERN.match("actions/checkout@v4")
        assert match is not None
        assert match.group("owner") == "actions"
        assert match.group("repo") == "checkout"
        assert match.group("ref") == "v4"

    @pytest.mark.parametrize(
        "uses_str",
        [
            "./local-action",
            "docker://alpine:latest",
            "just-a-string",
            "actions/checkout",
        ],
    )
    def test_action_pattern_rejects(self, uses_str: str) -> None:
        """ACTION_PATTERN should reject local, docker, and invalid "uses" values."""
        assert not ACTION_PATTERN.match(uses_str)

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
