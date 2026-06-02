#include <Interpreters/SlowQueryMonitor.h>
#include <DataTypes/DataTypeDate.h>
#include <DataTypes/DataTypeDateTime.h>
#include <DataTypes/DataTypeString.h>
#include <DataTypes/DataTypesNumber.h>
#include <Interpreters/Context.h>
#include <Common/DateLUT.h>

namespace DB
{

ColumnsDescription SlowQueryLogElement::getColumnsDescription()
{
    return ColumnsDescription
    {
        {"query", std::make_shared<DataTypeString>(), "Query string."},
        {"query_duration_ms", std::make_shared<DataTypeUInt64>(), "Query execution time in milliseconds."},
        {"memory_usage", std::make_shared<DataTypeUInt64>(), "Memory usage in bytes."},
        {"read_rows", std::make_shared<DataTypeUInt64>(), "Number of read rows."},
        {"event_date", std::make_shared<DataTypeDate>(), "Date of the event."},
        {"event_time", std::make_shared<DataTypeDateTime>(), "Time of the event."},
        {"client_name", std::make_shared<DataTypeString>(), "Client name."},
        {"current_database", std::make_shared<DataTypeString>(), "Current database."},
        {"query_id", std::make_shared<DataTypeString>(), "Query ID."}
    };
}

void SlowQueryLogElement::appendToBlock(MutableColumns & columns) const
{
    size_t i = 0;
    columns[i++]->insert(query);
    columns[i++]->insert(query_duration_ms);
    columns[i++]->insert(memory_usage);
    columns[i++]->insert(read_rows);
    columns[i++]->insert(DateLUT::instance().toDayNum(event_time).toUnderType());
    columns[i++]->insert(event_time);
    columns[i++]->insert(client_name);
    columns[i++]->insert(current_database);
    columns[i++]->insert(query_id);
}

void SlowQueryMonitor::checkAndRecord(const String & query, ContextPtr context, const QueryStatusInfo & info, UInt64 duration_ms, const QueryLogElement & elem)
{
    auto slow_log = context->getSystemLogs().slow_log;
    if (!slow_log)
        return;

    SlowQueryLogElement slow_elem;
    slow_elem.query = query;
    slow_elem.query_duration_ms = duration_ms;
    slow_elem.memory_usage = info.peak_memory_usage > 0 ? info.peak_memory_usage : 0;
    slow_elem.read_rows = info.read_rows;
    slow_elem.event_time = elem.event_time;
    slow_elem.client_name = elem.client_info.client_name;
    slow_elem.current_database = elem.current_database;
    slow_elem.query_id = elem.client_info.current_query_id;

    slow_log->add(slow_elem);
}

}