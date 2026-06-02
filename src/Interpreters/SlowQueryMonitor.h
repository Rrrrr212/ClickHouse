#pragma once

#include <Columns/IColumn_fwd.h>
#include <Interpreters/ClientInfo.h>
#include <Storages/ColumnsDescription.h>
#include <Core/NamesAndAliases.h>

namespace DB
{

/// A struct which will be inserted as row into slow_log table
struct SlowQueryLogElement
{
    time_t event_time{};
    Decimal64 event_time_microseconds{};
    time_t query_start_time{};
    Decimal64 query_start_time_microseconds{};
    UInt64 query_duration_ms{};

    /// The data fetched from DB to execute the query
    UInt64 read_rows{};
    UInt64 read_bytes{};

    /// The data written to DB
    UInt64 written_rows{};
    UInt64 written_bytes{};

    /// The data sent to the client
    UInt64 result_rows{};
    UInt64 result_bytes{};

    UInt64 memory_usage{};

    String current_database;
    String query;
    String query_id;

    ClientInfo client_info;

    String log_comment;

    static std::string name() { return "SlowQueryLog"; }

    static ColumnsDescription getColumnsDescription();
    static NamesAndAliases getNamesAndAliases();
    void appendToBlock(MutableColumns & columns) const;

    static void appendClientInfo(const ClientInfo & client_info, MutableColumns & columns, size_t & i);
};

class SlowQueryMonitor
{
public:
    /// Logs a slow query if it meets the criteria
    static void logSlowQuery(
        const SlowQueryLogElement & element,
        ContextPtr context);
};

}
