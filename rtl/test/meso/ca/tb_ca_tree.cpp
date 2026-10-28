// Sweep the child clock phase phi over one period at 1 ps: the parent start rises at fclk edge 12 (word 0 written
// there); the child origin is the first child edge where `start` is high.  Checks: ready, no fault, q == word(c - K)
// after child edge c, and reports the lag L = t_r0 + K*T - t_w0 range (must span < T + 1 ps: the tree window).
#include "Vtb_ca_tree.h"
#include "verilated.h"
#include <cstdio>
#ifndef KPAR
#define KPAR -2
#endif
static const long T = 833;
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  long Lmin = 1 << 30, Lmax = -(1 << 30), bad = 0, n = 0;
  for (long phi = 0; phi < T; ++phi) {
    Vtb_ca_tree m; m.fclk = 0; m.clk = 0; m.p_start = 0; m.rst_raw_n = 0; m.d = 0; m.eval();
    long tw0 = 12 * T, tr0 = -1; bool fault = false, wrong = false; long checks = 0;
    for (long t = 0; t < 100 * T; ++t) {
      bool fr = t % T == 0, ff = t % T == 416, rr = t >= phi && (t - phi) % T == 0, rf = t >= phi && (t - phi) % T == 416;
      if (!(fr || ff || rr || rf)) continue;
      if (fr) { m.p_start = t >= tw0; m.d = 0x5A000000u + (unsigned)(t >= tw0 ? (t - tw0) / T : 0); }
      if (rr) m.rst_raw_n = t >= 2 * T;
      if (ff) m.fclk = 0; if (rf) m.clk = 0; if (fr) m.fclk = 1; if (rr) m.clk = 1;
      bool start_before = m.start;
      m.eval();
      if (rr && start_before && tr0 < 0) tr0 = t;   // first child edge that samples start high = count 0
      if (rr && tr0 >= 0) {
        long c = (t - tr0) / T;
        if (m.fault) fault = true;
        if (m.ready && !m.fault) { checks++; if (m.q != 0x5A000000u + (unsigned)(c - KPAR)) wrong = true; }
      }
    }
    long L = tr0 + KPAR * T - tw0;
    if (L < Lmin) Lmin = L; if (L > Lmax) Lmax = L;
    n++; if (fault || wrong || checks < 40) { if (bad++ < 5) printf("BAD phi=%ld L=%ld fault=%d wrong=%d checks=%ld\n", phi, L, fault, wrong, checks); }
  }
  printf("TREE K=%d: %ld phases, %ld bad, lag L in [%ld, %ld] ps = [%.3f, %.3f] T\n", KPAR, n, bad, Lmin, Lmax, Lmin / (double)T, Lmax / (double)T);
  return bad ? 1 : 0;
}
