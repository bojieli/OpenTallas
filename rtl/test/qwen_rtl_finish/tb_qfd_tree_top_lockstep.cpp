// Driver for tb_qfd_tree_top_lockstep: reset, N cycles, report (exit 1 on any mismatch).
#include "Vtb.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    long n = argc > 1 ? atol(argv[1]) : 20000;
    Vtb* t = new Vtb;
    t->clk = 0; t->rst_n = 0;
    for (int i = 0; i < 8; i++) { t->clk = !t->clk; t->eval(); }
    t->rst_n = 1;
    for (long c = 0; c < n; c++) { t->clk = 1; t->eval(); t->clk = 0; t->eval(); }
    unsigned long fb = t->first_bad;
    printf("{\"cycles\": %ld, \"ops\": %lu, \"result_slots\": %lu, \"argmax_nonzero_cycles\": %lu, \"mismatch_cycles\": %lu, "
           "\"first_bad_cycle\": %lu, \"first_bad_mask\": %lu}\n", n, (unsigned long)t->ops, (unsigned long)t->results,
           (unsigned long)t->amax_upd, (unsigned long)t->mism, fb >> 8, fb & 0xff);
    int bad = t->mism != 0;
    delete t;
    return bad;
}
