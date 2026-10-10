// sys-takeover 2026-10-09: two unrelated clocks for tb_qfd_coll_native (Verilator 4): ck 833.333 ps, ckd 1111.111 ps,
// ckd offset by 130 ps; the time step is 1 ps.
#include "Vtb_qfd_coll_native.h"
#include "verilated.h"
static double g_t = 0;
double sc_time_stamp() { return g_t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_coll_native* t = new Vtb_qfd_coll_native;
    const long PCK = 833333, PCKD = 1111111;   // femtoseconds
    long nck = 0, nckd = 130000;                  // next toggle times (fs)
    t->ck = 0; t->ckd = 0; t->eval();
    while (!Verilated::gotFinish()) {
        if (nck <= nckd) { t->ck = !t->ck; nck += PCK / 2; }
        else { t->ckd = !t->ckd; nckd += PCKD / 2; }
        g_t = (double)(nck < nckd ? nck : nckd) / 1000.0;
        t->eval();
    }
    t->final(); delete t; return 0;
}
