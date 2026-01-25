# CLI Overview

The `awesome-audio` CLI provides commands for managing the curated list of audio projects.

## Installation

After installing the package, the CLI is available as `awesome-audio`:

```bash
awesome-audio --help
```

## Command Groups

### Data Management

| Command | Description |
|---------|-------------|
| `validate` | Validate YAML file for errors |
| `import` | Import YAML to SQLite database |
| `export` | Export database to YAML |
| `add` | Add new entry |
| `remove` | Remove entry |

### Querying

| Command | Description |
|---------|-------------|
| `list` | List all entries |
| `search` | Search by keyword |
| `stats` | Show statistics |
| `categories` | List canonical categories |

### Quality Assurance

| Command | Description |
|---------|-------------|
| `check` | Validate URLs |
| `github` | Fetch GitHub stats |
| `stale` | Find unmaintained projects |

### Generation

| Command | Description |
|---------|-------------|
| `generate` | Generate README |

## Global Options

```bash
awesome-audio --version  # Show version
awesome-audio --help     # Show help
```

## Common Workflows

### Initial Setup

```bash
awesome-audio validate && awesome-audio import
```

### Quality Check

```bash
awesome-audio check && awesome-audio github && awesome-audio stale
```

### Update README

```bash
awesome-audio generate -o README.md
```
