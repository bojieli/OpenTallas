// Verilator driver for rtl/test/tb_hdc_v41x_wgt.sv (built with --prefix Vtb): toggles the clock until $finish.
#include "Vtb.h"
#include "verilated.h"

static double main_time = 0;
double sc_time_stamp() { return main_time; }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb* top = new Vtb;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
        main_time += 0.5;
    }
    top->final();
    delete top;
    return 0;
}
