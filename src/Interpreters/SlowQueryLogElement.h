#pragma once

#include <Core/QueryLogElementType.h>
#include <Interpreters/ClientInfo.h>
#include <Storages/ColumnsDescription.h>
#include <Common/ProfileEvents.h>

namespace DB
{

struct SlowQueryLogElement
{
    using Type = QueryLogElementType;

    Type type = QUERY_FINISH;

    time_t event_time{};
    Decimal64 event_time_microseconds{};
    time_t query_start_time{};
    Decimal64 query_start_time_microseconds{};
    UInt64 query_duration_ms{};

    UInt64 read_rows{};
    UInt64 read_bytes{};
    UInt64 result_rows{};
    UInt64 result_bytes{};
    UInt64 memory_usage{};

    String current_database;
    String query;
    UInt64 normalized_query_hash{};

    Int32 exception_code{};
    String exception;
    String stack_trace;

    ClientInfo client_info;

    String log_comment;

    static std::string name() { return "SlowQueryLog"; }

    static ColumnsDescription getColumnsDescription();
    static NamesAndAliases getNamesAndAliases();
    void appendToBlock(MutableColumns & columns) const;
};

}
