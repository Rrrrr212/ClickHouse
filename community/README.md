# ClickHouse Community

Centralized community configuration and link generation.

## Configuration

All community links are stored in `channels.ini`. To update community links:

1. Edit `channels.ini`
2. Run `./generate_links.sh` to regenerate references

## Generating Links

Generate Markdown badges and links:

```bash
./community/generate_links.sh
```

Generate JSON output for programmatic access:

```bash
./community/generate_links.sh --format json
```

Generate YAML output:

```bash
./community/generate_links.sh --format yaml
```

Save to file:

```bash
./community/generate_links.sh --output docs/community-links.md
```

Generate specific section:

```bash
./community/generate_links.sh --section badges
./community/generate_links.sh --section social
./community/generate_links.sh --section links
```

## Configuration Sections

- `[official]` - Official ClickHouse websites
- `[social]` - Social media and community channels
- `[docs]` - Documentation links
- `[events]` - Events and meetups
- `[dev]` - Development resources
- `[support]` - Support channel priorities
