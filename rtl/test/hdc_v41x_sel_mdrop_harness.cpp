// Verilator driver for rtl/test/tb_hdc_v41x_sel_mdrop.sv: toggles the clock until $finish.
#include "Vtb_hdc_v41x_sel_mdrop.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_v41x_sel_mdrop* top = new Vtb_hdc_v41x_sel_mdrop;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
