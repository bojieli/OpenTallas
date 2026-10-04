// Verilator driver for rtl/test/dsrom_wavefront/tb_dsrom_wavefront_array.sv: toggles the clock until $finish.
#include "Vtb_dsrom_wavefront_array.h"
#include "verilated.h"

static vluint64_t sim_time = 0;
double sc_time_stamp() { return static_cast<double>(sim_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_wavefront_array* top = new Vtb_dsrom_wavefront_array;
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
