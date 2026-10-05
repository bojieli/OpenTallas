// Verilator driver for rtl/test/tb_hdc_select.sv: toggles the clock until $finish.
#include "Vtb_hdc_select.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_select* top = new Vtb_hdc_select;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
