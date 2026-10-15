// sys-takeover 2026-10-09: two unrelated clocks for tb_qfd_coll_native (Verilator 4): ck 833.333 ps, ckd 1111.111 ps,
// ckd offset by 130 ps; the time step is 1 ps.
#include "Vtb_qfd_coll_native.h"
#include "verilated.h"
#include <cstdlib>
static double g_t = 0;
double sc_time_stamp() { return g_t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_coll_native* t = new Vtb_qfd_coll_native;
    // NCOLL_CKD_FS (env): sequencer-domain period in fs (default 1111111 = 0.9 GHz; 833333 = the 1.2 GHz lever)
    const char* e = getenv("NCOLL_CKD_FS");
    const char* ek = getenv("NCOLL_CK_FS");   // engine-domain period (default 833333 = 1.2 GHz)
    const long PCK = ek ? atol(ek) : 833333, PCKD = e ? atol(e) : 1111111;   // femtoseconds
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
