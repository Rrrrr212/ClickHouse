#!/usr/bin/env bash
#
# ClickHouse Build Toolchain
# ===========================
# Unified build script for ClickHouse with support for multiple build types
# and configurations.
#
# Usage:
#   ./build.sh [OPTIONS]
#
# Options:
#   --type <debug|release|asan|tsan|msan|coverage>  Build type (default: release)
#   --clean                                         Clean build directory first
#   --jobs <N>                                      Parallel jobs (default: auto)
#   --ninja-args <ARGS>                             Additional ninja arguments
#   --help                                          Show this help message

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly BUILD_TYPE="${BUILD_TYPE:-release}"
readonly BUILD_DIR="${PROJECT_ROOT}/build_${BUILD_TYPE}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log_info() { echo -e "${BLUE}[BUILD]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

show_help() {
    head -15 "$0" | tail -13 | sed 's/^# \?//'
    exit 0
}

configure_build() {
    local build_type="$1"
    log_info "Configuring build type: $build_type"
    
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    cmake "$PROJECT_ROOT" \
        -DCMAKE_BUILD_TYPE="$(echo "$build_type" | tr '[:lower:]' '[:upper:]')" \
        -DENABLE_TESTS=OFF \
        -DENABLE_UTILS=ON \
        "$@"
}

run_build() {
    log_info "Building ClickHouse..."
    ninja 2>&1 | tee "${BUILD_DIR}/build.log"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_success "Build completed successfully"
        log_info "Binaries are in: $BUILD_DIR/programs/"
    else
        log_error "Build failed. Check log: $BUILD_DIR/build.log"
        return 1
    fi
}

main() {
    local clean=false
    local jobs=""
    local ninja_args=""
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type) BUILD_TYPE="$2"; shift 2 ;;
            --clean) clean=true; shift ;;
            --jobs) jobs="-j $2"; shift 2 ;;
            --ninja-args) ninja_args="$2"; shift 2 ;;
            --help|-h) show_help ;;
            *) log_error "Unknown option: $1"; show_help ;;
        esac
    done
    
    if [[ "$clean" == "true" ]]; then
        log_info "Cleaning build directory: $BUILD_DIR"
        rm -rf "$BUILD_DIR"
    fi
    
    configure_build "$BUILD_TYPE"
    run_build
}

main "$@"
