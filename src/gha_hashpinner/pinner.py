"""The main entrypoint for this package's behavior."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gha_hashpinner.discoverer import scan_path
from gha_hashpinner.exceptions import CheckFailedError, NoWorkflowsFoundError
from gha_hashpinner.models import ImmutableAction
from gha_hashpinner.resolver import resolve_mutable_actions
from gha_hashpinner.workflow import WorkflowFile

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
        workflow_files = scan_path(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise

    if not workflow_files:
        msg = f"No workflow files found in '{path}'"
        console.print(f"[yellow]{msg}[/yellow]")
        raise NoWorkflowsFoundError(msg)

    mutable_actions_count = sum(len(wf.mutable_actions) for wf in workflow_files)

    if mutable_actions_count == 0:
        console.print(
            "[green]✓ All actions are already pinned to immutable SHAs[/green]"
        )
        return

    _print_header(
        path=path,
        workflows_count=len(workflow_files),
        mutable_actions_count=mutable_actions_count,
    )

    _process_workflow_files(workflow_files, dry_run=dry_run, token=token)

    _print_summary(
        workflows_count=len(workflow_files),
        mutable_actions_count=mutable_actions_count,
        dry_run=dry_run,
    )

    if dry_run:
        console.print("\n[dim]Dry run: no changes written[/dim]")

    if check and mutable_actions_count > 0:
        msg = f"{mutable_actions_count} unpinned actions found"
        console.print(f"\n[red]✗ {msg}[/red]")
        raise CheckFailedError(msg)


def _print_header(
    *,
    path: Path,
    workflows_count: int,
    mutable_actions_count: int,
) -> None:
    """Print a summary of the discovered mutable actions."""
    console.print(
        Panel.fit(
            f"[bold]Scanned:[/bold] {path}\n"
            f"[cyan]Found {workflows_count} workflow file(s)"
            f" with {mutable_actions_count} mutable action(s)[/cyan]",
            border_style="cyan",
        )
    )


def _process_workflow_files(
    workflow_files: list[WorkflowFile],
    *,
    dry_run: bool,
    token: str | None = None,
) -> None:
    """Iterate over files containing mutable actions and process each."""
    for workflow_file in workflow_files:
        console.print(f"\n[bold cyan]{workflow_file.path.name}[/bold cyan]")

        if not workflow_file.mutable_actions:
            console.print("  [green]✓ No mutable action pins found[/green]")
            continue

        immutable_actions = resolve_mutable_actions(
            workflow_file.mutable_actions,
            token=token,
        )

        if not immutable_actions:
            console.print(
                "  [yellow]"
                "⚠ Could not resolve any mutable action specifiers as immutable"
                "[/yellow]"
            )

        for immutable in immutable_actions:
            _print_change(immutable)

        if not dry_run:
            workflow_file.update_actions(immutable_actions=immutable_actions)


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
    workflows_count: int,
    mutable_actions_count: int,
    dry_run: bool,
) -> None:
    """Print a summary of the final results."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Workflows processed:", str(workflows_count))
    table.add_row("Mutable actions found:", str(mutable_actions_count))

    if dry_run:
        status = "[yellow]Dry-run: no changes written[/yellow]"
    else:
        status = "[green]Complete![/green]"

    table.add_row("Status:", status)

    console.print("\n")
    console.print(Panel(table, title="[bold]Summary[/bold]", border_style="cyan"))
