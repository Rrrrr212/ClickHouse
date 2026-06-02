#pragma once

#include <Interpreters/Context_fwd.h>
#include <Interpreters/QueryLogElement.h>
#include <Interpreters/SystemLog.h>

namespace DB
{

struct SlowQueryLogElement
{
    time_t event_time{};
    Decimal64 event_time_microseconds{};
    time_t query_start_time{};
    Decimal64 query_start_time_microseconds{};
    UInt64 query_duration_ms{};
    UInt64 read_rows{};
    UInt64 read_bytes{};
    UInt64 memory_usage{};
    String current_database;
    String query;
    UInt64 normalized_query_hash{};
    String user;
    String query_id;
    String initial_query_id;
    Int32 exception_code{};
    String exception;
    bool is_initial_query{};
    bool is_internal{};

    static std::string name() { return "SlowQueryLog"; }
    static ColumnsDescription getColumnsDescription();
    static NamesAndAliases getNamesAndAliases() { return {}; }
    void appendToBlock(MutableColumns & columns) const;
};

class SlowQueryLog : public SystemLog<SlowQueryLogElement>
{
public:
    using SystemLog<SlowQueryLogElement>::SystemLog;

    static const char * getDefaultOrderBy() { return "event_date, event_time, query_duration_ms"; }
    static constexpr auto DESCRIPTION = R"(Contains queries whose execution time exceeded `slow_query_time_threshold_ms`.)";
};

class SlowQueryMonitor
{
public:
    static void logIfNeeded(ContextPtr context, const QueryLogElement & query_log_element);
};

}
