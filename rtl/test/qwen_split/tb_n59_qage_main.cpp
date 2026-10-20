// Verilator clock driver for tb_n59_qage (QW-N59-5).  Exit 0 only on $finish without $fatal.
#include "Vtb_n59_qage.h"
#include "verilated.h"
#include <cstdio>
double sc_time_stamp() { return 0; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_n59_qage* t = new Vtb_n59_qage;
    t->clk = 0; t->eval();
    for (int i = 0; i < 4000 && !Verilated::gotFinish(); i++) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    int ok = Verilated::gotFinish();
    t->final(); delete t;
    if (!ok) { std::printf("N59QAGE_FAIL timeout\n"); return 3; }
    return 0;
}
