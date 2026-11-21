#include "Vtb.h"
#include "verilated.h"
#include <cstdio>
#include <random>
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  Vtb* t = new Vtb; std::mt19937_64 r(12345);
  long N = 100000;
  for (long c = 0; c < N; c++) {
    t->rst_n = c >= 8;
    t->g_v = r() & 7; t->g_fam = r() & 7; t->g_idx = r() & 0x1fffff;
    for (int w = 0; w < 96; w++) t->g_d[w] = (uint32_t)r();
    t->is_v = (r() & 15) == 0; for (int w = 0; w < 5; w++) t->is_d[w] = (uint32_t)r();
    if (c % 2000 == 1000) { t->rst_n = 0; }
    t->clk = 0; t->eval(); t->clk = 1; t->eval();
  }
  printf("WC_LOCKSTEP cycles=%ld mism=%u writes=%u\n", N, t->mism, t->wr_seen);
  int ok = t->mism == 0 && t->wr_seen > 20000;
  printf(ok ? "WC_LOCKSTEP PASS\n" : "WC_LOCKSTEP FAIL\n");
  delete t; return ok ? 0 : 1;
}
