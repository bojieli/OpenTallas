// sys-takeover 2026-10-09: two unrelated clocks for tb_qfd_seq_coll_native (Verilator 4).  Die clock plan: the
// sequencer / vector memory on the stream clock ckd, the collective engine on ck, both 833.333 ps by default with ckd
// offset by 130 ps (NCOLL_CKD_FS / NCOLL_CK_FS override, femtoseconds).
#include "Vtb_qfd_seq_coll_native.h"
#include "verilated.h"
#include <cstdlib>
static double g_t = 0;
double sc_time_stamp() { return g_t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_qfd_seq_coll_native* t = new Vtb_qfd_seq_coll_native;
    const char* e = getenv("NCOLL_CKD_FS");
    const char* ek = getenv("NCOLL_CK_FS");
    const long PCK = ek ? atol(ek) : 833333, PCKD = e ? atol(e) : 833333;
    long nck = 0, nckd = 130000;
    t->ck = 0; t->ckd = 0; t->eval();
    while (!Verilated::gotFinish()) {
        if (nck <= nckd) { t->ck = !t->ck; nck += PCK / 2; }
        else { t->ckd = !t->ckd; nckd += PCKD / 2; }
        g_t = (double)(nck < nckd ? nck : nckd) / 1000.0;
        t->eval();
    }
    t->final(); delete t; return 0;
}
