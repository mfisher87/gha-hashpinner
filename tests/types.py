"""Types for unit tests."""

from collections.abc import Callable
from pathlib import Path
from typing import NotRequired, TypedDict, Unpack


class MakeWorkflowFileArgs(TypedDict):
    content: str
    name: NotRequired[str]


type MakeWorkflowFileFunc = Callable[[Unpack[MakeWorkflowFileArgs]], Path]
type MakeWorkflowsDirFunc = Callable[[dict[str, str]], Path]
