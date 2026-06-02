add_executable(clickhouse-install-verify InstallVerify.cpp)
target_link_libraries(clickhouse-install-verify PRIVATE clickhouse_common_io fmt::fmt)
install(TARGETS clickhouse-install-verify RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
