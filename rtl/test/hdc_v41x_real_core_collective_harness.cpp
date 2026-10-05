// Clock driver for the adopted-core producer/collective/consumer stage bench.
#include "Vtb_v41x_real_core_collective.h"
#include "verilated.h"

static vluint64_t sim_time = 0;
double sc_time_stamp() { return static_cast<double>(sim_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    auto* top = new Vtb_v41x_real_core_collective;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
        ++sim_time;
    }
    top->final();
    delete top;
    return 0;
}
