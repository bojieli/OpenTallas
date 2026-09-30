// Verilator driver for the W11 lockstep benches (clock-only top, the bench finishes itself)
#include "verilated.h"
#include "Vtop.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtop* t = new Vtop;
    t->clk = 0;
    while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }
    delete t;
    return 0;
}
