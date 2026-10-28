// MESO-INTEG-1 loop bench driver: NSEED chips; each draws region clock phases PH[x] +- SPREAD (so every crossing's d
// stays inside its plan interval) and per-region raw-reset release cycles 2..9; runs 400 periods; every crossing:
// no fault, ready within 120 receiver counts of its start, and q == word(c - K) (sender word = its local count).
#include "Vtb_ca_loop.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include "loop_params.h"
static const long T = 833;
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int nseed = argc > 1 ? atoi(argv[1]) : 200;
  long bad = 0, checks = 0;
  for (int seed = 1; seed <= nseed; ++seed) {
    srand(seed);
    long ph[NR], rel[NR], t0[NR];
    for (int i = 0; i < NR; ++i) { ph[i] = PH[i] + (rand() % (2 * SPREAD + 1)) - SPREAD + 4 * T; rel[i] = 2 + rand() % 8; t0[i] = -1; }
    Vtb_ca_loop m; m.clk = 0; m.rst_raw_n = 0; m.eval();
    unsigned *dv[] = {&m.d_a, &m.d_b, &m.d_c, &m.d_e, &m.d_r};
    bool fault = false, wrong = false; long nok[64] = {0};
    for (long t = 0; t < 400 * T; ++t) {
      int rise = 0, fall = 0;
      for (int i = 0; i < NR; ++i) { long u = t - ph[i]; if (u >= 0 && u % T == 0) rise |= 1 << i; if (u >= 0 && u % T == 416) fall |= 1 << i; }
      if (!(rise | fall)) continue;
      unsigned st = m.start;
      for (int i = 0; i < NR; ++i) if (rise >> i & 1) {
        long e = (t - ph[i]) / T;
        if (e >= rel[i]) m.rst_raw_n |= 1u << i;
        if ((st >> i & 1) && t0[i] < 0) t0[i] = t;
        *dv[i] = t0[i] >= 0 ? 0x5A000000u + (unsigned)((t - t0[i]) / T) : 0;
      }
      m.clk &= ~fall; m.clk |= rise; m.eval();
      int k = 0;
#define X(p, s, d, K) \
      if ((rise >> d & 1) && t0[d] >= 0) { long c = (t - t0[d]) / T; \
        if (m.flt_##p) { if (!fault && bad < 8) printf("seed %d port " #p " FAULT at c=%ld\n", seed, c); fault = true; } \
        if (m.rdy_##p && !m.flt_##p) { nok[k]++; checks++; if (m.q_##p != 0x5A000000u + (unsigned)(c - K)) { \
          if (!wrong && bad < 8) printf("seed %d port " #p " q=%x want %x c=%ld\n", seed, m.q_##p, 0x5A000000u + (unsigned)(c - K), c); wrong = true; } } } \
      k++;
      PORTS(X)
#undef X
    }
    if (getenv("LOOP_DEBUG")) {
      for (int i = 0; i < NR; ++i) printf("region %d start t0 %ld (edge %ld)\n", i, t0[i], (t0[i] - ph[i]) / T);
#define X(p, s, d, K) printf("port " #p " L = %.3f T checks %ld\n", (t0[d] + (K) * T - t0[s]) / (double)T, nok[k++]);
      { int k = 0; PORTS(X) }
#undef X
    }
    int k = 0; bool slow = false;
#define X(p, s, d, K) if (nok[k++] < 200) { slow = true; if (bad < 8) printf("seed %d port " #p " only %ld checks\n", seed, nok[k - 1]); }
    PORTS(X)
#undef X
    if (fault || wrong || slow) bad++;
  }
  printf("LOOP bench: %d chips x %d crossings, %ld word checks, %ld bad chips\n", nseed, NP, checks, bad);
  return bad ? 1 : 0;
}
