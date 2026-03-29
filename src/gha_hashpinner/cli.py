"""CLI for this package."""

from pathlib import Path
from typing import Annotated

import typer

from gha_hashpinner.pinner import pin

cli = typer.Typer()

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
) -> None:
    """Pin GitHub Actions to immutable SHAs with Dependabot compatibility."""
    try:
        pin(path=path, token=token, dry_run=dry_run, check=check)
    except Exception as e:
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    cli()
