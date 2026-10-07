// Reuse the completed quarter archive and its actual compiled SV scheduler.
// Read-only counters; an optional initial TESTBENCH edge-counter origin shifts
// the existing periodic ready stimulus. No DUT pin/state/credit/fatal writes.
// A constant counter-origin offset cancels in every measured cycle difference.
#include "verilated.h"
#include "Vtb_dsrom_reindex_native_quarter.h"
#include "Vtb_dsrom_reindex_native_quarter___024root.h"
#include <cstdio>
#include <memory>
#include <cstring>

static void counters(void* model) {
    const auto* r = static_cast<Vtb_dsrom_reindex_native_quarter*>(model)->rootp;
    std::fprintf(stderr,
        "QUARTER_DIAG accepted=%u received=%u checked=%u refused=%u invalid=%u stalled=%u\n",
        r->tb_dsrom_reindex_native_quarter__DOT__accepted,
        r->tb_dsrom_reindex_native_quarter__DOT__received,
        r->tb_dsrom_reindex_native_quarter__DOT__checked,
        r->tb_dsrom_reindex_native_quarter__DOT__refused,
        r->tb_dsrom_reindex_native_quarter__DOT__invalid,
        r->tb_dsrom_reindex_native_quarter__DOT__stalled);
    std::fflush(stderr);
}

int main(int argc, char** argv) {
    unsigned ready_phase = 0;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "+READY_PHASE=1") == 0) ready_phase = 1;
    auto context = std::make_unique<VerilatedContext>();
    context->threads(1);
    context->commandArgs(argc, argv);
    auto model = std::make_unique<Vtb_dsrom_reindex_native_quarter>(context.get(), "");
    Verilated::addExitCb(counters, model.get());
    bool origin_set = false;
    while (!context->gotFinish()) {
        model->eval();
        if (!origin_set) {
            origin_set = true;
            model->rootp->tb_dsrom_reindex_native_quarter__DOT__edges += ready_phase;
            std::fprintf(stderr, "QUARTER_STIMULUS ready_phase=%u hardware_clock_unchanged=1\n", ready_phase);
        }
        if (!model->eventsPending()) break;
        context->time(model->nextTimeSlot());
    }
    counters(model.get());
    model->final();
    return 0;
}
