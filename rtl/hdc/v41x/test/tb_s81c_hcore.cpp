#include "Vtb_s81c_hcore.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_s81c_hcore* t = new Vtb_s81c_hcore;
    t->clk = 0;
    for (long k = 0; k < 4000000 && !Verilated::gotFinish(); ++k) { t->clk = !t->clk; t->eval(); }
    delete t;
    return 0;
}
