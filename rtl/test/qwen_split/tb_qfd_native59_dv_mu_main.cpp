// Verilator clock driver for tb_qfd_native59_dv_mu (MU-DQ-D2DUSER).  Exit 0 only on $finish without $fatal.
#include "Vtb_qfd_native59_dv_mu.h"
#include "verilated.h"
#include <cstdio>
double sc_time_stamp() { return 0; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_native59_dv_mu* t = new Vtb_qfd_native59_dv_mu;
    t->clk = 0; t->eval();
    for (int i = 0; i < 6000 && !Verilated::gotFinish(); i++) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    int ok = Verilated::gotFinish();
    t->final(); delete t;
    if (!ok) { std::printf("N59MU_FAIL timeout\n"); return 3; }
    return 0;
}
