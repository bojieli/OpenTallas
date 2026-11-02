// Observe the unchanged, already-qualified native leaf model and its SV bench.
// No clocks, inputs, arithmetic, responses or model state are supplied here.
// This uses the same Verilator timing loop as the generated __main.cpp, adding
// read-only observation after the bench increments its real raw-valid counter.
#include "verilated.h"
#include "Vtb_native_head_leaf.h"
#include "Vtb_native_head_leaf___024root.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>

int main(int argc, char** argv) {
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> context{new VerilatedContext};
    context->threads(1);
    context->commandArgs(argc, argv);
    const std::unique_ptr<Vtb_native_head_leaf> model{new Vtb_native_head_leaf{context.get(), ""}};
    std::ofstream dump("actual_raw_prefixes.tsv");
    if (!dump) return 3;
    dump << "# raw_ordinal test_fixture_time_fs raw_fp32_lanes15_to0_hex\n";
    unsigned previous = 0;
    while (!context->gotFinish()) {
        model->eval();
        const auto count = model->rootp->tb_native_head_leaf__DOT__outputs;
        if (count != previous) {
            if (count != previous + 1 || count > 1600) {
                std::cerr << "RAW_PREFIX_COUNTER_JUMP " << previous << " " << count << "\n";
                return 4;
            }
            const auto& result = model->rootp->tb_native_head_leaf__DOT__result;
            if ((result[16] & 3U) != 1U) {
                std::cerr << "RAW_PREFIX_INVALID_OR_FAULT " << count << "\n";
                return 5;
            }
            dump << std::dec << previous << ' ' << context->time() << ' ' << std::hex << std::setfill('0');
            for (int lane = 15; lane >= 0; --lane) dump << std::setw(8) << result[lane];
            dump << '\n';
            previous = count;
        }
        if (!model->eventsPending()) break;
        context->time(model->nextTimeSlot());
    }
    model->final();
    dump.flush();
    if (!dump || !context->gotFinish() || previous != 1600) return 6;
    std::cout << "CAPTURE_ACTUAL_NATIVE_PREFIXES_PASS raw_vectors=1600 fp32_values=25600 final_K_vectors=200\n";
    context->statsPrintSummary();
    return 0;
}
