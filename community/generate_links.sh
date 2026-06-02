#!/usr/bin/env bash
#
# ClickHouse Community Links Generator
# =====================================
# Generates README badges, documentation links, and social media references
# from the centralized community configuration.
#
# Usage:
#   ./generate_links.sh [OPTIONS]
#
# Options:
#   --output <FILE>       Output file (default: stdout)
#   --format <md|html|json|yaml>  Output format (default: md)
#   --section <all|badges|links|social>  Section to generate
#   --help                Show this help message

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly CONFIG_FILE="${SCRIPT_DIR}/channels.ini"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

show_help() {
    head -15 "$0" | tail -13 | sed 's/^# \?//'
    exit 0
}

# Parse INI file
get_config() {
    local section="$1"
    local key="$2"
    sed -n "/^\[$section\]/,/^\[/p" "$CONFIG_FILE" | grep "^${key}=" | cut -d'=' -f2-
}

get_all_section() {
    local section="$1"
    sed -n "/^\[$section\]/,/^\[/p" "$CONFIG_FILE" | grep "=" | grep -v "^\["
}

# Generate Markdown badges
generate_badges_md() {
    cat << 'EOF'
<div align="center">

[![Website](https://img.shields.io/website?up_message=AVAILABLE&down_message=DOWN&url=https%3A%2F%2Fclickhouse.com&style=for-the-badge)](https://clickhouse.com)
[![Apache 2.0 License](https://img.shields.io/badge/license-Apache%202.0-blueviolet?style=for-the-badge)](https://www.apache.org/licenses/LICENSE-2.0)
[![Slack](https://img.shields.io/badge/slack-join%20chat-4A154B?style=for-the-badge)](https://clickhouse.com/slack)
[![Telegram](https://img.shields.io/badge/telegram-join%20chat-2CA5E0?style=for-the-badge)](https://telegram.me/clickhouse_en)
[![YouTube](https://img.shields.io/badge/youtube-subscribe-FF0000?style=for-the-badge)](https://www.youtube.com/c/ClickHouseDB)
[![Twitter](https://img.shields.io/badge/twitter-follow-1DA1F2?style=for-the-badge)](https://x.com/ClickHouseDB)

</div>
EOF
}

# Generate Markdown links section
generate_links_md() {
    cat << EOF
## Useful Links

* [Official website]($(get_config official website)) has a quick high-level overview of ClickHouse on the main page.
* [ClickHouse Cloud]($(get_config official cloud)) ClickHouse as a service, built by the creators and maintainers.
* [Tutorial]($(get_config docs getting_started)) shows how to set up and query a small ClickHouse cluster.
* [Documentation]($(get_config official docs)) provides more in-depth information.
* [YouTube channel]($(get_config social youtube)) has a lot of content about ClickHouse in video format.
* [ClickHouse Theater]($(get_config official presentations)) contains presentations and videos about ClickHouse.
* [Slack]($(get_config social slack)) and [Telegram]($(get_config social telegram_en)) allow chatting with ClickHouse users in real-time.
* [Blog]($(get_config official blog)) contains various ClickHouse-related articles, as well as announcements and reports about events.
* [Bluesky]($(get_config social bluesky)) and [X]($(get_config social twitter)) for short news.
* [Code Browser (github.dev)]($(get_config dev github_dev)) with syntax highlighting, powered by github.dev.
* [Contacts]($(get_config official contact)) can help to get your questions answered if there are any.
EOF
}

# Generate social links section
generate_social_md() {
    cat << EOF
## Community Channels

| Platform | Link | Description |
|----------|------|-------------|
| Slack | [Join Slack]($(get_config social slack)) | Primary community chat |
| Telegram (EN) | [Join Telegram]($(get_config social telegram_en)) | English-speaking community |
| Telegram (RU) | [Join Telegram RU]($(get_config social telegram_ru)) | Russian-speaking community |
| YouTube | [Subscribe]($(get_config social youtube)) | Video content and tutorials |
| Bluesky | [Follow]($(get_config social bluesky)) | Short news and updates |
| X (Twitter) | [Follow]($(get_config social twitter)) | Short news and updates |
| GitHub | [View Repository]($(get_config social github)) | Source code and issues |
EOF
}

# Generate JSON output
generate_json() {
    cat << EOF
{
  "official": {
    "website": "$(get_config official website)",
    "cloud": "$(get_config official cloud)",
    "docs": "$(get_config official docs)",
    "blog": "$(get_config official blog)",
    "careers": "$(get_config official careers)",
    "contact": "$(get_config official contact)",
    "presentations": "$(get_config official presentations)"
  },
  "social": {
    "slack": "$(get_config social slack)",
    "telegram_en": "$(get_config social telegram_en)",
    "telegram_ru": "$(get_config social telegram_ru)",
    "youtube": "$(get_config social youtube)",
    "bluesky": "$(get_config social bluesky)",
    "twitter": "$(get_config social twitter)",
    "github": "$(get_config social github)"
  },
  "docs": {
    "getting_started": "$(get_config docs getting_started)",
    "install": "$(get_config docs install)",
    "quick_start": "$(get_config docs quick_start)",
    "cloud_docs": "$(get_config docs cloud_docs)"
  },
  "events": {
    "events_page": "$(get_config events events_page)",
    "release_calls": "$(get_config events release_calls)",
    "luma": "$(get_config events luma)",
    "meetup_playlist": "$(get_config events meetup_playlist)"
  },
  "dev": {
    "github_dev": "$(get_config dev github_dev)",
    "ci_dashboard": "$(get_config dev ci_dashboard)",
    "issues": "$(get_config dev issues)",
    "pull_requests": "$(get_config dev pull_requests)",
    "contributing": "$(get_config dev contributing)"
  }
}
EOF
}

# Generate YAML output
generate_yaml() {
    cat << EOF
# ClickHouse Community Links - YAML Format
# Auto-generated by community/generate_links.sh

official:
  website: $(get_config official website)
  cloud: $(get_config official cloud)
  docs: $(get_config official docs)
  blog: $(get_config official blog)
  careers: $(get_config official careers)
  contact: $(get_config official contact)
  presentations: $(get_config official presentations)

social:
  slack: $(get_config social slack)
  telegram_en: $(get_config social telegram_en)
  telegram_ru: $(get_config social telegram_ru)
  youtube: $(get_config social youtube)
  bluesky: $(get_config social bluesky)
  twitter: $(get_config social twitter)
  github: $(get_config social github)

docs:
  getting_started: $(get_config docs getting_started)
  install: $(get_config docs install)
  quick_start: $(get_config docs quick_start)
  cloud_docs: $(get_config docs cloud_docs)

events:
  events_page: $(get_config events events_page)
  release_calls: $(get_config events release_calls)
  luma: $(get_config events luma)
  meetup_playlist: $(get_config events meetup_playlist)

dev:
  github_dev: $(get_config dev github_dev)
  ci_dashboard: $(get_config dev ci_dashboard)
  issues: $(get_config dev issues)
  pull_requests: $(get_config dev pull_requests)
  contributing: $(get_config dev contributing)
EOF
}

main() {
    local output=""
    local format="md"
    local section="all"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output) output="$2"; shift 2 ;;
            --format) format="$2"; shift 2 ;;
            --section) section="$2"; shift 2 ;;
            --help|-h) show_help ;;
            *) log_error "Unknown option: $1"; show_help ;;
        esac
    done

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi

    log_info "Generating community links (format: $format, section: $section)..."

    local result=""
    
    case "$format" in
        md)
            case "$section" in
                badges) result="$(generate_badges_md)" ;;
                links) result="$(generate_links_md)" ;;
                social) result="$(generate_social_md)" ;;
                all)
                    result="$(generate_badges_md)"
                    result+=$'\n\n'
                    result+="$(generate_links_md)"
                    result+=$'\n\n'
                    result+="$(generate_social_md)"
                    ;;
                *) log_error "Unknown section: $section"; exit 1 ;;
            esac
            ;;
        json) result="$(generate_json)" ;;
        yaml) result="$(generate_yaml)" ;;
        html)
            log_error "HTML format not yet implemented"
            exit 1
            ;;
        *) log_error "Unknown format: $format"; exit 1 ;;
    esac

    if [[ -n "$output" ]]; then
        echo "$result" > "$output"
        log_success "Output written to: $output"
    else
        echo "$result"
    fi
}

main "$@"
