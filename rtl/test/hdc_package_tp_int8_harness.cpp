// Verilator driver for rtl/test/tb_hdc_package_tp.sv: toggles the clock until $finish.
#include "Vtb_hdc_package_tp_int8.h"
#include "verilated.h"

static vluint64_t sim_time = 0;
double sc_time_stamp() { return static_cast<double>(sim_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_package_tp_int8* top = new Vtb_hdc_package_tp_int8;
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
