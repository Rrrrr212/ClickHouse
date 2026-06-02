#include <Interpreters/SlowQueryMonitor.h>
#include <DataTypes/DataTypeDateTime.h>
#include <DataTypes/DataTypeDateTime64.h>
#include <DataTypes/DataTypeString.h>
#include <DataTypes/DataTypesNumber.h>
#include <Interpreters/Context.h>
#include <Core/Settings.h>

namespace DB
{
namespace Setting
{
    extern const SettingsBool slow_query_log_enable;
    extern const SettingsMilliseconds slow_query_time_threshold_ms;
}

ColumnsDescription SlowQueryLogElement::getColumnsDescription()
{
    return ColumnsDescription
    {
        {"type", std::make_shared<DataTypeUInt8>(), "Event type."},
        {"event_time", std::make_shared<DataTypeDateTime>(), "Query finishing time."},
        {"event_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Query finishing time with microseconds precision."},
        {"query", std::make_shared<DataTypeString>(), "Query string."},
        {"query_id", std::make_shared<DataTypeString>(), "ID of the query."},
        {"query_duration_ms", std::make_shared<DataTypeUInt64>(), "Duration of query execution in milliseconds."},
        {"read_rows", std::make_shared<DataTypeUInt64>(), "Total number of rows read."},
        {"read_bytes", std::make_shared<DataTypeUInt64>(), "Total number of bytes read."},
        {"memory_usage", std::make_shared<DataTypeUInt64>(), "Memory consumption by the query."}
    };
}

void SlowQueryLogElement::appendToBlock(MutableColumns & columns) const
{
    size_t i = 0;
    columns[i++]->insert(static_cast<UInt8>(type));
    columns[i++]->insert(event_time);
    columns[i++]->insert(event_time_microseconds);
    columns[i++]->insertData(query.data(), query.size());
    columns[i++]->insertData(query_id.data(), query_id.size());
    columns[i++]->insert(query_duration_ms);
    columns[i++]->insert(read_rows);
    columns[i++]->insert(read_bytes);
    columns[i++]->insert(memory_usage);
}

void SlowQueryMonitor::logSlowQueryIfNeeded(
    const ContextMutablePtr & context,
    const String & query,
    const String & query_id,
    UInt64 query_duration_ms,
    UInt64 read_rows,
    UInt64 read_bytes,
    UInt64 memory_usage)
{
    if (!context->getSettingsRef()[Setting::slow_query_log_enable])
        return;

    UInt64 threshold = context->getSettingsRef()[Setting::slow_query_time_threshold_ms].totalMilliseconds();
    if (query_duration_ms < threshold)
        return;

    auto system_logs = context->getSystemLogs();
    if (!system_logs.slow_log)
        return;

    SlowQueryLogElement elem;
    auto now = std::chrono::system_clock::now();
    elem.event_time = std::chrono::system_clock::to_time_t(now);
    elem.event_time_microseconds = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
    elem.query = query;
    elem.query_id = query_id;
    elem.query_duration_ms = query_duration_ms;
    elem.read_rows = read_rows;
    elem.read_bytes = read_bytes;
    elem.memory_usage = memory_usage;

    system_logs.slow_log->add(elem);
}

}
