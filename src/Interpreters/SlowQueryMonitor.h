#pragma once

#include <Interpreters/SystemLog.h>
#include <Core/NamesAndTypes.h>
#include <Core/NamesAndAliases.h>
#include <Interpreters/QueryLogElement.h>
#include <Storages/ColumnsDescription.h>
#include <Interpreters/ProcessList.h>
#include <Columns/IColumn.h>

namespace DB
{

struct SlowQueryLogElement
{
    String query;
    UInt64 query_duration_ms = 0;
    UInt64 memory_usage = 0;
    UInt64 read_rows = 0;
    
    time_t event_time = 0;
    String client_name;
    String current_database;
    String query_id;

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
    static void checkAndRecord(const String & query, ContextPtr context, const QueryStatusInfo & info, UInt64 duration_ms, const QueryLogElement & elem);
};

}
