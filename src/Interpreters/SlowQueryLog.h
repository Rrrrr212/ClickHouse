#pragma once

#include <Interpreters/SlowQueryLogElement.h>
#include <Interpreters/SystemLog.h>

namespace DB
{

class SlowQueryLog : public SystemLog<SlowQueryLogElement>
{
    using SystemLog<SlowQueryLogElement>::SystemLog;
};

}
