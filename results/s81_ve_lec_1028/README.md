# ve_m retained RF constant diagnosis

Inherited kit: s81-cores-r27/lec12/kits/ot_s81sl_ve_m_r1. KEEP FAIL:49241 compare points,47465 proved,
1776 differ,640 missing of15183 declared kept bits. This evidence is preserved.

The actual RF is ot_s81sl_ve_ring in ot_s81sl_ve.sv; its add.hline has W32,D5,N3,K2.
The gate retains distinct high-half q/q2 flops. Missing low BF16 lanes are folded constants,
not missing high-value replica flops. Downstream x_aman low bits are also folded and supply
the first reported compare failures.

These minimal SAT cones use the exact current ring RTL with SYNTHESIS and arbitrary defined
hardware initial state, unconstrained input data at every edge, no reset/phase assumption:
- Ring plus one BF16 capture: low lanes universally zero after6edges;5edges SAT.
- Full-word ring versus shift delay, both outputs: lockstep6edges UNSAT; read-selector MUT3 SAT.
  The five-edge lockstep also passes; it is retained as a PASS, not a negative control.
- Actual ah_q BF16 expansion -> hr capture -> ring -> x_aman decode bit0:8edges UNSAT,
  7edges SAT; wrong bit16 SAT at8edges.

There is no RTL, pin, reset-duration, timing or cycle change in this commit. Whole-master
current LEC with existing OT_LEC_RAW_BASE_STEPS=8 is still running in an own exact kit copy,
with the unchanged release_unmasked check. The finite-prefix work proves a fact; it does not
authorize a new warmup phase or allow an early-observable value to be assumed constant.
No EQUIVALENT or SIGNED master claim is made by these component results.

Current selected sources match main26/27 staged files; the sole differing fp32_add_lat file
is explicitly pruned unused by actual ve_m hierarchy. The primary ve and custom arithmetic
sources are byte-identical to main.
