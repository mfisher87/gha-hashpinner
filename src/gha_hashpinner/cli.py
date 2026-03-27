"""CLI for this package."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gha_hashpinner.models import ActionReference, HashPinnedActionReference
from gha_hashpinner.parser import find_all_mutable_action_references
from gha_hashpinner.resolver import resolve_action_references
from gha_hashpinner.updater import update_workflow_file

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
) -> None:
    """Pin GitHub Actions to immutable SHAs with Dependabot compatibility."""
    pin(path=path, token=token, dry_run=dry_run, check=check)


def pin(
    *,
    path: Path,
    token: str | None,
    dry_run: bool,
    check: bool,
) -> None:
    """Pin GitHub Actions to immutable SHAs with Dependabot compatibility."""
    try:
        mutable_refs_by_file = find_all_mutable_action_references(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    if not mutable_refs_by_file:
        console.print(f"[yellow]No workflow files found in '{path}'[/yellow]")

    total_refs = sum(len(refs) for refs in mutable_refs_by_file.values())

    if total_refs == 0:
        console.print(
            "[green]✓[/green] All actions are already pinned to immutable SHAs"
        )
        raise typer.Exit(code=0)

    _print_header(
        path=path,
        num_paths=len(mutable_refs_by_file),
        num_refs=total_refs,
    )

    _process_refs(mutable_refs_by_file, dry_run=dry_run, token=token)

    _print_summary(
        total_workflows=len(mutable_refs_by_file),
        total_refs=total_refs,
        dry_run=dry_run,
    )

    if dry_run:
        console.print("\n[dim]Dry run: no changes written[/dim]")

    if check and total_refs > 0:
        console.print(f"\n[red]✗ {total_refs} unpinned actions found[/red]")
        raise typer.Exit(code=1)


def _print_header(*, path: Path, num_paths: int, num_refs: int) -> None:
    """Print a summary of the discovered mutable refs."""
    console.print(
        Panel.fit(
            f"[bold]Scanned:[/bold] {path}\n"
            f"[cyan]Found {num_paths} workflow file(s)"
            f" with {num_refs} mutable reference(s)[/cyan]",
            border_style="cyan",
        )
    )


def _process_refs(
    mutable_refs_by_file: dict[Path, list[ActionReference]],
    *,
    dry_run: bool,
    token: str | None = None,
) -> None:
    """Iterate over files containing mutable refs and process each."""
    for workflow_file, mutable_refs in mutable_refs_by_file.items():
        console.print(f"\n[bold cyan]{workflow_file.name}[/bold cyan]")

        if not mutable_refs:
            console.print("  [green]✓ No mutable action pins found[/green]")
            continue

        immutable_refs = resolve_action_references(mutable_refs, token=token)

        if not immutable_refs:
            console.print(
                "  [yellow]⚠ Could not resolve any action references[/yellow]"
            )

        for ref in immutable_refs:
            _print_change(ref)

        if not dry_run:
            update_workflow_file(workflow_file, refs=immutable_refs)


def _print_change(immutable_ref: HashPinnedActionReference) -> None:
    """Print a summary of an individual ref transformation."""
    mutable = immutable_ref.action_reference

    console.print(
        f"  [green]✓ Line {mutable.line_number:3d}:"
        f" [dim]{mutable.full_string.strip()}[/dim] ->"
        f" [bold]{immutable_ref.short_string}[/bold]"
        f" [dim]# {immutable_ref.comment}[/dim]"
    )


def _print_summary(
    *,
    total_workflows: int,
    total_refs: int,
    dry_run: bool,
) -> None:
    """Print a summary of the final results."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Workflows processed:", str(total_workflows))
    table.add_row("Mutable refs found:", str(total_refs))

    if dry_run:
        status = "[yellow]Dry-run: no changes written[/yellow]"
    else:
        status = "[green]Complete![/green]"

    table.add_row("Status:", status)

    console.print("\n")
    console.print(Panel(table, title="[bold]Summary[/bold]", border_style="cyan"))


if __name__ == "__main__":
    cli()
