// Verilator driver for the DeepSeek-V4.1 HDC benches (tb_hdc_v41_quant,
// tb_hdc_v41_blockdot), built with --prefix Vtb: toggles the clock until $finish.
#include "Vtb.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb* top = new Vtb;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
