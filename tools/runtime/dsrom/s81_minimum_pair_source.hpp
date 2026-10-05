#pragma once
#include "s81_minimum_runtime.hpp"

namespace dsrom_s81_minimum {
// Install before the shared cold start. The source factory retains the exact
// native phase/row owner in these closures. A selected source must supply both
// ROM and CFG reads; an unavailable selected payload must throw, never fall
// back to a different field allocation. This does not change Runtime's layout.
void bind_native_pair_source(
    DsromS81MinimumRuntime&,
    std::function<bool()> selected,
    std::function<std::array<uint32_t,9>(unsigned bank,unsigned address)> rom,
    std::function<uint64_t(unsigned address)> cfg);
}
