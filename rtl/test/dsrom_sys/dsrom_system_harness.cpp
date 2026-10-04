// Verilator driver for rtl/test/dsrom_sys/tb_dsrom_system.sv: toggles the clock until $finish.
#include "Vtb_dsrom_system.h"
#include "verilated.h"

static vluint64_t sim_time = 0;
double sc_time_stamp() { return static_cast<double>(sim_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_system* top = new Vtb_dsrom_system;
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
