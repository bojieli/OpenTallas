#include "Vtb_hbm_refresh_stream.h"
#include "verilated.h"
#include <cstdio>
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    auto* t = new Vtb_hbm_refresh_stream;
    t->rst_n = 0; for (int i = 0; i < 4; i++) { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }
    t->rst_n = 1;
    for (long c = 0; c < 4000000 && !t->done; c++) { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }
    printf("HBM_STREAM phase1_cycles=%u phase2_cycles=%u\n", t->c1, t->c2);
    return 0;
}
