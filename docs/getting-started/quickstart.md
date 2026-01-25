# Quick Start

This guide walks you through the basic workflow of using awesome-audio.

## 1. Validate the Data

First, validate the YAML entries file:

```bash
awesome-audio validate
```

This checks for:

- Schema errors (missing fields, invalid URLs)
- Duplicate entries
- Non-canonical categories

## 2. Import to Database

Import the validated entries into SQLite:

```bash
awesome-audio import
```

This creates `awesome-audio.db` with all entries.

## 3. Search and Explore

Search for entries:

```bash
# Search by keyword
awesome-audio search "dsp"

# List all entries
awesome-audio list

# Filter by category
awesome-audio list -c analysis

# View statistics
awesome-audio stats
```

## 4. Check Links

Validate all URLs for broken links:

```bash
awesome-audio check
```

## 5. Fetch GitHub Stats

Get repository statistics (requires optional GITHUB_TOKEN for higher rate limits):

```bash
# Set token (optional but recommended)
export GITHUB_TOKEN=your_token_here

# Fetch stats
awesome-audio github
```

## 6. Find Stale Projects

Identify unmaintained projects:

```bash
awesome-audio stale
```

## 7. Normalize Categories

Consolidate non-canonical categories:

```bash
# Preview changes
awesome-audio normalize --dry-run

# Apply normalization
awesome-audio normalize
```

## 8. Generate README

Generate a README from the database:

```bash
awesome-audio generate -o README.md
```

## Adding New Entries

Add a new project:

```bash
awesome-audio add \
  -n "my-project" \
  -c "dsp" \
  -d "Description of my project" \
  -r "https://github.com/user/my-project"
```

## Next Steps

- See [CLI Reference](../cli/commands.md) for all commands
- Read [Contributing](../development/contributing.md) to add entries
- Check [Architecture](../development/architecture.md) for code structure
