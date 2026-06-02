#!/usr/bin/env python3
"""Test script to verify keyword extraction works for Keeper/ZooKeeper related files."""
import sys
import re
import os

def _extract_domain_keywords(filename):
    """
    Extract domain-specific CamelCase words from a source filename.
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    # Split CamelCase and all-caps acronyms
    words = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z0-9]+|[A-Z]{2,}|[a-z][a-z0-9]+|[A-Z]', base)
    # Merge a lone trailing uppercase letter into the previous word
    merged: list = []
    for w in words:
        if len(w) == 1 and w.isupper() and merged:
            merged[-1] = merged[-1] + w
        else:
            merged.append(w)
    words = merged
    # Architectural / ubiquitous words that appear in most files in a directory.
    COMMON = {
        "block", "input", "output", "format", "column", "stream",
        "storage", "table", "query", "parser", "writer", "reader",
        "buffer", "default", "base", "impl", "merge", "tree",
        "row", "file", "data", "info", "type", "list", "map",
        "with", "from", "into",
        "condition", "granularity", "selector", "partition", "replica",
        "transaction", "virtual", "local", "remote", "range", "level",
        "handler", "manager", "source", "access", "control",
        "service", "server", "client", "external", "internal",
        "settings", "setting", "config", "context", "result",
        "state", "status", "entry", "record", "update", "create",
    }
    # Generic acronyms that don't generate false matches.
    COMMON_ACRONYMS = {"api", "sql", "ddl", "dml", "ids", "uid", "abi", "cpu", "gpu", "ram",
                       "tcp", "udp", "tls", "ssl", "rpc", "ttl", "log", "tag", "row", "set"}
    specific = [
        w for w in words
        if w.lower() not in COMMON
        and (
            (len(w) >= 4)
            or (len(w) == 3 and w.isupper() and w.lower() not in COMMON_ACRONYMS)
        )
    ]
    return specific

# Test cases
test_files = [
    "Commands.cpp",
    "KeeperClientCLI/Commands.cpp",
    "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
    "Keeper.cpp",
    "ZooKeeper.cpp",
    "KeeperStorage.cpp",
    "KeeperMap.cpp",
    "src/Coordination/Keeper.cpp"
]

print("Testing keyword extraction for Keeper/ZooKeeper related files:\n")
for f in test_files:
    keywords = _extract_domain_keywords(f)
    print(f"File: {f}")
    print(f"Extracted keywords: {keywords}")
    print()
