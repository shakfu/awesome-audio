"""README generator using Jinja2 templates."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.model import Entry, get_session

# Default template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Default README template
DEFAULT_TEMPLATE = """# Awesome Audio

> A curated guide to open-source audio and music projects.

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

This list contains **{{ total_entries }}** projects across **{{ total_categories }}** categories.

*Last updated: {{ generated_at }}*

## Contents

{% for category in categories %}
- [{{ category.title }}](#{{ category.anchor }})
{% endfor %}

---

{% for category in categories %}
## {{ category.title }}

{% for entry in category.entries %}
- **[{{ entry.name }}]({{ entry.url or entry.repo }})** - {{ entry.description }}{% if entry.stars %} ({{ entry.stars }} stars){% endif %}

{% endfor %}
{% endfor %}

---

## Contributing

Contributions welcome! Please read the contribution guidelines first.

## Documentation

See [docs/README.md](docs/README.md) for documentation on the CLI tool used to manage this list.

## License

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](http://creativecommons.org/publicdomain/zero/1.0/)

To the extent possible under law, the authors have waived all copyright and related rights to this work.
"""


def normalize_category(category: str) -> str:
    """Normalize a category string for display."""
    # Split on common separators and take first meaningful word
    words = category.replace("-", " ").replace("_", " ").split()
    # Title case each word
    return " ".join(word.capitalize() for word in words)


def category_anchor(category: str) -> str:
    """Generate a markdown anchor from a category name."""
    return category.lower().replace(" ", "-").replace("_", "-")


def group_entries_by_category(entries: list[Entry]) -> dict[str, list[Entry]]:
    """Group entries by their category."""
    groups = defaultdict(list)
    for entry in entries:
        groups[entry.category].append(entry)
    return dict(groups)


def generate_readme(
    db_path: Optional[Path] = None,
    template_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    stats: Optional[dict] = None,
) -> str:
    """
    Generate README.md from database entries.

    Args:
        db_path: Path to SQLite database
        template_path: Path to Jinja2 template file
        output_path: Path to write output (if None, returns string only)
        stats: Optional dict mapping entry names to GitHub stats

    Returns:
        Generated README content as string
    """
    session = get_session(db_path)
    entries = session.query(Entry).order_by(Entry.category, Entry.name).all()
    session.close()

    if not entries:
        return "# Awesome Audio\n\nNo entries yet.\n"

    # Group entries by category
    grouped = group_entries_by_category(entries)

    # Build category data for template
    categories = []
    for cat_name in sorted(grouped.keys()):
        cat_entries = grouped[cat_name]
        entry_data = []

        for entry in sorted(cat_entries, key=lambda e: e.name.lower()):
            data = {
                "name": entry.name,
                "url": entry.url,
                "repo": entry.repo,
                "description": entry.description,
                "stars": None,
            }

            # Add GitHub stats if available
            if stats and entry.name in stats:
                entry_stats = stats[entry.name]
                if hasattr(entry_stats, "stars"):
                    data["stars"] = entry_stats.stars

            entry_data.append(data)

        categories.append({
            "name": cat_name,
            "title": normalize_category(cat_name),
            "anchor": category_anchor(normalize_category(cat_name)),
            "entries": entry_data,
            "count": len(entry_data),
        })

    # Prepare template context
    context = {
        "categories": categories,
        "total_entries": len(entries),
        "total_categories": len(categories),
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
    }

    # Load and render template
    if template_path and template_path.exists():
        env = Environment(loader=FileSystemLoader(template_path.parent))
        template = env.get_template(template_path.name)
        content = template.render(**context)
    else:
        # Use default template
        from jinja2 import Template
        template = Template(DEFAULT_TEMPLATE)
        content = template.render(**context)

    # Write output if path provided
    if output_path:
        with open(output_path, "w") as f:
            f.write(content)

    return content


def create_template_file(output_path: Path) -> None:
    """Create a template file that can be customized."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(DEFAULT_TEMPLATE)
