#include <Interpreters/SlowQueryLog.h>

#include <Columns/ColumnLowCardinality.h>
#include <Columns/ColumnString.h>
#include <Columns/ColumnsDateTime.h>
#include <Columns/ColumnsNumber.h>
#include <Core/QueryLogElementType.h>
#include <DataTypes/DataTypeDate.h>
#include <DataTypes/DataTypeDateTime.h>
#include <DataTypes/DataTypeDateTime64.h>
#include <DataTypes/DataTypeEnum.h>
#include <DataTypes/DataTypeFactory.h>
#include <DataTypes/DataTypeLowCardinality.h>
#include <DataTypes/DataTypeString.h>
#include <DataTypes/DataTypesNumber.h>
#include <Interpreters/QueryLogElement.h>
#include <base/getFQDNOrHostName.h>
#include <Common/DateLUTImpl.h>
#include <Common/IPv6ToBinary.h>

#include <Poco/Net/IPAddress.h>


namespace DB
{

ColumnsDescription SlowQueryLogElement::getColumnsDescription()
{
    auto query_status_datatype = std::make_shared<DataTypeEnum8>(
        DataTypeEnum8::Values
        {
            {"QueryFinish",                 static_cast<Int8>(QUERY_FINISH)},
            {"ExceptionBeforeStart",        static_cast<Int8>(EXCEPTION_BEFORE_START)},
            {"ExceptionWhileProcessing",    static_cast<Int8>(EXCEPTION_WHILE_PROCESSING)}
        });

    auto low_cardinality_string = std::make_shared<DataTypeLowCardinality>(std::make_shared<DataTypeString>());

    return ColumnsDescription
    {
        {"hostname", low_cardinality_string, "Hostname of the server executing the query."},
        {"type", std::move(query_status_datatype), "Type of the slow query event: `QueryFinish` or `ExceptionWhileProcessing`."},
        {"event_date", std::make_shared<DataTypeDate>(), "Event date."},
        {"event_time", std::make_shared<DataTypeDateTime>(), "Event time."},
        {"event_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Event time with microseconds precision."},
        {"query_start_time", std::make_shared<DataTypeDateTime>(), "Start time of query execution."},
        {"query_start_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Start time of query execution with microsecond precision."},
        {"query_duration_ms", std::make_shared<DataTypeUInt64>(), "Duration of query execution in milliseconds."},

        {"read_rows", std::make_shared<DataTypeUInt64>(), "Total number of rows read from all tables and table functions participated in query."},
        {"read_bytes", std::make_shared<DataTypeUInt64>(), "Total number of bytes read from all tables and table functions participated in query."},
        {"result_rows", std::make_shared<DataTypeUInt64>(), "Number of rows in the result of the query."},
        {"result_bytes", std::make_shared<DataTypeUInt64>(), "RAM volume in bytes used to store the query result."},
        {"memory_usage", std::make_shared<DataTypeUInt64>(), "Memory consumption by the query."},

        {"current_database", low_cardinality_string, "Name of the current database."},
        {"query", std::make_shared<DataTypeString>(), "Query string."},
        {"normalized_query_hash", std::make_shared<DataTypeUInt64>(), "A numeric hash value that is identical for queries that differ only by values of literals."},

        {"exception_code", std::make_shared<DataTypeInt32>(), "Code of an exception."},
        {"exception", std::make_shared<DataTypeString>(), "Exception message."},
        {"stack_trace", std::make_shared<DataTypeString>(), "Stack trace. An empty string if the query was completed successfully."},

        {"is_initial_query", std::make_shared<DataTypeUInt8>(), "Query type. 1 — query was initiated by the client, 0 — by another query for distributed query execution."},
        {"user", low_cardinality_string, "Name of the user who initiated the current query."},
        {"query_id", std::make_shared<DataTypeString>(), "ID of the query."},
        {"address", DataTypeFactory::instance().get("IPv6"), "IP address that was used to make the query."},
        {"port", std::make_shared<DataTypeUInt16>(), "The client port that was used to make the query."},
        {"initial_user", low_cardinality_string, "Name of the user who ran the initial query (for distributed query execution)."},
        {"initial_query_id", std::make_shared<DataTypeString>(), "ID of the initial query (for distributed query execution)."},
        {"initial_address", DataTypeFactory::instance().get("IPv6"), "IP address that the parent query was launched from."},
        {"initial_port", std::make_shared<DataTypeUInt16>(), "The client port that was used to make the parent query."},
        {"initial_query_start_time", std::make_shared<DataTypeDateTime>(), "Initial query starting time (for distributed query execution)."},
        {"initial_query_start_time_microseconds", std::make_shared<DataTypeDateTime64>(6), "Initial query starting time with microseconds precision (for distributed query execution)."},
        {"interface", std::make_shared<DataTypeUInt8>(), "Interface that the query was initiated from. 1 — TCP, 2 — HTTP."},
        {"is_secure", std::make_shared<DataTypeUInt8>(), "Whether a query was executed over a secure interface."},
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
    typeid_cast<ColumnInt8 &>(*columns[i++]).getData().push_back(type);
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(static_cast<UInt16>(DateLUT::instance().toDayNum(event_time).toUnderType()));
    typeid_cast<ColumnUInt32 &>(*columns[i++]).getData().push_back(static_cast<UInt32>(event_time));
    typeid_cast<ColumnDateTime64 &>(*columns[i++]).getData().push_back(event_time_microseconds);
    typeid_cast<ColumnUInt32 &>(*columns[i++]).getData().push_back(static_cast<UInt32>(query_start_time));
    typeid_cast<ColumnDateTime64 &>(*columns[i++]).getData().push_back(query_start_time_microseconds);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(query_duration_ms);

    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(read_rows);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(read_bytes);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(result_rows);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(result_bytes);
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(memory_usage);

    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(current_database.data(), current_database.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(query.data(), query.size());
    typeid_cast<ColumnUInt64 &>(*columns[i++]).getData().push_back(normalized_query_hash);

    typeid_cast<ColumnInt32 &>(*columns[i++]).getData().push_back(exception_code);
    typeid_cast<ColumnString &>(*columns[i++]).insertData(exception.data(), exception.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(stack_trace.data(), stack_trace.size());

    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(client_info.query_kind == ClientInfo::QueryKind::INITIAL_QUERY);
    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(client_info.current_user.data(), client_info.current_user.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(client_info.current_query_id.data(), client_info.current_query_id.size());
    typeid_cast<ColumnIPv6 &>(*columns[i++]).insertData(IPv6ToBinary(client_info.current_address->host()).data(), 16);
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(client_info.current_address->port());
    typeid_cast<ColumnLowCardinality &>(*columns[i++]).insertData(client_info.initial_user.data(), client_info.initial_user.size());
    typeid_cast<ColumnString &>(*columns[i++]).insertData(client_info.initial_query_id.data(), client_info.initial_query_id.size());
    typeid_cast<ColumnIPv6 &>(*columns[i++]).insertData(IPv6ToBinary(client_info.initial_address->host()).data(), 16);
    typeid_cast<ColumnUInt16 &>(*columns[i++]).getData().push_back(client_info.initial_address->port());
    typeid_cast<ColumnUInt32 &>(*columns[i++]).getData().push_back(static_cast<UInt32>(client_info.initial_query_start_time));
    typeid_cast<ColumnDateTime64 &>(*columns[i++]).getData().push_back(client_info.initial_query_start_time_microseconds);
    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(static_cast<UInt8>(client_info.interface));
    typeid_cast<ColumnUInt8 &>(*columns[i++]).getData().push_back(static_cast<UInt8>(client_info.is_secure));
    typeid_cast<ColumnString &>(*columns[i++]).insertData(log_comment.data(), log_comment.size());
}

}
