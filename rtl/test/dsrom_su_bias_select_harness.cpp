// Verilator driver for rtl/test/tb_dsrom_su_bias_select.sv: toggles the clock until $finish.
#include "Vtb_dsrom_su_bias_select.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_su_bias_select* top = new Vtb_dsrom_su_bias_select;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
