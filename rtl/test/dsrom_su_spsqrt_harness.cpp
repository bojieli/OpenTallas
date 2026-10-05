// Verilator driver for rtl/test/tb_dsrom_su_spsqrt.sv: toggles the clock until $finish.
#include "Vtb_dsrom_su_spsqrt.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_su_spsqrt* top = new Vtb_dsrom_su_spsqrt;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
