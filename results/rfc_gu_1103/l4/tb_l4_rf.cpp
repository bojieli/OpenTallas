#include "Vtb_l4_rf.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_l4_rf* t = new Vtb_l4_rf;
    t->clk = 0; t->eval();
    while (!Verilated::gotFinish()) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    delete t; return 0;
}
