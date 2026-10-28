// Usage: Vtb CASES.tsv  (lines: id <tab> depth <tab> L_ps), only lines whose depth equals the build's DEPTH are run.
// Per case: sender clock edges at n*T (fclk = forwarded sender clock), receiver edges at m*T + phi.  The sender writes
// word n (data = 0x5A000000 + n) at fclk edge n of its count (first edge with t_rst_n high = word 0).  The receiver
// origin edge (first edge with rst_n high, count 0) is placed at t_r0 = t_w0 + L - K*T.  Checks at every receiver
// edge after ready: q (sampled right after receiver edge `count`) == word (count - K): the consumer flop takes it at count + 1, latency K + 1, fault never; ready within 60 cycles.
// Mode "sweep LMIN LMAX STEP" instead runs a lag sweep and prints the [first,last] L that came up clean, and checks
// that every other L either faults or never becomes ready (fail closed) and never presents a wrong word while ready.
#include "Vtb_dp_clk_landing_ca.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#ifndef KPAR
#define KPAR 2
#endif
#ifndef DPAR
#define DPAR 4
#endif
static const long T = 833;
struct Res { bool ready, fault, wrong; long checks; };
static Res run_case(long L) {
  Vtb_dp_clk_landing_ca m;
  long tw0 = 12 * T;                 // sender word 0 written at this fclk edge
  long tr0 = tw0 + L - KPAR * T;      // receiver origin edge
  long base = 4 * T;                  // keep both origins after a few cycles of each clock
  if (tr0 < base) { long sh = base - tr0; tw0 += ((sh + T - 1) / T) * T; tr0 = tw0 + L - KPAR * T; }
  long phi = ((tr0 % T) + T) % T;
  m.fclk = 0; m.clk = 0; m.t_rst_n = 0; m.rst_n = 0; m.d = 0; m.eval();
  Res r{false, false, false, 0};
  long tend = tr0 + 80 * T;
  long n_next = 0;                    // sender count of the word presented for the next fclk edge
  bool wrong_printed = false;
  for (long t = 0; t <= tend; ++t) {
    bool fr = t % T == 0, ff = t % T == 416;
    bool rr = t >= phi && (t - phi) % T == 0, rf = t >= phi && (t - phi) % T == 416;
    if (!(fr || ff || rr || rf)) continue;
    // inputs change just after the edge that launches them: set them before the edge they are sampled on
    if (fr) {
      // t_rst_n is the sender's start flop: high from the fclk edge that writes word 0 (sampled at that edge)
      m.t_rst_n = (t >= tw0) ? 1 : 0;
      m.d = 0x5A000000u + (unsigned)(t >= tw0 ? (t - tw0) / T : 0);
    }
    if (rr) m.rst_n = (t >= tr0) ? 1 : 0;
    if (ff) m.fclk = 0;
    if (rf) m.clk = 0;
    if (fr) m.fclk = 1;
    if (rr) m.clk = 1;
    m.eval();
    if (rr && t >= tr0) {
      long cnt = (t - tr0) / T;       // receiver count of this edge
      if (m.fault) r.fault = true;
      if (m.ready && !m.fault) {
        r.ready = true; r.checks++;
        long want = cnt - KPAR;      // the word captured at this edge (RDREG): the next receiver flop takes it at count + 1
        unsigned w = 0x5A000000u + (unsigned)want;
        if (want < 0 || m.q != w) { r.wrong = true; if (!wrong_printed) { wrong_printed = true;
          fprintf(stderr, "WRONG L=%ld cnt=%ld q=%08x want=%08x\n", L, cnt, (unsigned)m.q, w); } }
      }
    }
  }
  (void)n_next;
  return r;
}
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  if (argc > 1 && !strcmp(argv[1], "sweep")) {
    long lo = atol(argv[2]), hi = atol(argv[3]), st = atol(argv[4]);
    long first = -1, last = -1, bad = 0, n = 0, nclean = 0;
    for (long L = lo; L <= hi; L += st) {
      Res r = run_case(L); n++;
      bool clean = r.ready && !r.fault && !r.wrong && r.checks > 40;
      if (r.wrong) bad++;                       // wrong word while ready and not faulted: silent error
      if (clean) { if (first < 0) first = L; last = L; nclean++; }
    }
    printf("SWEEP K=%d DEPTH=%d L=[%ld,%ld] step %ld: clean window [%ld, %ld] ps = [%.3f, %.3f] T (%ld clean, contiguous %s), silent-wrong %ld of %ld\n",
           KPAR, DPAR, lo, hi, st, first, last, first / (double)T, last / (double)T, nclean,
           (nclean == (last - first) / st + 1) ? "yes" : "NO", bad, n);
    return (bad || nclean != (last - first) / st + 1) ? 1 : 0;
  }
  FILE* f = fopen(argv[1], "r");
  if (!f) { perror("cases"); return 2; }
  char id[256]; int dep; long L; long ok = 0, fail = 0;
  while (fscanf(f, "%255s %d %ld", id, &dep, &L) == 3) {
    if (dep != DPAR) continue;
    Res r = run_case(L);
    bool good = r.ready && !r.fault && !r.wrong && r.checks > 40;
    if (good) ok++; else { fail++; if (fail < 20) printf("FAIL %s L=%ld ready=%d fault=%d wrong=%d checks=%ld\n", id, L, r.ready, r.fault, r.wrong, r.checks); }
  }
  printf("CASES K=%d DEPTH=%d: %ld PASS %ld FAIL\n", KPAR, DPAR, ok, fail);
  return fail ? 1 : 0;
}
