#include "Vtb_hdc_v41x_idx_kgrow.h"
#include "verilated.h"

static double simulation_time = 0.0;
double sc_time_stamp() { return simulation_time; }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_v41x_idx_kgrow top;
    top.clk = 0;
    top.eval();
    for (long cycle = 0; cycle < 8000000 && !Verilated::gotFinish(); ++cycle) {
        top.clk = 1; top.eval(); simulation_time += 5.0;
        top.clk = 0; top.eval(); simulation_time += 5.0;
    }
    const bool finished = Verilated::gotFinish();
    top.final();
    return finished ? 0 : 2;
}
