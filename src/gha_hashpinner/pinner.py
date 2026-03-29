"""The main entrypoint for this package's behavior."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gha_hashpinner.exceptions import CheckFailedError
from gha_hashpinner.models import ImmutableAction, MutableAction
from gha_hashpinner.parser import find_all_mutable_actions
from gha_hashpinner.resolver import resolve_mutable_actions
from gha_hashpinner.updater import update_workflow_file

console = Console()


def pin(
    *,
    path: Path,
    token: str | None,
    dry_run: bool,
    check: bool,
) -> None:
    """Pin GitHub Actions to immutable SHAs with Dependabot compatibility."""
    try:
        mutable_actions_by_file = find_all_mutable_actions(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise

    if not mutable_actions_by_file:
        console.print(f"[yellow]No workflow files found in '{path}'[/yellow]")

    mutable_actions_count = sum(
        len(actions) for actions in mutable_actions_by_file.values()
    )

    if mutable_actions_count == 0:
        console.print(
            "[green]✓[/green] All actions are already pinned to immutable SHAs"
        )
        return

    _print_header(
        path=path,
        paths_count=len(mutable_actions_by_file),
        mutable_actions_count=mutable_actions_count,
    )

    process_mutable_actions(mutable_actions_by_file, dry_run=dry_run, token=token)

    _print_summary(
        total_workflows=len(mutable_actions_by_file),
        mutable_actions_count=mutable_actions_count,
        dry_run=dry_run,
    )

    if dry_run:
        console.print("\n[dim]Dry run: no changes written[/dim]")

    if check and mutable_actions_count > 0:
        msg = f"{mutable_actions_count} unpinned actions found"
        console.print(f"\n[red]✗ {msg}[/red]")
        raise CheckFailedError(msg)


def _print_header(*, path: Path, paths_count: int, mutable_actions_count: int) -> None:
    """Print a summary of the discovered mutable actions."""
    console.print(
        Panel.fit(
            f"[bold]Scanned:[/bold] {path}\n"
            f"[cyan]Found {paths_count} workflow file(s)"
            f" with {mutable_actions_count} mutable action(s)[/cyan]",
            border_style="cyan",
        )
    )


def process_mutable_actions(
    mutable_actions_by_file: dict[Path, list[MutableAction]],
    *,
    dry_run: bool,
    token: str | None = None,
) -> None:
    """Iterate over files containing mutable actions and process each."""
    for workflow_file, mutable_actions in mutable_actions_by_file.items():
        console.print(f"\n[bold cyan]{workflow_file.name}[/bold cyan]")

        if not mutable_actions:
            console.print("  [green]✓ No mutable action pins found[/green]")
            continue

        immutable_actions = resolve_mutable_actions(mutable_actions, token=token)

        if not immutable_actions:
            console.print(
                "  [yellow]"
                "⚠ Could not resolve any mutable action specifiers as immutable"
                "[/yellow]"
            )

        for immutable in immutable_actions:
            _print_change(immutable)

        if not dry_run:
            update_workflow_file(workflow_file, immutable_actions=immutable_actions)


def _print_change(immutable_action: ImmutableAction) -> None:
    """Print a summary of an individual action's transformation."""
    mutable = immutable_action.mutable_origin

    console.print(
        f"  [green]✓ Line {mutable.line_number:5d}:"
        f" [dim]{mutable.full_string.strip()}[/dim]"
        f"\n             -> [bold]{immutable_action.short_string}[/bold]"
        f" [dim]# {immutable_action.comment}[/dim]"
    )


def _print_summary(
    *,
    total_workflows: int,
    mutable_actions_count: int,
    dry_run: bool,
) -> None:
    """Print a summary of the final results."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Workflows processed:", str(total_workflows))
    table.add_row("Mutable actions found:", str(mutable_actions_count))

    if dry_run:
        status = "[yellow]Dry-run: no changes written[/yellow]"
    else:
        status = "[green]Complete![/green]"

    table.add_row("Status:", status)

    console.print("\n")
    console.print(Panel(table, title="[bold]Summary[/bold]", border_style="cyan"))
