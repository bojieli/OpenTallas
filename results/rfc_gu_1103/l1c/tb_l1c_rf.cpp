#include "Vtb_l1c_rf.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_l1c_rf* t = new Vtb_l1c_rf;
    t->clk = 0; t->eval();
    while (!Verilated::gotFinish()) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    delete t; return 0;
}
