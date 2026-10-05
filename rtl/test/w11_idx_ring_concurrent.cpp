#include "Vtb_w11_idx_ring_concurrent.h"
#include "verilated.h"
#include <cstdlib>
#include <cstring>

static double simulation_time = 0.0;
double sc_time_stamp() { return simulation_time; }

// Clock/reset driver; the bench sequences itself.  +max_cycles=<n> bounds the run.
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    long long max_cycles = 60000000LL;
    for (int i = 1; i < argc; ++i)
        if (std::strncmp(argv[i], "+max_cycles=", 12) == 0) max_cycles = std::atoll(argv[i] + 12);
    Vtb_w11_idx_ring_concurrent top;
    top.clk = 0; top.rst_n = 0; top.cmd_v = 0;
    top.eval();
    for (long long cycle = 0; cycle < max_cycles && !Verilated::gotFinish(); ++cycle) {
        if (cycle == 4) top.rst_n = 1;
        top.clk = 1; top.eval(); simulation_time += 5.0;
        top.clk = 0; top.eval(); simulation_time += 5.0;
    }
    const bool finished = Verilated::gotFinish();
    top.final();
    return finished ? 0 : 2;
}
