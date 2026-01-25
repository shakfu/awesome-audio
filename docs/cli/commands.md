# CLI Commands

Complete reference for all CLI commands.

## validate

Validate the entries YAML file.

```bash
awesome-audio validate [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-y, --yaml PATH` | Path to YAML file (default: data/entries.yml) |

**Example:**

```bash
awesome-audio validate
awesome-audio validate -y custom-entries.yml
```

---

## import

Import entries from YAML to SQLite database.

```bash
awesome-audio import [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-y, --yaml PATH` | Path to YAML file |
| `-d, --db PATH` | Path to SQLite database |
| `--update/--no-update` | Update existing entries instead of skipping |

**Example:**

```bash
awesome-audio import
awesome-audio import --update
```

---

## export

Export entries from database to YAML.

```bash
awesome-audio export [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |
| `-o, --output PATH` | Output YAML file (required) |

**Example:**

```bash
awesome-audio export -o backup.yml
```

---

## list

List all entries in the database.

```bash
awesome-audio list [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |
| `-c, --category TEXT` | Filter by category |
| `-f, --format [table\|json\|yaml]` | Output format (default: table) |

**Example:**

```bash
awesome-audio list
awesome-audio list -c dsp
awesome-audio list -f json
```

---

## search

Search entries by name or description.

```bash
awesome-audio search QUERY [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |

**Example:**

```bash
awesome-audio search "audio"
awesome-audio search "python"
```

---

## stats

Show database statistics.

```bash
awesome-audio stats [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |

---

## categories

List canonical categories.

```bash
awesome-audio categories
```

---

## add

Add a new entry to the database.

```bash
awesome-audio add [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Project name (required) |
| `-c, --category TEXT` | Category (required) |
| `-d, --description TEXT` | Project description (required) |
| `-u, --url TEXT` | Project URL |
| `-r, --repo TEXT` | Repository URL |
| `--db PATH` | Path to SQLite database |
| `-y, --yaml PATH` | Also append to YAML file |

**Example:**

```bash
awesome-audio add -n "my-project" -c "dsp" -d "My DSP library" -r "https://github.com/me/my-project"
```

---

## remove

Remove an entry from the database.

```bash
awesome-audio remove NAME [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |
| `-y, --yes` | Skip confirmation |

**Example:**

```bash
awesome-audio remove "old-project"
awesome-audio remove "old-project" -y
```

---

## check

Check all URLs for broken links.

```bash
awesome-audio check [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-y, --yaml PATH` | Path to YAML file |
| `-c, --concurrency INT` | Number of concurrent requests (default: 10) |
| `-t, --timeout FLOAT` | Timeout per request in seconds (default: 10) |

**Example:**

```bash
awesome-audio check
awesome-audio check -c 20 -t 15
```

---

## github

Fetch GitHub statistics for all repositories.

```bash
awesome-audio github [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-y, --yaml PATH` | Path to YAML file |
| `-c, --concurrency INT` | Number of concurrent requests (default: 5) |
| `-s, --sort [stars\|name\|activity]` | Sort results by (default: stars) |
| `--show-topics` | Display repository topics |
| `--update-db` | Update database with fetched topics |
| `-d, --db PATH` | Path to SQLite database |

**Environment Variables:**

- `GITHUB_TOKEN` or `GH_TOKEN` - GitHub API token for higher rate limits

**Example:**

```bash
awesome-audio github
awesome-audio github -s activity
awesome-audio github --show-topics
awesome-audio github --update-db
```

---

## stale

Find stale/unmaintained projects.

```bash
awesome-audio stale [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-y, --yaml PATH` | Path to YAML file |
| `-d, --days INT` | Days since last push to consider stale (default: 365) |
| `-c, --concurrency INT` | Number of concurrent requests (default: 5) |

**Example:**

```bash
awesome-audio stale
awesome-audio stale -d 180
```

---

## generate

Generate README.md from database.

```bash
awesome-audio generate [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to SQLite database |
| `-o, --output PATH` | Output README path (default: stdout) |
| `-t, --template PATH` | Custom Jinja2 template file |

**Example:**

```bash
awesome-audio generate
awesome-audio generate -o README.md
```
