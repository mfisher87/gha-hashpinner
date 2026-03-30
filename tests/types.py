"""Types for unit tests."""

from collections.abc import Callable
from pathlib import Path

type MakeWorkflowsDirFunc = Callable[[dict[str, str]], Path]
