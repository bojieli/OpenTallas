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
- What-if B (wiB: same placement, CTS re-run with lever 2 + cb rows): hop-latch pass 5,892 latches on their launch tap, 1,058
  re-hung, 256 without a tapped launch flop. Post-CTS FF gate: 785 endpoints = cross_tap 712 worst -44.17, same_tap 71 worst -47.80,
  port_in 2 at -91.84 (IO shift not regenerated). After one pass: 0 endpoints, +5.01, 1,311 hold cells, setup unchanged -285.78, 475 s.
- Setup read (setupA, TT, placement RC, repaired wiA DB): wns -294.44, 417 endpoints, all internal; 409 are one class
  u_fab_u_x_*.u_st.b_d -> tap_d / cap / u_d*_a_d.r[0] (worst = zero logic, 20 buffers, 955 ps of wire); 8 are u_lk_nk latch -> core.
  Old source has 0 ot_qfd_xcst_rep cells; the L2 source has it (rtl/physical/qcluster/qfd_c_stn.sv). Setup on cb is UNPROVEN until
  the pilot on the L2 source; pilot gate: no b_d -> tap_d/cap/a_d endpoint below -42 at post-CTS TT.
- Limits of both: old S4Q6D source (no r301 xcst_rep), IO window shift kept at the old W 644.2, placement RC.

## Source
- claude/fable-fix-qc-dieclk-1116 @dd226b837fa: clock_taps.tcl hop-latch pass also takes u_lk_nk_*; pregrt_ff_hold pg_verdict accepts
  on endpoint + TNS gain, pass loop continues while endpoints fall >= 5 %; GRT-form anchors follow; +5 tests.
  GATE 25/25, r454 approved, MERGED (ancestor of main 17e5c950f49).
- The S4q9m published tree must carry these two files, else every cb kit repeats the FALLBACK (told QC-PLAN-R).

## Pilot on the L2 source (2026-11-17 00:xx PST), private, off-wave
- E8 /srv/opentallas-scratch2/claude/fable-fix-qc-dieclk: src_l2cb3 = real copy (57 GB) of kw45/src_qc_pin_eb1e73448bd0_s4q9l2 + plan
  zz_s29_qc103_s4q9l2cb.json (L2 19be3f0a3bb4 with the 18 cb types' rows from 5eb16cc73797, sha 511500f23114) + the two patched kit tools.
  A symlink farm does not work (kit-rtl: filelist paths outside the tree). Spec intel2 ~/fable-fix-qc-dieclk/pilot2/spec.json
  (kit_wave.py run-item), route by pilot2/chain_route.sh (ot-run E8, container dpkit-cbn_q01__clab6e67f2-3164183), kit
  pilot2/items/cbn_q01__clab6e67f2/attempt_1/gen/cbn_q01__clab6e67f2. src_l2cb, src_l2cb2 are dead farms (tiny), pilot1 a failed try.
- HOLD: post-CTS FF 526 ends (cross_tap 426 worst -49.84, same_tap 97 worst -48.93, port_in 3 at -160.82); after one pass
  0 ends, +5.00, 929 hold cells, 441 s. Lever 2: 5,892 latches on the launch tap, 868 re-hung. Hold class CLOSED at post-CTS.
- SETUP: TT -302.85 (-300.40 after the kit TT repair), 147 ends, TNS -14.2 ns; 118 on station u_fab_u_x_1_2. NOT distance:
  b_d[460] (674,532) -> r[0][460] (674,812), 2 leaf sinks within 280 um, built path about 1,740 um through the QN inverter
  _79485_ at (673,136) and the place157775..82 chain up to (664,1145). PROVEN cause (E2 fable-fix-qc-dieclk/posout/pos.log):
  in 3_3_place_gp b_d[460] was at (672,129) and r0 at (663,1234), buffered with place*; between 3_3 and 3_4_place_resized the
  two registers were re-sited to (674,532) / (675,812); the inverter and the place* chain stayed, wire* buffers were added.
  Fix = kit placement order (site station registers before global placement / buffering, or remove the place* buffers and
  re-place the QN inverter of re-sited registers), plus a post-place check buffered length / HPWL > 3. Owner QC-TYPES-R.
  No +1-cycle station row: every d6 hop is 264-288 um (x_1_2) / <= 217 um (x_0_2); street utilisation 1-8 %.
- The pilot run goes on to GRT / route; it will fail sign-off on setup (-300) unless the fix lands; read its GRT/routed FF hold.
- E8 scratch2 was at 100 % (37-108 GB free); ot-run refuses E8 under 50 GB. Delete src_l2cb3 (through the guard) after the pilot.

## Retired 2026-11-17 01:1x PST (COORD order)
- Pilot stopped at 01:03 PST (kit logs end 09:03:32 UTC, in route): docker stop/kill of the exact container name, then exact PIDs
  intel2 172958 / 1605552 and E8 3164183 / 3165194 / 3165206. The docker daemon was stalled by the full disk; verify with
  docker ps on E8 that dpkit-cbn_q01__clab6e67f2-3164183 is gone.
- src_l2cb3 (57 GB): ot_delete_guard check REFUSED for me (lane root in protected.txt, built 1794906001); the tree was removed
  by another actor at 09:09 UTC while I was checking (not by me). df E8 scratch2: 0-67 GB free before, 145-150 GB after.
- Re-siting script FOUND: kit core_input_chain.tcl (gen_phys core_input_place), sourced by gp_noconverge_gate.tcl = PRE_RESIZE_TCL,
  i.e. between 3_3_place_gp and 3_4_place_resized. Pilot log: OT_XSTN_SITE xstn 4 moved 3 cells_moved 14292 a_d_chains_spread 1032;
  OT_NK_CHAIN stages_moved 15420 head_hop_cells_moved 3598. The xstn block (file lines about 204-356) moves the b_d/cap/cnt registers
  and spreads the D6 a_d chain but leaves the b_d -> a_d.r[0] hop cells (QN inverter _N_, GPL place* buffers) where GPL put them.
  OT_XSTN_KEEP u_fab_u_x_0_2 (external nets, plan event needed) is a separate line of the same log.
- Other lanes wrote into my E8 lane dir (dd226_on_eb1e_L2_exact.patch/.json, results/): not mine, left untouched.
- Stage DBs for the proof: E2 fable-fix-qc-dieclk/stages (3_1, 3_3, 3_4, 3_5 of the pilot), posout/pos.log, setupP/, coords/.

## Open / next
1. s4q9m_l2d chain (E2 fable-die-qc-r/chain/qc/s4q9m_l2d, kit started 19:45, about 3 h): QC-CLK-R2 posts l2d rows; QC-PLAN-R
   composes S4q9m = l2d a915f1136c27 + rows + G rows + tool files, bind / LATCHECK / G0, publish E7/E8, atomic apply.
2. Setup detour fix (QC-TYPES-R), then relaunch the pilot from place on the same private tree (new attempt dir) to sign-off.
3. After the pilot signs off: release cb18 on s29q103S4Q9M, 18 types / 192 partitions; export signed types to AGIdock + rtx-pro.
4. Die clock gate: die STA with real cb views (routed pair setup >= 0, hold >= +10) once cb views exist; first proof = DRT + RCX
   of one cb region vs the SPEF offsets (QC-CLK-R2 self-review note).
5. Advisory: 6 taps over the 1,200-sink cap in cbn_q01 (clk_t115 5,425, clk_t104 2,471, clk_t42 2,488, clk_t103 2,249,
   clk_t39 1,354, clk_t97 1,281); trees still matched to 2 ps on the worst pair; finer tap pitch is a later event.

## Method shared (COORD request): post METHOD to KV-CLK-R2 / HEAD-DIE-R 21:1x (diagnose per tap pair, SPEF row cut, same-DB what-if).

## Not checked
- Routed (RCX) hold of the padded pairs; other cb types' own DBs; whether the l2d cb rows equal the s4q9m_r cb rows to 1 ps.
