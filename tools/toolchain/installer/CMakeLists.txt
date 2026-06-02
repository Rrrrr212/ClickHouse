add_executable(clickhouse-install Install.cpp)
target_link_libraries(clickhouse-install PRIVATE clickhouse_common_io clickhouse_common_config clickhouse_common_zlib OpenSSL::SSL Boost::program_options fmt::fmt)

if (TARGET clickhouse-common-static)
    target_link_libraries(clickhouse-install PRIVATE clickhouse-common-static)
endif()

install(TARGETS clickhouse-install RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
