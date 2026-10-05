// Verilator driver for rtl/test/tb_v41_l0_live_chain.sv: toggles the clock until $finish.
#include "Vtb_v41_l0_live_chain.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_v41_l0_live_chain* top = new Vtb_v41_l0_live_chain;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
