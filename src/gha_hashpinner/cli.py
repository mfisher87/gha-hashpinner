"""CLI for this package."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from gha_hashpinner._version import __version__
from gha_hashpinner.exceptions import CheckFailedError, NoWorkflowsFoundError
from gha_hashpinner.pinner import pin

cli = typer.Typer()
console = Console()
CWD = Path.cwd()


@cli.command()
def cli_root(
    *,
    path: Annotated[
        Path,
        typer.Argument(
            help=(
                "Path to a directory containing `.github/workflows/`,"
                " or path to a specific workflow file."
            ),
        ),
    ] = CWD,
    token: Annotated[
        str | None,
        typer.Option(
            envvar="GITHUB_TOKEN",
            help="GitHub token for API access. **Read-only** token recommended.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Show changes without applying changes.",
        ),
    ] = False,
    check: Annotated[
        bool,
        typer.Option(
            help=(
                "Exit with return code 1 if any unpinned actions found. Useful for CI."
            ),
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help=("Print the version and immediately exit."),
        ),
    ] = False,
) -> None:
    """Pin GitHub Actions to immutable SHAs with Dependabot compatibility."""
    if version:
        console.print(f"gha-hashpinner version: {__version__}")
        raise typer.Exit(0)

    try:
        pin(path=path, token=token, dry_run=dry_run, check=check)
    except (NoWorkflowsFoundError, CheckFailedError, FileNotFoundError) as e:
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise


if __name__ == "__main__":
    cli()
