// Verilator clock driver for tb_qfd_native59_dv_service (Q-N59).  Exit 0 only on $finish without $fatal.
#include "Vtb_qfd_native59_dv_service.h"
#include "verilated.h"
#include <cstdio>
double sc_time_stamp() { return 0; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_native59_dv_service* t = new Vtb_qfd_native59_dv_service;
    t->clk = 0; t->eval();
    for (int i = 0; i < 4000 && !Verilated::gotFinish(); i++) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    int ok = Verilated::gotFinish();
    t->final(); delete t;
    if (!ok) { std::printf("N59DV_FAIL timeout\n"); return 3; }
    return 0;
}
