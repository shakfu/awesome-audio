"""CLI for awesome-audio."""

from pathlib import Path

import click

from src.importer import export_to_yaml, import_from_yaml
from src.model import Entry, get_session
from src.schema import CATEGORIES, load_and_validate

DEFAULT_YAML = Path(__file__).parent.parent / "data" / "entries.yml"
DEFAULT_DB = Path(__file__).parent.parent / "awesome-audio.db"


@click.group()
@click.version_option(version="0.4.0")
def cli():
    """awesome-audio: A curated guide to open-source audio projects."""
    pass


@cli.command()
@click.option("--yaml", "-y", "yaml_path", type=click.Path(exists=True), default=None,
              help="Path to YAML file (default: data/entries.yml)")
def validate(yaml_path: str | None):
    """Validate the entries YAML file."""
    path = Path(yaml_path) if yaml_path else DEFAULT_YAML
    result = load_and_validate(path)

    click.echo(result.summary())
    click.echo()

    if result.errors:
        click.secho("ERRORS:", fg="red", bold=True)
        for idx, entry, error in result.errors:
            click.echo(f"  Entry {idx}: {entry.get('name', 'UNKNOWN')}")
            click.echo(f"    {error}")
        click.echo()

    if result.duplicates:
        click.secho("DUPLICATES:", fg="yellow", bold=True)
        for name, indices in result.duplicates:
            click.echo(f"  '{name}' appears at entries: {indices}")
        click.echo()

    if result.warnings:
        click.secho("WARNINGS:", fg="yellow")
        for idx, entry, warning in result.warnings:
            click.echo(f"  Entry {idx}: {entry.get('name', 'UNKNOWN')}: {warning}")

    if result.is_valid and not result.duplicates:
        click.secho("Validation passed!", fg="green", bold=True)
        raise SystemExit(0)
    else:
        raise SystemExit(1)


@cli.command("import")
@click.option("--yaml", "-y", "yaml_path", type=click.Path(exists=True), default=None,
              help="Path to YAML file (default: data/entries.yml)")
@click.option("--db", "-d", "db_path", type=click.Path(), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--update/--no-update", default=False,
              help="Update existing entries instead of skipping")
def import_cmd(yaml_path: str | None, db_path: str | None, update: bool):
    """Import entries from YAML to SQLite database."""
    yaml_file = Path(yaml_path) if yaml_path else DEFAULT_YAML
    db_file = Path(db_path) if db_path else DEFAULT_DB

    click.echo(f"Importing from {yaml_file} to {db_file}...")
    imported, skipped, errors = import_from_yaml(
        yaml_file, db_file, skip_duplicates=not update
    )

    click.echo(f"Imported: {imported}")
    click.echo(f"Skipped: {skipped}")

    if errors:
        click.secho("Errors:", fg="red")
        for err in errors:
            click.echo(f"  {err}")
        raise SystemExit(1)

    click.secho("Import complete.", fg="green")


@cli.command("export")
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--output", "-o", "output_path", type=click.Path(), required=True,
              help="Output YAML file path")
def export_cmd(db_path: str | None, output_path: str):
    """Export entries from SQLite database to YAML."""
    db_file = Path(db_path) if db_path else DEFAULT_DB
    out_file = Path(output_path)

    count = export_to_yaml(db_file, out_file)
    click.echo(f"Exported {count} entries to {out_file}")


@cli.command()
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--category", "-c", "category", default=None,
              help="Filter by category")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="Output format")
def list(db_path: str | None, category: str | None, fmt: str):
    """List all entries in the database."""
    db_file = Path(db_path) if db_path else DEFAULT_DB

    if not db_file.exists():
        click.secho(f"Database not found: {db_file}", fg="red")
        click.echo("Run 'awesome-audio import' first to create the database.")
        raise SystemExit(1)

    session = get_session(db_file)
    query = session.query(Entry).order_by(Entry.name)

    if category:
        query = query.filter(Entry.category.ilike(f"%{category}%"))

    entries = query.all()
    session.close()

    if not entries:
        click.echo("No entries found.")
        return

    if fmt == "json":
        import json
        data = [e.to_dict() for e in entries]
        click.echo(json.dumps(data, indent=2))
    elif fmt == "yaml":
        import yaml
        data = [{"name": e.name, "category": e.category, "desc": e.description,
                 "url": e.url, "repo": e.repo} for e in entries]
        click.echo(yaml.dump(data, sort_keys=False))
    else:
        # Table format
        click.echo(f"{'Name':<30} {'Category':<20} {'URL/Repo':<50}")
        click.echo("-" * 100)
        for e in entries:
            url = e.url or e.repo or ""
            if len(url) > 47:
                url = url[:47] + "..."
            click.echo(f"{e.name:<30} {e.category:<20} {url:<50}")
        click.echo(f"\nTotal: {len(entries)} entries")


@cli.command()
@click.argument("query")
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
def search(query: str, db_path: str | None):
    """Search entries by name or description."""
    db_file = Path(db_path) if db_path else DEFAULT_DB

    if not db_file.exists():
        click.secho(f"Database not found: {db_file}", fg="red")
        click.echo("Run 'awesome-audio import' first to create the database.")
        raise SystemExit(1)

    session = get_session(db_file)
    entries = session.query(Entry).filter(
        Entry.name.ilike(f"%{query}%") |
        Entry.description.ilike(f"%{query}%") |
        Entry.category.ilike(f"%{query}%")
    ).order_by(Entry.name).all()
    session.close()

    if not entries:
        click.echo(f"No entries found matching '{query}'")
        return

    for e in entries:
        click.secho(e.name, fg="green", bold=True)
        click.echo(f"  Category: {e.category}")
        click.echo(f"  {e.description}")
        if e.url:
            click.echo(f"  URL: {e.url}")
        if e.repo:
            click.echo(f"  Repo: {e.repo}")
        click.echo()

    click.echo(f"Found {len(entries)} entries matching '{query}'")


@cli.command()
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
def stats(db_path: str | None):
    """Show statistics about the database."""
    db_file = Path(db_path) if db_path else DEFAULT_DB

    if not db_file.exists():
        click.secho(f"Database not found: {db_file}", fg="red")
        click.echo("Run 'awesome-audio import' first to create the database.")
        raise SystemExit(1)

    session = get_session(db_file)

    total = session.query(Entry).count()
    with_url = session.query(Entry).filter(Entry.url.isnot(None)).count()
    with_repo = session.query(Entry).filter(Entry.repo.isnot(None)).count()

    # Category breakdown
    from sqlalchemy import func
    categories = session.query(
        Entry.category, func.count(Entry.id)
    ).group_by(Entry.category).order_by(func.count(Entry.id).desc()).all()

    session.close()

    click.secho("Database Statistics", fg="blue", bold=True)
    click.echo(f"Total entries: {total}")
    click.echo(f"With URL: {with_url}")
    click.echo(f"With repo: {with_repo}")
    click.echo()

    click.secho("Categories:", fg="blue", bold=True)
    for cat, count in categories:
        click.echo(f"  {cat}: {count}")


@cli.command()
def categories():
    """List canonical categories."""
    click.secho("Canonical Categories:", fg="blue", bold=True)
    for cat in sorted(CATEGORIES):
        click.echo(f"  {cat}")
    click.echo(f"\nTotal: {len(CATEGORIES)} categories")


@cli.command()
@click.option("--yaml", "-y", "yaml_path", type=click.Path(exists=True), default=None,
              help="Path to YAML file (default: data/entries.yml)")
@click.option("--concurrency", "-c", default=10, help="Number of concurrent requests")
@click.option("--timeout", "-t", default=10.0, help="Timeout per request in seconds")
def check(yaml_path: str | None, concurrency: int, timeout: float):
    """Check all URLs for broken links."""
    import yaml as yaml_lib

    from src.checker import LinkStatus, run_check

    path = Path(yaml_path) if yaml_path else DEFAULT_YAML

    with open(path) as f:
        entries = yaml_lib.safe_load(f)

    click.echo(f"Checking {len(entries)} entries...")

    def progress(current, total, name):
        click.echo(f"  [{current}/{total}] {name}", nl=True)

    results = run_check(entries, concurrency, timeout, progress)

    # Summarize results
    ok_count = 0
    redirect_count = 0
    issues = []

    for result in results:
        for link_result in [result.url_result, result.repo_result]:
            if link_result is None:
                continue
            if link_result.status == LinkStatus.OK:
                ok_count += 1
            elif link_result.status == LinkStatus.REDIRECT:
                redirect_count += 1
            elif link_result.status != LinkStatus.SKIPPED:
                issues.append((result.entry_name, link_result))

    click.echo()
    click.secho("Results:", fg="blue", bold=True)
    click.echo(f"  OK: {ok_count}")
    click.echo(f"  Redirects: {redirect_count}")
    click.echo(f"  Issues: {len(issues)}")

    if issues:
        click.echo()
        click.secho("Issues found:", fg="red", bold=True)
        for entry_name, link_result in issues:
            status_color = "red" if link_result.status == LinkStatus.NOT_FOUND else "yellow"
            click.secho(f"  {entry_name}", fg=status_color)
            click.echo(f"    URL: {link_result.url}")
            click.echo(f"    Status: {link_result.status.value}")
            if link_result.error_message:
                click.echo(f"    Error: {link_result.error_message}")

    if issues:
        raise SystemExit(1)


@cli.command()
@click.option("--yaml", "-y", "yaml_path", type=click.Path(exists=True), default=None,
              help="Path to YAML file (default: data/entries.yml)")
@click.option("--concurrency", "-c", default=5, help="Number of concurrent requests")
@click.option("--sort", "-s", "sort_by", type=click.Choice(["stars", "name", "activity"]),
              default="stars", help="Sort results by")
@click.option("--show-topics", is_flag=True, help="Display repository topics")
@click.option("--update-db", is_flag=True, help="Update database with fetched topics")
@click.option("--db", "-d", "db_path", type=click.Path(), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
def github(yaml_path: str | None, concurrency: int, sort_by: str,
           show_topics: bool, update_db: bool, db_path: str | None):
    """Fetch GitHub statistics for all repositories."""
    import yaml as yaml_lib

    from src.github import get_github_token, run_fetch_stats

    path = Path(yaml_path) if yaml_path else DEFAULT_YAML

    with open(path) as f:
        entries = yaml_lib.safe_load(f)

    # Filter to GitHub repos only
    github_entries = [e for e in entries if e.get("repo") and "github.com" in e.get("repo", "")]

    if not github_entries:
        click.echo("No GitHub repositories found.")
        return

    token = get_github_token()
    if not token:
        click.secho("Warning: No GITHUB_TOKEN set. Rate limits will be strict.", fg="yellow")
        click.echo("Set GITHUB_TOKEN or GH_TOKEN environment variable for higher limits.")
        click.echo()

    click.echo(f"Fetching stats for {len(github_entries)} GitHub repos...")

    def progress(current, total, name):
        click.echo(f"  [{current}/{total}] {name}", nl=True)

    results = run_fetch_stats(entries, concurrency, progress)

    # Filter successful results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    if not successful:
        click.secho("No stats retrieved.", fg="red")
        if failed:
            click.echo("Errors:")
            for r in failed:
                click.echo(f"  {r.entry_name}: {r.error}")
        return

    # Sort results
    if sort_by == "stars":
        successful.sort(key=lambda r: r.stats.stars, reverse=True)
    elif sort_by == "activity":
        successful.sort(key=lambda r: r.stats.days_since_push or 9999)
    else:
        successful.sort(key=lambda r: r.entry_name.lower())

    click.echo()
    click.secho("GitHub Statistics:", fg="blue", bold=True)
    click.echo(f"{'Name':<25} {'Stars':>8} {'Forks':>7} {'Activity':<15} {'Language':<12}")
    click.echo("-" * 75)

    for r in successful:
        s = r.stats
        click.echo(
            f"{r.entry_name:<25} {s.stars:>8} {s.forks:>7} {s.activity_status:<15} {(s.language or 'N/A'):<12}"
        )
        if show_topics and s.topics:
            click.echo(f"  Topics: {', '.join(s.topics)}")

    click.echo()
    click.echo(f"Total: {len(successful)} repos")
    total_stars = sum(r.stats.stars for r in successful)
    click.echo(f"Combined stars: {total_stars:,}")

    # Show stale/archived repos
    stale = [r for r in successful if r.stats.activity_status in ("stale", "archived")]
    if stale:
        click.echo()
        click.secho("Stale/Archived repos:", fg="yellow")
        for r in stale:
            days = r.stats.days_since_push
            click.echo(f"  {r.entry_name}: {r.stats.activity_status} ({days} days since push)")

    if failed:
        click.echo()
        click.secho(f"Failed to fetch {len(failed)} repos:", fg="red")
        for r in failed:
            click.echo(f"  {r.entry_name}: {r.error}")

    # Update database with topics if requested
    if update_db:
        db_file = Path(db_path) if db_path else DEFAULT_DB
        if not db_file.exists():
            click.secho(f"Database not found: {db_file}", fg="red")
            click.echo("Run 'awesome-audio import' first to create the database.")
            raise SystemExit(1)

        session = get_session(db_file)
        updated = 0
        for r in successful:
            if r.stats.topics:
                entry = session.query(Entry).filter_by(name=r.entry_name).first()
                if entry:
                    entry.keywords = ", ".join(r.stats.topics)
                    updated += 1
        session.commit()
        session.close()
        click.echo()
        click.secho(f"Updated {updated} entries with topics in database", fg="green")


@cli.command()
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--output", "-o", "output_path", type=click.Path(), default=None,
              help="Output README path (default: stdout)")
@click.option("--template", "-t", "template_path", type=click.Path(exists=True), default=None,
              help="Custom Jinja2 template file")
def generate(db_path: str | None, output_path: str | None, template_path: str | None):
    """Generate README.md from database."""
    from src.generator import generate_readme

    db_file = Path(db_path) if db_path else DEFAULT_DB

    if not db_file.exists():
        click.secho(f"Database not found: {db_file}", fg="red")
        click.echo("Run 'awesome-audio import' first to create the database.")
        raise SystemExit(1)

    template = Path(template_path) if template_path else None
    output = Path(output_path) if output_path else None

    content = generate_readme(db_file, template, output)

    if output:
        click.secho(f"Generated README at {output}", fg="green")
    else:
        click.echo(content)


@cli.command()
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--category", "-c", required=True, help="Category (use 'categories' command to list)")
@click.option("--description", "-d", "desc", required=True, help="Project description")
@click.option("--url", "-u", default=None, help="Project URL")
@click.option("--repo", "-r", default=None, help="Repository URL")
@click.option("--db", "db_path", type=click.Path(), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--yaml", "-y", "yaml_path", type=click.Path(), default=None,
              help="Also append to YAML file")
def add(name: str, category: str, desc: str, url: str | None, repo: str | None,
        db_path: str | None, yaml_path: str | None):
    """Add a new entry to the database."""
    from src.model import init_db
    from src.schema import EntrySchema

    if not url and not repo:
        click.secho("Error: Must provide at least --url or --repo", fg="red")
        raise SystemExit(1)

    # Validate category
    if category not in CATEGORIES:
        click.secho(f"Error: '{category}' is not a canonical category", fg="red")
        click.echo("Use 'awesome-audio categories' to see valid categories.")
        raise SystemExit(1)

    # Validate entry
    try:
        EntrySchema(name=name, category=category, desc=desc, url=url, repo=repo)
    except Exception as e:
        click.secho(f"Validation error: {e}", fg="red")
        raise SystemExit(1)

    db_file = Path(db_path) if db_path else DEFAULT_DB
    session = init_db(db_file)

    # Check if entry already exists
    existing = session.query(Entry).filter_by(name=name).first()
    if existing:
        click.secho(f"Entry '{name}' already exists", fg="yellow")
        raise SystemExit(1)

    # Add to database
    entry = Entry(
        name=name,
        category=category,
        url=url,
        repo=repo,
        description=desc,
    )
    session.add(entry)
    session.commit()
    session.close()

    click.secho(f"Added '{name}' to database", fg="green")

    # Optionally append to YAML
    if yaml_path:
        import yaml as yaml_lib
        yaml_file = Path(yaml_path)

        entry_dict = {
            "name": name,
            "category": category,
            "desc": desc,
            "url": url,
            "repo": repo,
        }

        with open(yaml_file, "a") as f:
            f.write("\n")
            f.write(yaml_lib.dump([entry_dict], sort_keys=False, indent=2))

        click.echo(f"Appended to {yaml_file}")


@cli.command()
@click.option("--yaml", "-y", "yaml_path", type=click.Path(exists=True), default=None,
              help="Path to YAML file (default: data/entries.yml)")
@click.option("--days", "-d", default=365, help="Days since last push to consider stale")
@click.option("--concurrency", "-c", default=5, help="Number of concurrent requests")
def stale(yaml_path: str | None, days: int, concurrency: int):
    """Find stale/unmaintained projects using GitHub data."""
    import yaml as yaml_lib

    from src.github import get_github_token, run_fetch_stats

    path = Path(yaml_path) if yaml_path else DEFAULT_YAML

    with open(path) as f:
        entries = yaml_lib.safe_load(f)

    # Filter to GitHub repos only
    github_entries = [e for e in entries if e.get("repo") and "github.com" in e.get("repo", "")]

    if not github_entries:
        click.echo("No GitHub repositories found.")
        return

    token = get_github_token()
    if not token:
        click.secho("Warning: No GITHUB_TOKEN set. Rate limits will be strict.", fg="yellow")
        click.echo()

    click.echo(f"Checking {len(github_entries)} GitHub repos for staleness...")

    def progress(current, total, name):
        click.echo(f"  [{current}/{total}] {name}", nl=True)

    results = run_fetch_stats(entries, concurrency, progress)

    # Filter to stale repos
    stale_repos = []
    archived_repos = []
    active_repos = []

    for r in results:
        if not r.success:
            continue

        if r.stats.archived:
            archived_repos.append(r)
        elif r.stats.days_since_push and r.stats.days_since_push > days:
            stale_repos.append(r)
        else:
            active_repos.append(r)

    # Sort stale by days since push
    stale_repos.sort(key=lambda r: r.stats.days_since_push or 0, reverse=True)

    click.echo()
    click.secho("Results:", fg="blue", bold=True)
    click.echo(f"  Active: {len(active_repos)}")
    click.echo(f"  Stale (>{days} days): {len(stale_repos)}")
    click.echo(f"  Archived: {len(archived_repos)}")

    if archived_repos:
        click.echo()
        click.secho("Archived repositories:", fg="red", bold=True)
        for r in archived_repos:
            click.echo(f"  {r.entry_name}")
            click.echo(f"    {r.repo_url}")

    if stale_repos:
        click.echo()
        click.secho(f"Stale repositories (>{days} days since push):", fg="yellow", bold=True)
        for r in stale_repos:
            days_ago = r.stats.days_since_push
            click.echo(f"  {r.entry_name}: {days_ago} days ago")
            click.echo(f"    {r.repo_url}")

    # Summary
    total_checked = len(active_repos) + len(stale_repos) + len(archived_repos)
    if total_checked > 0:
        health_pct = len(active_repos) / total_checked * 100
        click.echo()
        click.echo(f"Repository health: {health_pct:.1f}% active")


@cli.command()
@click.argument("name")
@click.option("--db", "-d", "db_path", type=click.Path(exists=True), default=None,
              help="Path to SQLite database (default: awesome-audio.db)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def remove(name: str, db_path: str | None, yes: bool):
    """Remove an entry from the database."""
    db_file = Path(db_path) if db_path else DEFAULT_DB

    if not db_file.exists():
        click.secho(f"Database not found: {db_file}", fg="red")
        raise SystemExit(1)

    session = get_session(db_file)
    entry = session.query(Entry).filter_by(name=name).first()

    if not entry:
        click.secho(f"Entry '{name}' not found", fg="yellow")
        session.close()
        raise SystemExit(1)

    click.echo(f"Entry: {entry.name}")
    click.echo(f"  Category: {entry.category}")
    click.echo(f"  Description: {entry.description}")

    if not yes:
        if not click.confirm("Remove this entry?"):
            click.echo("Cancelled")
            session.close()
            return

    session.delete(entry)
    session.commit()
    session.close()

    click.secho(f"Removed '{name}'", fg="green")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
