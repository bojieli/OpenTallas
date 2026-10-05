// Verilator driver for rtl/test/tb_v41x_matched_weight_ab.sv (the observation-only
// wrapper around tb_hdc_v41x_array): toggles the clock until $finish, then runs
// the final blocks, which print the A/B probe counters.
#include "Vtb_v41x_matched_weight_ab.h"
#include "verilated.h"

static vluint64_t sim_time = 0;
double sc_time_stamp() { return static_cast<double>(sim_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_v41x_matched_weight_ab* top = new Vtb_v41x_matched_weight_ab;
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
