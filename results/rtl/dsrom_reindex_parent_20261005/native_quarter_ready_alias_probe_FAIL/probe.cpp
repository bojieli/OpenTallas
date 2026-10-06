// Read-only counters from the completed quarter archive. No DUT writes,
// no fatal waiver and no arithmetic or scheduler replacement.
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
    bool request_stall = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "+HOLD_FIRST_SCORE=1") == 0) request_stall = true;
    auto context = std::make_unique<VerilatedContext>();
    context->threads(1);
    context->commandArgs(argc, argv);
    auto model = std::make_unique<Vtb_dsrom_reindex_native_quarter>(context.get(), "");
    Verilated::addExitCb(counters, model.get());
    bool held_once = false;
    unsigned hold_edges = 0;
    while (!context->gotFinish()) {
        auto* r = model->rootp;
        const bool previous_clock = r->tb_dsrom_reindex_native_quarter__DOT__clk;
        // The only writable DUT boundary is the existing consumer-ready pin.
        // This gives the prepared bench a deterministic three-edge stall;
        // native arithmetic, valid, credits, reset and fatal checks stay live.
        if (hold_edges) r->tb_dsrom_reindex_native_quarter__DOT__sc_ready = 0;
        model->eval();
        bool started = false;
        if (request_stall && !held_once &&
            r->tb_dsrom_reindex_native_quarter__DOT__scoring &&
            r->tb_dsrom_reindex_native_quarter__DOT__sc_valid) {
            held_once = true;
            hold_edges = 3;
            started = true;
        }
        if (hold_edges) {
            r->tb_dsrom_reindex_native_quarter__DOT__sc_ready = 0;
            model->eval();
            if (!started && !previous_clock && r->tb_dsrom_reindex_native_quarter__DOT__clk)
                --hold_edges;
        }
        if (!model->eventsPending()) break;
        context->time(model->nextTimeSlot());
    }
    counters(model.get());
    model->final();
    return 0;
}
