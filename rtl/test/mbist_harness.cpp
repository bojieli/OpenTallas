// Verilator driver for rtl/test/tb_mbist.sv and rtl/test/tb_secded.sv: toggles the clock until $finish.
#include "verilated.h"
#include VTOP_HEADER

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    VTOP* top = new VTOP;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
