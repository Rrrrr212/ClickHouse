---
name: "clickhouse-pr-review"
description: "Reviews ClickHouse PRs with module detection, performance analysis, and bug detection. Invoke when user asks to review a PR, analyze code changes, or review ClickHouse code."
---

# ClickHouse PR Review Skill

This skill provides comprehensive code review for ClickHouse pull requests, automatically detecting modules, analyzing performance-sensitive code, and detecting common bugs.

## Module Detection

When reviewing changes, first identify which ClickHouse module the modified files belong to:

| Module | Directory Pattern | Description |
|--------|------------------|-------------|
| **Parser** | `src/Parsers/` | SQL parsing, AST nodes, query syntax |
| **Storage** | `src/Storages/` | Table engines (MergeTree, Log, etc.), data storage |
| **Functions** | `src/Functions/` | SQL functions (math, string, date, etc.) |
| **Aggregations** | `src/AggregateFunctions/` | Aggregate functions (sum, avg, groupBy, etc.) |
| **Interpreter** | `src/Interpreters/` | Query execution, context, expression evaluation |
| **Analyzer** | `src/Analyzer/` | Query analysis, resolution, validation |
| **Planner** | `src/Planner/` | Query planning, optimization |
| **Processors** | `src/Processors/` | Query pipeline processors, transforms |
| **QueryPipeline** | `src/QueryPipeline/` | Pipeline construction and execution |
| **Columns** | `src/Columns/` | Column implementations (IColumn, etc.) |
| **DataTypes** | `src/DataTypes/` | Type system (IDataType, serialization) |
| **IO** | `src/IO/` | ReadBuffer/WriteBuffer, serialization |
| **Formats** | `src/Formatters/` | Input/output formats (JSON, CSV, etc.) |
| **Compression** | `src/Compression/` | Compression codecs (LZ4, ZSTD, etc.) |
| **Disks** | `src/Disks/` | Disk abstraction, object storage |
| **Dictionaries** | `src/Dictionaries/` | Dictionary structures |
| **TableFunctions** | `src/TableFunctions/` | Table functions (numbers, merge, etc.) |
| **Access** | `src/Access/` | Authentication, authorization |
| **Backups** | `src/Backups/` | Backup/restore functionality |
| **Coordination** | `src/Coordination/` | ZooKeeper/Keeper integration |
| **Core** | `src/Core/` | Core types (Field, Block, etc.) |
| **Common** | `src/Common/` | Utilities, threading, memory, logging |
| **Client** | `src/Client/` | CLI client, connection handling |
| **Server** | `src/Server/` | HTTP/TCP servers |

## Performance-Sensitive Code Analysis

When reviewing code, pay special attention to these performance-critical patterns:

### 1. Hot Loops
- Look for loops in `Processors`, `Functions`, `AggregateFunctions`
- Check for unnecessary allocations inside loops
- Verify vectorization opportunities (prefer SIMD where possible)
- Watch for hidden O(n²) complexity

### 2. Memory Allocation
- Avoid `std::make_shared`, `new` in hot paths - prefer arena allocation
- Check for unnecessary copies of `String`, `Column`, `Block`
- Prefer `reserve()` before filling containers
- Watch for `std::vector` reallocations in tight loops
- Use `PODArray` instead of `std::vector` for numeric data

### 3. Serialization
- Review `ReadBuffer`/`WriteBuffer` usage patterns
- Check for proper endianness handling
- Verify compression is applied where appropriate
- Watch for unnecessary string conversions

### 4. String Operations
- Prefer `StringRef` over `std::string` for read-only access
- Use `fmt::format` or `WriteBuffer` instead of string concatenation
- Check for unnecessary `c_str()` calls

### 5. Virtual Dispatch
- Hot paths should avoid virtual calls when possible
- Consider `std::variant` or templates over inheritance
- Check for `dynamic_cast` in performance-critical code

## Common Bug Detection

### 1. Integer Overflow
```cpp
// BAD: Potential overflow
size_t total = count * element_size;

// GOOD: Check before multiplication
if (count > std::numeric_limits<size_t>::max() / element_size)
    throw Exception(...);
```

### 2. Use-After-Free (UAF)
- Watch for references/pointers to temporary objects
- Check lifetime of `StringRef` pointing to temporary strings
- Verify iterators aren't used after container modification
- Watch for dangling references after `std::move`

### 3. Iterator Invalidation
```cpp
// BAD: Iterator invalidated by erase
for (auto it = vec.begin(); it != vec.end(); ++it)
    if (condition(*it))
        vec.erase(it);

// GOOD: Use erase-remove idiom or proper iteration
vec.erase(std::remove_if(vec.begin(), vec.end(), condition), vec.end());
```

### 4. Thread Safety
- Check for unprotected shared state
- Verify proper use of `std::atomic` for counters
- Watch for data races in concurrent data structures
- Check mutex lock ordering

### 5. Resource Leaks
- Verify RAII patterns for file handles, locks
- Check for proper cleanup in exception paths
- Watch for unclosed `ReadBuffer`/`WriteBuffer`

## ClickHouse Code Standards References

When detecting issues, reference these ClickHouse-specific conventions:

1. **Allman brace style** - Opening braces on new lines
2. **No `sleep()` in C++** - Never use sleep to fix race conditions
3. **Fail-close principle** - Prefer propagating errors over fallbacks
4. **No "no-*" tags** - Don't add test tags like "no-parallel" unless necessary
5. **Function naming** - Refer to functions as `f` not `f()` in comments
6. **Exception terminology** - Say "exception" not "crash" for logical errors
7. **Security** - Never expose or log secrets/keys

## Output Format

Always format review results as a Markdown table:

```markdown
## Code Review Results

| Risk Level | File Location | Issue Description | Fix Suggestion |
|------------|--------------|-------------------|----------------|
| 🔴 Critical | `src/Functions/function.cpp:L123` | Integer overflow in size calculation | Add overflow check before multiplication |
| 🟡 Warning | `src/Storages/storage.cpp:L456` | Unnecessary copy in hot loop | Use StringRef instead of std::string |
| 🟢 Info | `src/Processors/transform.cpp:L789` | Could use reserve() for vector | Add vec.reserve(estimated_size) |
```

### Risk Levels
- **🔴 Critical**: Security vulnerabilities, crashes, data corruption, UAF
- **🟡 Warning**: Performance issues, memory leaks, potential bugs
- **🟢 Info**: Style improvements, optimization opportunities, best practices

## Review Process

1. **Identify changed files** - Use git diff or file list
2. **Detect modules** - Map each file to its ClickHouse module
3. **Analyze patterns** - Check for performance-sensitive code
4. **Detect bugs** - Look for common error patterns
5. **Generate report** - Output formatted Markdown table
6. **Suggest fixes** - Provide concrete code examples when possible

## Example Usage

When reviewing a PR:

1. First, identify the modules affected
2. For each module, apply relevant checks:
   - **Functions**: Check vectorization, null handling
   - **Storage**: Check concurrency, memory usage
   - **Aggregations**: Check state serialization, thread safety
   - **Parser**: Check AST validation, error messages
3. Generate the review table with all findings
4. Provide code snippets for critical issues
