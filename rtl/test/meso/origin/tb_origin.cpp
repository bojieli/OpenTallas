// MESO-COUNT-2 task 3: exhaustive start-sync check of ot_dp_landing_origin (RTL, Verilator) for one tree edge.
// Parent edges at n*T; the parent's start is launched at parent edge SP (its count origin a_p = SP + 1) and reaches the
// child's first sync flop delta ps later (delta = start-path skew vs fclk).  Child edges at m*T + phi, phi = 0..T-1 ps
// (EVERY static phase at 1 ps).  Metastability: a first-stage sample within +-SAP ps of the transition captures 0 OR 1:
// both outcomes are run.  Child origin a_c = first child edge sampling `start` high.  Checks per phase:
//   d = phi - delta (effective phase), off = 0 (rise) / T/2 (fall), J(d) = -floor((d - off)/T):
//   clean (|d - off| mod T > SAP): a_c - a_p == PAD + 2 + J(d) for both outcomes (one value);
//   ambiguous: phase phi_L = (a_c - a_p - PAD - 2) T + d in [off - SAP, off + T + SAP] (the plan's sync window).
#include "Vtb_origin.h"
#include "verilated.h"
#include <cstdio>
#include <cmath>
static const long T = 833;
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  long SAP = 27, delta = 0; if (argc > 1) delta = atol(argv[1]);
  const long off = EF ? T - T / 2 : 0;   // falling edge at phi + T/2 (integer ps) = phi - (T - T/2) mod T
  long bad = 0, n = 0, amb = 0, two = 0, wlo = 1 << 30, whi = -(1 << 30);
  for (long SP = 3; SP <= 4; ++SP)
  for (long phi = 0; phi < T; ++phi) {
    long dv[2];
    for (int v = 0; v < 2; ++v) {
      Vtb_origin m; m.clk = 0; m.rst_raw_n = 0; m.p_start = 0; m.eval();
      long tr = SP * T + delta, ac = -1;
      for (long t = 0; t < 40 * T && ac < 0; ++t) {
        bool rr = t >= phi && (t - phi) % T == 0, rf = t >= phi && (t - phi) % T == T / 2;
        if (!(rr || rf)) continue;
        bool samp = EF ? rf : rr;
        long dt = t - tr;
        bool ps = t > tr;
        if (samp && std::labs(dt) <= SAP) ps = v;         // metastable sample: forced outcome
        m.p_start = ps;
        if (rr) m.rst_raw_n = t >= phi + T;              // raw reset through the first child edge
        bool st = m.start;
        if (rr && st && m.rst_raw_n && t >= phi + 2 * T) ac = (t - phi) / T;   // child edge index sampling start high
        if (rf) m.clk = 0;
        if (rr) m.clk = 1;
        m.eval();
      }
      dv[v] = ac - (SP + 1);
    }
    double d = phi - delta;
    long J = -(long)std::floor((d - off) / (double)T);
    double r = std::fmod(std::fmod(d - off, (double)T) + T, (double)T);
    bool isamb = r <= SAP || r >= T - SAP;
    n++; amb += isamb; two += (dv[0] != dv[1]);
    for (int v = 0; v < 2; ++v) {
      double ph = (dv[v] - PADV - 2) * (double)T + d;
      if (ph < wlo) wlo = (long)std::floor(ph); if (ph > whi) whi = (long)std::ceil(ph);
      bool ok = isamb ? (ph >= off - SAP && ph <= off + T + SAP) : (dv[v] == PADV + 2 + J);
      if (!ok) { if (bad++ < 5) printf("BAD SP=%ld phi=%ld v=%d da=%ld J=%ld amb=%d\n", SP, phi, v, dv[v], J, isamb); }
    }
  }
  printf("ORIGIN PAD=%d EDGE_FALL=%d delta=%ld: %ld phase cases (1 ps), %ld ambiguous, %ld with 2 outcomes, %ld bad; "
         "a_c-a_p = PAD+2+J(d) on every clean phase; sync phase in [%ld, %ld] ps (window [%ld, %ld])\n",
         PADV, EF, delta, n, amb, two, bad, wlo, whi, off - SAP, off + T + SAP);
  return bad ? 1 : 0;
}
