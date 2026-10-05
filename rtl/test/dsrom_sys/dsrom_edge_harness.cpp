// Verilator driver for the EDGE INDEX SCORER benches: toggles the clock until $finish.
#include "verilated.h"
#include EDGE_TOPH

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    EDGE_TOP* top = new EDGE_TOP;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
