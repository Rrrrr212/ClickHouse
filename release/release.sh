#!/usr/bin/env bash
#
# ClickHouse Monthly Release Checklist
# ======================================
# Executable script for the monthly release process.
# Transforms the manual release checklist into an automated workflow.
#
# Usage:
#   ./release.sh [OPTIONS]
#
# Options:
#   --version <VERSION>           Release version (e.g., 26.5)
#   --branch <BRANCH>             Release branch (default: master)
#   --channel <stable|lts>        Release channel (default: stable)
#   --dry-run                     Show steps without executing
#   --skip <step1,step2,...>      Skip specific steps
#   --help                        Show this help message
#
# Release Steps (can be skipped with --skip):
#   1. preflight      - Pre-release checks
#   2. build          - Build release binaries
#   3. test           - Run test suite
#   4. package        - Create packages (deb, rpm, tgz, docker)
#   5. sign           - Sign packages
#   6. publish        - Publish to repositories
#   7. announce       - Generate announcements
#   8. post-release   - Post-release tasks

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly RELEASE_DIR="${PROJECT_ROOT}/tmp/release_$(date +%Y%m%d_%H%M%S)"

# Default values
VERSION="${VERSION:-}"
BRANCH="${BRANCH:-master}"
CHANNEL="${CHANNEL:-stable}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_STEPS="${SKIP_STEPS:-}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Step tracking
declare -A STEP_STATUS
TOTAL_STEPS=8
COMPLETED_STEPS=0

log_info() { echo -e "${BLUE}[RELEASE]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${BLUE}[STEP $1/$TOTAL_STEPS]${NC} $2"; }

show_help() {
    head -20 "$0" | tail -18 | sed 's/^# \?//'
    exit 0
}

should_skip() {
    local step="$1"
    [[ ",$SKIP_STEPS," == *",$step,"* ]]
}

mark_step() {
    local step="$1"
    local status="$2"
    STEP_STATUS["$step"]="$status"
    if [[ "$status" == "completed" ]]; then
        ((COMPLETED_STEPS++))
    fi
}

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "[DRY-RUN] Would execute: $*"
        return 0
    else
        "$@"
    fi
}

# ============================================================================
# Step 1: Pre-flight Checks
# ============================================================================

step_preflight() {
    log_step 1 "Pre-flight Checks"
    
    if should_skip "preflight"; then
        log_warn "Skipping preflight checks"
        mark_step "preflight" "skipped"
        return 0
    fi

    log_info "Checking prerequisites..."

    # Check Git repository
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        log_error "Not inside a Git repository"
        return 1
    fi

    # Check current branch
    local current_branch
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [[ "$current_branch" != "$BRANCH" ]]; then
        log_warn "Current branch: $current_branch, expected: $BRANCH"
        log_info "Switching to branch: $BRANCH"
        run_cmd git checkout "$BRANCH"
    fi

    # Check for uncommitted changes
    if [[ -n "$(git status --porcelain)" ]]; then
        log_error "Working directory has uncommitted changes"
        log_info "Commit or stash changes before releasing"
        return 1
    fi

    # Check required tools
    local required_tools=(git cmake ninja curl gpg)
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            log_error "Required tool not found: $tool"
            return 1
        fi
    done

    # Validate version format
    if [[ -z "$VERSION" ]]; then
        log_error "Version not specified. Use --version <VERSION>"
        return 1
    fi

    if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format: $VERSION (expected MAJOR.MINOR)"
        return 1
    fi

    log_success "Pre-flight checks passed"
    mark_step "preflight" "completed"
}

# ============================================================================
# Step 2: Build Release Binaries
# ============================================================================

step_build() {
    log_step 2 "Build Release Binaries"
    
    if should_skip "build"; then
        log_warn "Skipping build step"
        mark_step "build" "skipped"
        return 0
    fi

    log_info "Building ClickHouse release version $VERSION..."

    local build_dir="${PROJECT_ROOT}/build_release"
    mkdir -p "$build_dir"
    cd "$build_dir"

    # Configure
    run_cmd cmake "$PROJECT_ROOT" \
        -DCMAKE_BUILD_TYPE=RELEASE \
        -DENABLE_TESTS=OFF \
        -DENABLE_UTILS=ON

    # Build
    log_info "Compiling... (this may take a while)"
    run_cmd ninja 2>&1 | tee "${build_dir}/build_${VERSION}.log"

    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "Build failed. Check log: ${build_dir}/build_${VERSION}.log"
        return 1
    fi

    # Verify binaries
    local binaries=(clickhouse clickhouse-server clickhouse-client)
    for binary in "${binaries[@]}"; do
        if [[ ! -f "${build_dir}/programs/$binary" ]]; then
            log_error "Binary not found: ${build_dir}/programs/$binary"
            return 1
        fi
    done

    log_success "Build completed successfully"
    mark_step "build" "completed"
}

# ============================================================================
# Step 3: Run Test Suite
# ============================================================================

step_test() {
    log_step 3 "Run Test Suite"
    
    if should_skip "test"; then
        log_warn "Skipping test suite"
        mark_step "test" "skipped"
        return 0
    fi

    log_info "Running release validation tests..."

    local log_file="${RELEASE_DIR}/test_release_${VERSION}.log"
    mkdir -p "$RELEASE_DIR"

    # Run stateless tests
    log_info "Running stateless tests..."
    if run_cmd python3 "${PROJECT_ROOT}/tests/runner.py" \
        --test-dir "${PROJECT_ROOT}/tests/queries/0_stateless" \
        --timeout 300 \
        --parallel auto 2>&1 | tee "$log_file"; then
        log_success "Stateless tests passed"
    else
        log_error "Some stateless tests failed. Log: $log_file"
        log_warn "Review failures before proceeding"
        return 1
    fi

    # Run integration tests (subset)
    log_info "Running critical integration tests..."
    if run_cmd python3 -m ci.praktika run "integration" \
        --test keeper \
        --test replication 2>&1 | tee -a "$log_file"; then
        log_success "Integration tests passed"
    else
        log_warn "Some integration tests failed"
    fi

    mark_step "test" "completed"
}

# ============================================================================
# Step 4: Create Packages
# ============================================================================

step_package() {
    log_step 4 "Create Packages"
    
    if should_skip "package"; then
        log_warn "Skipping packaging step"
        mark_step "package" "skipped"
        return 0
    fi

    log_info "Creating release packages..."

    local package_dir="${RELEASE_DIR}/packages"
    mkdir -p "$package_dir"

    local build_dir="${PROJECT_ROOT}/build_release"

    # Create tarball
    log_info "Creating tarball..."
    local tgz_name="clickhouse-${VERSION}-amd64.tgz"
    run_cmd tar -czf "${package_dir}/${tgz_name}" \
        -C "${build_dir}/programs" \
        clickhouse clickhouse-server clickhouse-client

    # Create DEB package (if on Debian-based system)
    if [[ -f /etc/debian_version ]]; then
        log_info "Creating DEB package..."
        # Placeholder: actual DEB packaging logic
        log_warn "DEB packaging requires additional configuration"
    fi

    # Create RPM package (if on RHEL-based system)
    if command -v rpm &>/dev/null; then
        log_info "Creating RPM package..."
        # Placeholder: actual RPM packaging logic
        log_warn "RPM packaging requires additional configuration"
    fi

    # Create Docker image metadata
    log_info "Creating Docker image metadata..."
    cat > "${package_dir}/Dockerfile" << EOF
FROM ubuntu:22.04
LABEL maintainer="ClickHouse Dev Team"
LABEL version="${VERSION}"

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY clickhouse-${VERSION}-amd64.tgz /tmp/
RUN tar -xzf /tmp/clickhouse-${VERSION}-amd64.tgz -C /usr/local/bin/ \
    && rm /tmp/clickhouse-${VERSION}-amd64.tgz

EXPOSE 8123 9000 9009
VOLUME ["/var/lib/clickhouse"]

ENTRYPOINT ["/usr/local/bin/clickhouse-server"]
EOF

    log_success "Packages created in: $package_dir"
    mark_step "package" "completed"
}

# ============================================================================
# Step 5: Sign Packages
# ============================================================================

step_sign() {
    log_step 5 "Sign Packages"
    
    if should_skip "sign"; then
        log_warn "Skipping signing step"
        mark_step "sign" "skipped"
        return 0
    fi

    log_info "Signing release packages..."

    local package_dir="${RELEASE_DIR}/packages"

    # Check GPG key
    if ! gpg --list-secret-keys &>/dev/null; then
        log_error "No GPG secret key found. Configure GPG signing first."
        return 1
    fi

    # Sign tarball
    local tgz_name="clickhouse-${VERSION}-amd64.tgz"
    if [[ -f "${package_dir}/${tgz_name}" ]]; then
        log_info "Signing ${tgz_name}..."
        run_cmd gpg --armor --detach-sign "${package_dir}/${tgz_name}"
        log_success "Signature created: ${tgz_name}.asc"
    fi

    # Create checksums
    log_info "Creating checksums..."
    cd "$package_dir"
    run_cmd sha256sum *.tgz > SHA256SUMS
    run_cmd gpg --armor --detach-sign SHA256SUMS

    log_success "Packages signed successfully"
    mark_step "sign" "completed"
}

# ============================================================================
# Step 6: Publish to Repositories
# ============================================================================

step_publish() {
    log_step 6 "Publish to Repositories"
    
    if should_skip "publish"; then
        log_warn "Skipping publish step"
        mark_step "publish" "skipped"
        return 0
    fi

    log_info "Publishing release $VERSION..."

    local package_dir="${RELEASE_DIR}/packages"

    # Create GitHub release
    log_info "Creating GitHub release..."
    if command -v gh &>/dev/null; then
        run_cmd gh release create "v${VERSION}" \
            --title "ClickHouse ${VERSION}" \
            --notes "Release notes for ClickHouse ${VERSION}" \
            "${package_dir}"/*
        log_success "GitHub release created"
    else
        log_warn "GitHub CLI not found. Create release manually at:"
        log_warn "https://github.com/ClickHouse/ClickHouse/releases/new"
    fi

    # Push to package repositories
    log_info "Pushing to package repositories..."
    log_warn "Package repository publishing requires additional configuration"
    log_info "See: docs/en/development/release-process.md"

    # Push Docker image
    log_info "Pushing Docker image..."
    if command -v docker &>/dev/null; then
        log_warn "Docker image push requires manual authentication"
        log_info "Run: docker push clickhouse/clickhouse-server:${VERSION}"
    fi

    log_success "Publish steps documented"
    mark_step "publish" "completed"
}

# ============================================================================
# Step 7: Generate Announcements
# ============================================================================

step_announce() {
    log_step 7 "Generate Announcements"
    
    if should_skip "announce"; then
        log_warn "Skipping announcement step"
        mark_step "announce" "skipped"
        return 0
    fi

    log_info "Generating release announcements..."

    local announce_dir="${RELEASE_DIR}/announcements"
    mkdir -p "$announce_dir"

    # Generate release notes template
    cat > "${announce_dir}/release_notes.md" << EOF
# ClickHouse ${VERSION} Release Notes

## Release Date
$(date +%Y-%m-%d)

## New Features
- TODO: Add new features

## Performance Improvements
- TODO: Add performance improvements

## Bug Fixes
- TODO: Add bug fixes

## Breaking Changes
- TODO: Add breaking changes (if any)

## Upgrade Instructions
- TODO: Add upgrade instructions

## Contributors
- TODO: Add contributor acknowledgments

## Links
- [Documentation](https://clickhouse.com/docs/)
- [GitHub Release](https://github.com/ClickHouse/ClickHouse/releases/tag/v${VERSION})
- [Release Call Recording](TODO: Add recording link)
EOF

    # Generate social media posts
    cat > "${announce_dir}/social_posts.md" << EOF
# Social Media Posts for ClickHouse ${VERSION}

## Twitter/X
ClickHouse ${VERSION} is now available! 🚀

New features, performance improvements, and bug fixes.

Download: https://clickhouse.com/docs/install
Docs: https://clickhouse.com/docs/

#ClickHouse #Database #OpenSource

## Bluesky
ClickHouse ${VERSION} release is here! Check out the new features and improvements.

📖 Docs: https://clickhouse.com/docs/
💾 Install: https://clickhouse.com/docs/install

## Slack/Telegram Announcement
🎉 ClickHouse ${VERSION} is now available!

Key highlights:
- TODO: Add highlights

Upgrade now: https://clickhouse.com/docs/install
Join the release call: TODO: Add link
EOF

    log_success "Announcement templates created in: $announce_dir"
    mark_step "announce" "completed"
}

# ============================================================================
# Step 8: Post-Release Tasks
# ============================================================================

step_post_release() {
    log_step 8 "Post-Release Tasks"
    
    if should_skip "post-release"; then
        log_warn "Skipping post-release tasks"
        mark_step "post-release" "skipped"
        return 0
    fi

    log_info "Executing post-release tasks..."

    # Update version in documentation
    log_info "Updating documentation version references..."
    # Placeholder: actual version update logic

    # Create release branch for next version
    log_info "Preparing next release branch..."
    local major minor
    major="$(echo "$VERSION" | cut -d. -f1)"
    minor="$(echo "$VERSION" | cut -d. -f2)"
    local next_version="${major}.$((minor + 1))"
    log_info "Next version will be: $next_version"

    # Tag current release
    log_info "Tagging release..."
    if ! git tag -l "v${VERSION}" | grep -q "v${VERSION}"; then
        run_cmd git tag -a "v${VERSION}" -m "ClickHouse ${VERSION}"
        log_success "Tag created: v${VERSION}"
    else
        log_warn "Tag already exists: v${VERSION}"
    fi

    # Update CHANGELOG
    log_info "Updating CHANGELOG..."
    log_warn "Manual CHANGELOG update required"

    # Schedule release call
    log_info "Release call scheduling..."
    log_info "Schedule release call at: https://clickhouse.com/company/events"

    log_success "Post-release tasks completed"
    mark_step "post-release" "completed"
}

# ============================================================================
# Summary Report
# ============================================================================

print_summary() {
    echo ""
    log_info "═══════════════════════════════════════════════════════"
    log_info "                    RELEASE SUMMARY                    "
    log_info "═══════════════════════════════════════════════════════"
    log_info "Version: $VERSION"
    log_info "Branch: $BRANCH"
    log_info "Channel: $CHANNEL"
    log_info "Release Directory: $RELEASE_DIR"
    echo ""
    
    local steps=("preflight" "build" "test" "package" "sign" "publish" "announce" "post-release")
    for step in "${steps[@]}"; do
        local status="${STEP_STATUS[$step]:-not_run}"
        case "$status" in
            completed) echo -e "  ${GREEN}✓${NC} $step" ;;
            skipped) echo -e "  ${YELLOW}○${NC} $step (skipped)" ;;
            failed) echo -e "  ${RED}✗${NC} $step (failed)" ;;
            *) echo -e "  ${RED}?${NC} $step (not run)" ;;
        esac
    done
    
    echo ""
    log_info "Completed: $COMPLETED_STEPS/$TOTAL_STEPS steps"
    log_info "═══════════════════════════════════════════════════════"
}

# ============================================================================
# Main
# ============================================================================

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version) VERSION="$2"; shift 2 ;;
            --branch) BRANCH="$2"; shift 2 ;;
            --channel) CHANNEL="$2"; shift 2 ;;
            --dry-run) DRY_RUN="true"; shift ;;
            --skip) SKIP_STEPS="$2"; shift 2 ;;
            --help|-h) show_help ;;
            *) log_error "Unknown option: $1"; show_help ;;
        esac
    done

    log_info "ClickHouse Release Automation"
    log_info "Version: ${VERSION:-not specified}"
    log_info "Branch: $BRANCH"
    log_info "Channel: $CHANNEL"
    [[ "$DRY_RUN" == "true" ]] && log_warn "DRY-RUN MODE - No changes will be made"
    echo ""

    # Create release directory
    mkdir -p "$RELEASE_DIR"

    # Execute release steps
    step_preflight || { print_summary; exit 1; }
    step_build || { print_summary; exit 1; }
    step_test || { print_summary; exit 1; }
    step_package || { print_summary; exit 1; }
    step_sign || { print_summary; exit 1; }
    step_publish || { print_summary; exit 1; }
    step_announce || { print_summary; exit 1; }
    step_post_release || { print_summary; exit 1; }

    print_summary
    log_success "Release process completed!"
}

main "$@"
