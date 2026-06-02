#include <Interpreters/SlowQueryMonitor.h>

#include <Columns/ColumnLowCardinality.h>
#include <Columns/ColumnString.h>
#include <Columns/ColumnsDateTime.h>
#include <Columns/ColumnsNumber.h>
#include <Core/Settings.h>
#include <Interpreters/Context.h>
#include <DataTypes/DataTypeDate.h>
#include <DataTypes/DataTypeDateTime.h>
#include <DataTypes/DataTypeDateTime64.h>
#include <DataTypes/DataTypeLowCardinality.h>
#include <DataTypes/DataTypeString.h>
#include <DataTypes/DataTypesNumber.h>
#include <Common/DateLUTImpl.h>
#include <Common/typeid_cast.h>
#include <base/getFQDNOrHostName.h>

namespace DB
{

namespace Setting
{
    extern const SettingsBool slow_query_log_enable;
    extern const SettingsMilliseconds slow_query_time_threshold_ms;
}

ColumnsDescription SlowQueryLogElement::getColumnsDescription()
{
    auto low_cardinality_string = std::make_shared<DataTypeLowCardinality>(std::make_shared<DataTypeString>());

    return ColumnsDescription
    {
        {"hostname", low_cardinality_string, "Hostname of the server executing the query."},
        {"event_date", std::make_shared<DataTypeDate>(), "Query finish date."},
        {"event_time", std::make_shared<DataTypeDateTime>(), "Query finish time."},
        {"event_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Query finish time with microseconds precision."},
        {"query_start_time", std::make_shared<DataTypeDateTime>(), "Start time of query execution."},
        {"query_start_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Start time of query execution with microseconds precision."},
        {"query_duration_ms", std::make_shared<DataTypeUInt64>(), "Duration of query execution in milliseconds."},
        {"read_rows", std::make_shared<DataTypeUInt64>(), "Total number of rows read during query execution."},
        {"read_bytes", std::make_shared<DataTypeUInt64>(), "Total number of bytes read during query execution."},
        {"memory_usage", std::make_shared<DataTypeUInt64>(), "Peak memory consumption by the query."},
        {"current_database", low_cardinality_string, "Name of the current database."},
        {"query", std::make_shared<DataTypeString>(), "Query string."},
        {"normalized_query_hash", std::make_shared<DataTypeUInt64>(), "Normalized query hash."},
        {"user", low_cardinality_string, "Name of the user who initiated the query."},
        {"query_id", std::make_shared<DataTypeString>(), "ID of the query."},
        {"initial_query_id", std::make_shared<DataTypeString>(), "ID of the initial query."},
        {"exception_code", std::make_shared<DataTypeInt32>(), "Code of an exception if query finished with an exception."},
        {"exception", std::make_shared<DataTypeString>(), "Exception message if query finished with an exception."},
        {"is_initial_query", std::make_shared<DataTypeUInt8>(), "Indicates whether the query was initiated by the client."},
        {"is_internal", std::make_shared<DataTypeUInt8>(), "Indicates whether it is an auxiliary query executed internally."},
    };
}

void SlowQueryLogElement::appendToBlock(MutableColumns & columns) const
{
    size_t i = 0;

    const auto & hostname = getFQDNOrHostName();
    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(hostname.data(), hostname.size());
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(static_cast<UInt16>(DateLUT::instance().toDayNum(event_time).toUnderType()));
    typeid_cast<ColumnUInt32 &>(*columns[i++]).getData().push_back(static_cast<UInt32>(event_time));
    typeid_cast<ColumnDateTime64 &>(*columns[i++]).getData().push_back(event_time_microseconds);
    typeid_cast<ColumnUInt32 &>(*columns[i++]).getData().push_back(static_cast<UInt32>(query_start_time));
    typeid_cast<ColumnDateTime64 &>(*columns[i++]).getData().push_back(query_start_time_microseconds);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(query_duration_ms);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(read_rows);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(read_bytes);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(memory_usage);
    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(current_database.data(), current_database.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(query.data(), query.size());
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(normalized_query_hash);
    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(user.data(), user.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(query_id.data(), query_id.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(initial_query_id.data(), initial_query_id.size());
    typeid_cast<ColumnInt32 &>(*columns[i++]).getData().push_back(exception_code);
    typeid_cast<ColumnString &>(*columns[i++]).insertData(exception.data(), exception.size());
    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(is_initial_query);
    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(is_internal);
}

void SlowQueryMonitor::logIfNeeded(ContextPtr context, const QueryLogElement & query_log_element)
{
    if (!context)
        return;

    if (query_log_element.type != QueryLogElementType::QUERY_FINISH
        && query_log_element.type != QueryLogElementType::EXCEPTION_WHILE_PROCESSING)
        return;

    const Settings & settings = context->getSettingsRef();
    if (!settings[Setting::slow_query_log_enable])
        return;

    const auto threshold_ms = settings[Setting::slow_query_time_threshold_ms].totalMilliseconds();
    if (static_cast<Int64>(query_log_element.query_duration_ms) < threshold_ms)
        return;

    auto slow_query_log = context->getSlowQueryLog();
    if (!slow_query_log)
        return;

    SlowQueryLogElement elem;
    elem.event_time = query_log_element.event_time;
    elem.event_time_microseconds = query_log_element.event_time_microseconds;
    elem.query_start_time = query_log_element.query_start_time;
    elem.query_start_time_microseconds = query_log_element.query_start_time_microseconds;
    elem.query_duration_ms = query_log_element.query_duration_ms;
    elem.read_rows = query_log_element.read_rows;
    elem.read_bytes = query_log_element.read_bytes;
    elem.memory_usage = query_log_element.memory_usage;
    elem.current_database = query_log_element.current_database;
    elem.query = query_log_element.query;
    elem.normalized_query_hash = query_log_element.normalized_query_hash;
    elem.user = query_log_element.client_info.current_user;
    elem.query_id = query_log_element.client_info.current_query_id;
    elem.initial_query_id = query_log_element.client_info.initial_query_id;
    elem.exception_code = query_log_element.exception_code;
    elem.exception = query_log_element.exception;
    elem.is_initial_query = query_log_element.client_info.query_kind == ClientInfo::QueryKind::INITIAL_QUERY;
    elem.is_internal = query_log_element.is_internal;

    slow_query_log->add(elem);
}

}
