#include <iostream>
#include <filesystem>
#include <vector>
#include <string>

#include <fmt/format.h>

namespace fs = std::filesystem;

struct CheckResult
{
    bool passed;
    std::string message;
};

std::vector<CheckResult> checkInstallation(const std::string & prefix)
{
    std::vector<CheckResult> results;

    const std::vector<std::string> required_binaries = {
        prefix + "/usr/bin/clickhouse",
        prefix + "/usr/bin/clickhouse-server",
        prefix + "/usr/bin/clickhouse-client"
    };

    const std::vector<std::string> required_directories = {
        prefix + "/etc/clickhouse-server",
        prefix + "/var/lib/clickhouse",
        prefix + "/var/log/clickhouse-server"
    };

    for (const auto & binary : required_binaries)
    {
        if (!fs::exists(binary))
            results.push_back({false, fmt::format("Missing binary: {}", binary)});
        else if (!fs::is_regular_file(binary))
            results.push_back({false, fmt::format("Not a regular file: {}", binary)});
        else
            results.push_back({true, fmt::format("Found binary: {}", binary)});
    }

    for (const auto & dir : required_directories)
    {
        if (!fs::exists(dir))
            results.push_back({false, fmt::format("Missing directory: {}", dir)});
        else if (!fs::is_directory(dir))
            results.push_back({false, fmt::format("Not a directory: {}", dir)});
        else
            results.push_back({true, fmt::format("Found directory: {}", dir)});
    }

    return results;
}

int main(int argc, char ** argv)
{
    std::string prefix = "";
    if (argc > 1)
        prefix = argv[1];

    auto results = checkInstallation(prefix);

    int passed = 0;
    int failed = 0;

    for (const auto & result : results)
    {
        if (result.passed)
        {
            fmt::print("✓ {}\n", result.message);
            passed++;
        }
        else
        {
            fmt::print("✗ {}\n", result.message);
            failed++;
        }
    }

    fmt::print("\n=== Summary ===\n");
    fmt::print("Total: {}, Passed: {}, Failed: {}\n",
               results.size(), passed, failed);

    if (failed > 0)
    {
        fmt::print("\nInstallation verification FAILED\n");
        return 1;
    }

    fmt::print("\nInstallation verification PASSED\n");
    return 0;
}
