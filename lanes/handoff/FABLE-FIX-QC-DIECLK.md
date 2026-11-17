# FABLE-FIX-QC-DIECLK handoff (QC die clock closure + cb family, end to end). Started 2026-11-16 20:4x PST.

Work dir epyc2 /srv/opentallas-scratch3/claude/fable-fix-qc-dieclk (repo/ = my clone, wiA/, wiB/, helper scripts).
Client logs intel2 ~/fable-fix-qc-dieclk/. Lanes directed by posts: QC-CLK-R2 (rows), QC-TYPES-R (kits), QC-PLAN-R (plan, wave).

## Measured so far
- Residual 707 pairs (projection, tol 11, latch on launch tap): all flop -> flop, 31 tap pairs, 634 fail only by the 2 x tol = 22 ps
  window, 65 fail on an ideal clock (zero-logic pipe stages vs 25 ps hold uncertainty), 606 within -20 ps. Tighter tol: tol 5 -> 267,
  tol 3 -> 168, tol 0 -> 73. No per-pair budget or tap move is needed: it is ordinary padding. (resid.py on fable-pd-qc-mclk/rows.tsv)
- What-if A (wiA: failed kit cee3540cfd65 4_cts.odb unchanged + kit SDC rewritten with S4q9m cb rows 5eb16cc73797 + lever-3 repair):
  before 1,736 endpoints, cross-tap 1,699 worst -81.55; after ONE pass 0 endpoints, wns +5.00, 2,369 hold cells (0.55 %),
  TT setup estimate unchanged -294.44, 0 overlaps, 861 s. Old rows: 36,093 cells and -211.66 kept.
- What-if B (wiB: same placement, CTS re-run with lever 2): hop-latch pass 5,892 latches on their launch tap, 1,058 re-hung,
  256 without a tapped launch flop; result lines in wiB/kit/hold_gate.log, pregrt_ff_hold.log (see posts).
- Limits of both: old S4Q6D source (no r301 xcst_rep), IO window shift kept at the old W 644.2, placement RC.

## Source
- claude/fable-fix-qc-dieclk-1116 @dd226b837fa: clock_taps.tcl hop-latch pass also takes u_lk_nk_*; pregrt_ff_hold pg_verdict accepts
  on endpoint + TNS gain, pass loop continues while endpoints fall >= 5 %; GRT-form anchors follow; +5 tests.
  Gate: intel2 ~/fable-fix-qc-dieclk/gate2.client.log (gate1 = RED on a source-text test, fixed). Post READY on GREEN.
- The S4q9m published tree must carry these two files, else every cb kit repeats the FALLBACK (told QC-PLAN-R).

## Open / next
1. s4q9m_l2d chain (E2 fable-die-qc-r/chain/qc/s4q9m_l2d, kit started 19:45, about 3 h): QC-CLK-R2 posts l2d rows; QC-PLAN-R
   composes S4q9m = l2d a915f1136c27 + rows + G rows + tool files, bind / LATCHECK / G0, publish E7/E8, atomic apply.
2. cb pilot before adoption (directive 21:1x): private plan = L2 19be3f0a3bb4 + cb rows, private src = L2 tree + 2 tool files,
   canary for cbn_q01__clab6e67f2 to route + sign-off. Gate at post-CTS: cross_tap <= 2,000, ws >= -90, 0 u_lk_nk_* endpoints
   open; after repair 0 endpoints. If not launched by 22:15 run it by hand (kit_wave.py step --config, private AP_DIR).
3. After the pilot signs off: release cb18 on s29q103S4Q9M, 18 types / 192 partitions; export signed types to AGIdock + rtx-pro.
4. Die clock gate: die STA with real cb views (routed pair setup >= 0, hold >= +10) once cb views exist; first proof = DRT + RCX
   of one cb region vs the SPEF offsets (QC-CLK-R2 self-review note).
5. Advisory: 6 taps over the 1,200-sink cap in cbn_q01 (clk_t115 5,425, clk_t104 2,471, clk_t42 2,488, clk_t103 2,249,
   clk_t39 1,354, clk_t97 1,281); trees still matched to 2 ps on the worst pair; finer tap pitch is a later event.

## Not checked
- Routed (RCX) hold of the padded pairs; other cb types' own DBs; whether the l2d cb rows equal the s4q9m_r cb rows to 1 ps.
