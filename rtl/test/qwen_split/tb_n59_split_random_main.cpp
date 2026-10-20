// Verilator clock driver for tb_n59_split_random (QW-N59-4).  Exit 0 only on $finish without $fatal.
#include "Vtb_n59_split_random.h"
#include "verilated.h"
#include <cstdio>
double sc_time_stamp() { return 0; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_n59_split_random* t = new Vtb_n59_split_random;
    t->clk = 0; t->eval();
    for (long i = 0; i < 2000000 && !Verilated::gotFinish(); i++) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    int ok = Verilated::gotFinish();
    t->final(); delete t;
    if (!ok) { std::printf("N59RND_FAIL timeout\n"); return 3; }
    return 0;
}
