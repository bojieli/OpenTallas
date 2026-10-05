#include "Vtb_hdc_v41x_idx_four_stack_verilator.h"
#include "verilated.h"

static double simulation_time = 0.0;
double sc_time_stamp() { return simulation_time; }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_v41x_idx_four_stack_verilator top;
    top.clk = 0;
    top.rst_n = 0;
    top.cmd_v = 0;
    top.eval();
    for (int cycle = 0; cycle < 400010 && !Verilated::gotFinish(); ++cycle) {
        if (cycle == 4) top.rst_n = 1;
        if (cycle == 5) top.cmd_v = 1;
        if (cycle == 6) top.cmd_v = 0;
        top.clk = 1;
        top.eval();
        simulation_time += 5.0;
        top.clk = 0;
        top.eval();
        simulation_time += 5.0;
    }
    const bool finished = Verilated::gotFinish();
    top.final();
    return finished ? 0 : 2;
}
