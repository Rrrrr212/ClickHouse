#pragma once

#include <Interpreters/SystemLog.h>
#include <Core/NamesAndAliases.h>
#include <Storages/ColumnsDescription.h>
#include <Interpreters/Context_fwd.h>

namespace DB
{

struct SlowQueryLogElement
{
    enum class Type : UInt8
    {
        QUERY_FINISH = 1,
    };

    Type type = Type::QUERY_FINISH;
    time_t event_time{};
    Decimal64 event_time_microseconds{};
    String query;
    String query_id;
    UInt64 query_duration_ms{};
    UInt64 read_rows{};
    UInt64 read_bytes{};
    UInt64 memory_usage{};

    static std::string name() { return "SlowQueryLog"; }
    static ColumnsDescription getColumnsDescription();
    static NamesAndAliases getNamesAndAliases() { return {}; }
    void appendToBlock(MutableColumns & columns) const;
};

class SlowQueryLog : public SystemLog<SlowQueryLogElement>
{
    using SystemLog<SlowQueryLogElement>::SystemLog;
};

class SlowQueryMonitor
{
public:
    static void logSlowQueryIfNeeded(
        const ContextMutablePtr & context,
        const String & query,
        const String & query_id,
        UInt64 query_duration_ms,
        UInt64 read_rows,
        UInt64 read_bytes,
        UInt64 memory_usage);
};

}
