// Verilator driver for rtl/test/tb_hdc_core_hbm.sv: toggles the clock until $finish.
#include "Vtb_hdc_core_hbm.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_core_hbm* top = new Vtb_hdc_core_hbm;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
