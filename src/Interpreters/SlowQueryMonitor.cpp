#include <Interpreters/SlowQueryMonitor.h>

#include <Columns/ColumnLowCardinality.h>
#include <Columns/ColumnString.h>
#include <Columns/ColumnsDateTime.h>
#include <Columns/ColumnsNumber.h>
#include <DataTypes/DataTypeDate.h>
#include <DataTypes/DataTypeDateTime.h>
#include <DataTypes/DataTypeDateTime64.h>
#include <DataTypes/DataTypeLowCardinality.h>
#include <DataTypes/DataTypeString.h>
#include <DataTypes/DataTypesNumber.h>
#include <DataTypes/DataTypeFactory.h>
#include <Common/IPv6ToBinary.h>
#include <base/getFQDNOrHostName.h>
#include <Common/ClickHouseRevision.h>
#include <Common/DateLUTImpl.h>
#include <Interpreters/Context.h>
#include <Interpreters/ProcessList.h>
#include <Core/Settings.h>
#include <Storages/IStorage.h>
#include <Access/ContextAccess.h>

namespace DB
{

ColumnsDescription SlowQueryLogElement::getColumnsDescription()
{
    auto low_cardinality_string = std::make_shared<DataTypeLowCardinality>(std::make_shared<DataTypeString>());

    return ColumnsDescription
    {
        {"hostname", low_cardinality_string, "Hostname of the server executing the query."},
        {"event_date", std::make_shared<DataTypeDate>(), "Event date."},
        {"event_time", std::make_shared<DataTypeDateTime>(), "Event time."},
        {"event_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Event time with microseconds precision."},
        {"query_start_time", std::make_shared<DataTypeDateTime>(), "Start time of query execution."},
        {"query_start_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Start time of query execution with microsecond precision."},
        {"query_duration_ms", std::make_shared<DataTypeUInt64>(), "Duration of query execution in milliseconds."},

        {"read_rows", std::make_shared<DataTypeUInt64>(), "Total number of rows read."},
        {"read_bytes", std::make_shared<DataTypeUInt64>(), "Total number of bytes read."},
        {"written_rows", std::make_shared<DataTypeUInt64>(), "Number of written rows."},
        {"written_bytes", std::make_shared<DataTypeUInt64>(), "Number of written bytes."},
        {"result_rows", std::make_shared<DataTypeUInt64>(), "Number of rows in query result."},
        {"result_bytes", std::make_shared<DataTypeUInt64>(), "Number of bytes in query result."},
        {"memory_usage", std::make_shared<DataTypeUInt64>(), "Memory consumption by the query."},

        {"current_database", low_cardinality_string, "Name of the current database."},
        {"query", std::make_shared<DataTypeString>(), "Query string."},
        {"query_id", std::make_shared<DataTypeString>(), "Query ID."},

        {"is_initial_query", std::make_shared<DataTypeUInt8>(), "Query type flag."},
        {"connection_address", DataTypeFactory::instance().get("IPv6"), "Connection address."},
        {"connection_port", std::make_shared<DataTypeUInt16>(), "Connection port."},
        {"user", low_cardinality_string, "User who ran the query."},
        {"address", DataTypeFactory::instance().get("IPv6"), "Address used for the query."},
        {"port", std::make_shared<DataTypeUInt16>(), "Port used for the query."},

        {"log_comment", std::make_shared<DataTypeString>(), "Log comment."},
    };
}

NamesAndAliases SlowQueryLogElement::getNamesAndAliases()
{
    return {};
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
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(written_rows);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(written_bytes);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(result_rows);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(result_bytes);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(memory_usage);

    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(current_database.data(), current_database.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(query.data(), query.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(query_id.data(), query_id.size());

    appendClientInfo(client_info, columns, i);

    typeid_cast<ColumnString &>(*columns[i++]).insertData(log_comment.data(), log_comment.size());
}

void SlowQueryLogElement::appendClientInfo(const ClientInfo & client_info, MutableColumns & columns, size_t & i)
{
    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(client_info.query_kind == ClientInfo::QueryKind::INITIAL_QUERY);

    typeid_cast<ColumnIPv6 &>(*columns[i++]).insertData(IPv6ToBinary(client_info.connection_address->host()).data(), 16);
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(client_info.connection_address->port());

    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(client_info.current_user.data(), client_info.current_user.size());
    typeid_cast<ColumnIPv6 &>(*columns[i++]).insertData(IPv6ToBinary(client_info.current_address->host()).data(), 16);
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(client_info.current_address->port());
}

void SlowQueryMonitor::logSlowQuery(
    const SlowQueryLogElement & element,
    ContextPtr context)
{
    try
    {
        if (!context->getSettingsRef().slow_query_log_enable)
            return;

        // Check if query duration exceeds threshold
        if (element.query_duration_ms < context->getSettingsRef().slow_query_time_threshold_ms)
            return;

        // TODO: Implement actual logging to system.slow_log
        // For now, this is a placeholder for the actual implementation
        // In a complete implementation, we would:
        // 1. Get the system.slow_log storage
        // 2. Insert the record into it
        // 3. Handle any errors
    }
    catch (...)
    {
        // Don't crash the query if logging fails
    }
}

}
