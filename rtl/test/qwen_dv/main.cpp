// Verilator driver for tb_qfd_dv: free-running clock until $finish.
#include "Vtb_qfd_dv.h"
#include "verilated.h"
static double g_t = 0;
double sc_time_stamp() { return g_t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_dv* t = new Vtb_qfd_dv;
    t->ck = 0;
    while (!Verilated::gotFinish()) { t->ck = !t->ck; t->eval(); g_t += 0.5; }
    t->final();
    delete t;
    return 0;
}
