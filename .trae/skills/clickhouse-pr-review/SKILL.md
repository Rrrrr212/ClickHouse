---
name: "clickhouse-pr-review"
description: "Reviews ClickHouse PRs to identify module, analyze performance-sensitive code, detect common errors, and provide fixes in Markdown table format. Invoke when reviewing ClickHouse PRs or analyzing code changes."
---

# ClickHouse PR Review

## 功能说明

本技能用于审查 ClickHouse 项目的 PR，自动识别修改文件所属模块，对性能敏感代码进行分析，检测常见错误并提供修复建议。

## 使用场景

- 审查 ClickHouse 项目的 PR
- 分析代码变更的潜在风险
- 优化性能关键路径的代码
- 检测常见的 C++ 错误

## 审查要点

### 1. 模块识别

根据文件路径自动识别所属模块：
- **Parser**: `src/Parsers/`
- **Storage**: `src/Storages/`
- **Functions**: `src/Functions/`
- **Aggregations**: `src/AggregateFunctions/`
- **DataTypes**: `src/DataTypes/`
- **Interpreters**: `src/Interpreters/`
- **Processors**: `src/Processors/`
- **IO**: `src/IO/`
- **Core**: `src/Core/`
- **Common**: `src/Common/`
- **Columns**: `src/Columns/`
- **Compression**: `src/Compression/`

### 2. 性能敏感代码分析

重点关注：
- 循环优化
- 内存分配
- 序列化
- 避免不必要的拷贝
- SIMD 优化

### 3. 常见错误检测

- 整数溢出
- 用后释放（UAF）
- 迭代器失效
- 空指针访问
- 异常安全

### 4. ClickHouse 代码规范

- 使用 Allman 风格大括号
- 避免使用 sleep 解决竞态条件
- 优先使用 fail-close 原则
- 使用 ClickHouse 提供的内存跟踪工具
- 遵循 ClickHouse 的异常处理规范

## 输出格式

审查结果以 Markdown 表格形式输出：

| 风险等级 | 文件位置 | 问题描述 | 修复建议 | 新代码 |
|---------|---------|---------|---------|-------|
| 高/中/低 | 文件路径 | 问题详细描述 | 修复建议 | 修复后的代码片段 |

## 使用示例

```
技能会自动分析 PR 中的代码变更，识别模块，检测问题并提供修复建议。
```
