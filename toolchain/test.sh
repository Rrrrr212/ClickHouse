#!/usr/bin/env bash
#
# ClickHouse Test Runner Toolchain
# ==================================
# Unified test execution script for running different test suites.
#
# Usage:
#   ./test.sh [OPTIONS] [TEST_SELECTOR]
#
# Options:
#   --suite <stateless|stateful|integration|unit|functional>  Test suite (default: stateless)
#   --test <PATTERN>                                          Test name pattern
#   --parallel <N>                                            Parallel workers (default: auto)
#   --timeout <SECONDS>                                       Test timeout (default: 300)
#   --keep-going                                              Continue on failure
#   --verbose                                                 Verbose output
#   --help                                                    Show this help message
#
# Examples:
#   ./test.sh                                                 # Run all stateless tests
#   ./test.sh --test 00001                                   # Run specific test
#   ./test.sh --suite integration --test keeper              # Run keeper integration tests
#   ./test.sh --suite unit --parallel 8                      # Run unit tests with 8 workers

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
SUITE="${SUITE:-stateless}"
TEST_PATTERN="${TEST_PATTERN:-}"
PARALLEL="${PARALLEL:-auto}"
TIMEOUT="${TIMEOUT:-300}"
KEEP_GOING="${KEEP_GOING:-false}"
VERBOSE="${VERBOSE:-false}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log_info() { echo -e "${BLUE}[TEST]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" >&2; }

show_help() {
    head -20 "$0" | tail -18 | sed 's/^# \?//'
    exit 0
}

run_stateless_tests() {
    local test_dir="${PROJECT_ROOT}/tests/queries/0_stateless"
    local log_file="${PROJECT_ROOT}/tmp/test_stateless_$(date +%Y%m%d_%H%M%S).log"
    
    mkdir -p "${PROJECT_ROOT}/tmp"
    
    log_info "Running stateless tests..."
    [[ -n "$TEST_PATTERN" ]] && log_info "Pattern: $TEST_PATTERN"
    
    local cmd=(
        python3 "${PROJECT_ROOT}/tests/runner.py"
        --test-dir "$test_dir"
        --timeout "$TIMEOUT"
    )
    
    [[ "$PARALLEL" != "auto" ]] && cmd+=(--parallel "$PARALLEL")
    [[ "$KEEP_GOING" == "true" ]] && cmd+=(--keep-going)
    [[ "$VERBOSE" == "true" ]] && cmd+=(--verbose)
    [[ -n "$TEST_PATTERN" ]] && cmd+=(--test "$TEST_PATTERN")
    
    "${cmd[@]}" 2>&1 | tee "$log_file"
    
    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -eq 0 ]]; then
        log_success "All stateless tests passed"
    else
        log_error "Some stateless tests failed. Log: $log_file"
    fi
    
    return $exit_code
}

run_integration_tests() {
    local test_dir="${PROJECT_ROOT}/tests/integration"
    local log_file="${PROJECT_ROOT}/tmp/test_integration_$(date +%Y%m%d_%H%M%S).log"
    
    mkdir -p "${PROJECT_ROOT}/tmp"
    
    log_info "Running integration tests..."
    [[ -n "$TEST_PATTERN" ]] && log_info "Pattern: $TEST_PATTERN"
    
    local cmd=(
        python3 -m ci.praktika run "integration"
        --test-dir "$test_dir"
        --timeout "$TIMEOUT"
    )
    
    [[ -n "$TEST_PATTERN" ]] && cmd+=(--test "$TEST_PATTERN")
    [[ "$VERBOSE" == "true" ]] && cmd+=(--verbose)
    
    "${cmd[@]}" 2>&1 | tee "$log_file"
    
    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -eq 0 ]]; then
        log_success "All integration tests passed"
    else
        log_error "Some integration tests failed. Log: $log_file"
    fi
    
    return $exit_code
}

run_unit_tests() {
    local build_dir="${PROJECT_ROOT}/build_release"
    local log_file="${PROJECT_ROOT}/tmp/test_unit_$(date +%Y%m%d_%H%M%S).log"
    
    mkdir -p "${PROJECT_ROOT}/tmp"
    
    log_info "Running unit tests..."
    
    if [[ ! -d "$build_dir" ]]; then
        log_error "Build directory not found: $build_dir"
        log_info "Run './toolchain/build.sh' first"
        return 1
    fi
    
    local cmd=(
        "${build_dir}/programs/clickhouse-test"
        --test-dir "${PROJECT_ROOT}/tests/queries/0_stateless"
    )
    
    [[ "$PARALLEL" != "auto" ]] && cmd+=(--jobs "$PARALLEL")
    [[ -n "$TEST_PATTERN" ]] && cmd+=(--test "$TEST_PATTERN")
    
    "${cmd[@]}" 2>&1 | tee "$log_file"
    
    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -eq 0 ]]; then
        log_success "All unit tests passed"
    else
        log_error "Some unit tests failed. Log: $log_file"
    fi
    
    return $exit_code
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --suite) SUITE="$2"; shift 2 ;;
            --test) TEST_PATTERN="$2"; shift 2 ;;
            --parallel) PARALLEL="$2"; shift 2 ;;
            --timeout) TIMEOUT="$2"; shift 2 ;;
            --keep-going) KEEP_GOING="true"; shift ;;
            --verbose) VERBOSE="true"; shift ;;
            --help|-h) show_help ;;
            *) log_error "Unknown option: $1"; show_help ;;
        esac
    done
    
    log_info "Test Configuration:"
    log_info "  Suite: $SUITE"
    log_info "  Pattern: ${TEST_PATTERN:-all}"
    log_info "  Parallel: $PARALLEL"
    log_info "  Timeout: $TIMEOUT"
    echo ""
    
    case "$SUITE" in
        stateless) run_stateless_tests ;;
        integration) run_integration_tests ;;
        unit) run_unit_tests ;;
        *) log_error "Unknown test suite: $SUITE"; exit 1 ;;
    esac
}

main "$@"
