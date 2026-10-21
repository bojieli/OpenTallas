# PVM9 r6 (HBM-SMATT8 2026-10-20), ep6 /srv/opentallas-scratch/claude/pvm9-r6-1020

r6 is a copy of r5 (RTL 5d4cc226a/cd7a2f865 + kit 445ac5e26). It resumes at the first failed stage. Floorplan through 3_4 passed in r5, and their receipts are in that run's stage_inventory.

1. r5 3_5_place_dp DPL-0033 (55 site-alignment problems, 31 overlaps, 2 edge-spacing violations). All 85 offending cells are NON-member cells. They sit on the 16 EXCLUSIVE fence edges (x 45.36 / 73.44 / 271.98 / 324.0) or in the 4.32 um slivers between fence columns, and the bad ones are 1 dbu off the site grid. The fences themselves are on the grid (core origin 2.16, site 0.054, row 0.27).
   I replayed DPL offline on the r5 3_4 odb (`smatt8_dpt.tcl`, `dpl_replay_*.out`). The negotiation legalizer alone is clean. improve_placement (DPO) on its output gives the DPL-0033. The diamond legalizer, with or without DPO, gives 0 violations.
   Fix: `DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer`. With it, r6 3_5 and 3_place PASS.
2. r6 4_1_cts ODB-0370: CTS cannot reconnect the CLK term of a dont_touch bind-first kernel flop.
   `pvm_cts_release.tcl` (PRE_CTS) releases dont_touch on the 10064 protected SEQUENTIAL kernel cells only, and records every non-clock term->net binding first. It wraps clock_tree_synthesis so that `pvm_cts_restore.tcl` runs right after CTS, before repair_timing. The restore re-protects the same set and refuses on any non-clock binding change. Result: PASS, 10064 re-protected, bindings identical.
3. r6b 4_1_cts EST-0104 at repair_timing. Standard-mode ot_protect_clock_tree PG-binds 5 new CTS cells after cts.tcl's estimate_parasitics, and only strict mode re-estimates. As a run-local fix, the release hook re-estimates placement RC after ot_protect_clock_tree. This needs a common_flow fix.
r6c = r6b with fix 3, running 4_1_cts -> 4_cts -> 5_1_grt.

## r7a audit-only rerun on r6c 5_1_grt + r8 kernel hold fix (HBM-SMATT9 10-20)
r6c 4_1_cts/4_cts/5_1_grt rc 0; GRT overflow 0 (12.4% usage). The two r6c audit failures were invocation errors:
- post_grt_audit: asserted native PG BEFORE the final global_connect (helper says "run after final global_connect").
  18028 unbound terms = resizer hold/wire buffers only, dont_touch 0. r7a/pg_audit2.tcl: global_connect in memory -> OT_PG_FINAL_PASS 206730.
- post_grt_native32: mapped-netlist census run on a post-CTS netlist: walks clk -> wire9654 (repair_clock_nets) -> CTS tree (635) and
  flags 8531 TAPCELLs. r7a/fanout_audit.py (clock network + PG excluded): max 32 dynamic; only >32 = TIEHI _33678_ constant (112).
Facts at 5_1_grt (r7a): sequential reach max 444.8 um, 8 >405 (one source g_first_tag1[1] -> g_first_tag[54..63], meets TT);
CTS insertion TT 350..419 (all, spread 69) / boundary 358..401 (43); FF 283..347 (64) / boundary 291..331 (40);
TT setup @833.333 worst -5.16 (pv_y outputs, route-SDC IO; reg paths met; route @770 -25.65);
FF hold reg->reg -50.04 ps, 448 endpoints, ALL inside g_native7.u_native (cX/QN -> inv -> cY/D, ~82 ps local skew):
REAL defect - repair_timing cannot buffer dont_touch kernel flops/nets (r6b released them for CTS only).
Input-port hold (-147 sum->sum1, -111 rst_n) = diagnostic SDC artifact (5_1_grt.sdc w/o die-context re-reference; route repair saw kernel worst).
r8 (bf8/work copy of bf/work, r6c verdicts kept): sequential kernel cells + their input nets stay released through 4_1_cts/5_1_grt
so hold repair can buffer D inputs; comb kernel cells stay dont_touch; restore+change report at POST_GLOBAL_ROUTE (owner 10-20 09:05:
standard equivalence + strict bind). Then fixed audits; 5_2_route + 5_3_fillcell only if PG binds and FF reg hold >= -5 ps.

## r8 5_1_grt FAIL + r9 a/b (HBM-PVM10 10-20)
r8 4_1_cts/4_cts PASS; 5_1_grt GRT itself PASS (overflow 0, 14.85% usage, 942.7 mm WL), then post-GRT `repair_design` died:
`ODB-1211 load pin ...g_madd[5].g_fan32.u_m.genblk1.g_native7.u_native.c2189/A is dont_touch` -> `RSZ-3006` on net
`...u_native.n3623` (r8/r8_do-5_1_grt.RSZ3006.tail.log). Cause: r8 released the SEQUENTIAL kernel cells and their input nets
but left the combinational kernel cells dont_touch, so a released net with a protected load cannot be buffered. A half-release
is structurally unworkable for the resizer. Fix (owner 10-20 09:05: equivalence + strict bind, no native proof): drop the
bind-first kernel dont_touch for good at PRE_CTS (r9/pvm9_release_all.tcl: every dont_touch inst/net under *u_native*,
listed, never restored), then CTS/GRT/route/finish run as a normal tile. r9a = kit CTS (main); r9b = fallback with tighter sink
clustering (size 16, max diameter 30 um) to cut the 82 ps local kernel skew. Both from r6c 3_place.odb in copies bf9a/bf9b.
Audits (PG after global_connect, fanout, seq reach, TT/FF STA, insertion) at 5_1_grt and 6_final. Then equivalence of the final netlist.

## r9 verdict + r10 (HBM-PVM11, 10-21)
- r9a / r9b: 4_1_cts + 4_cts PASS, 5_1_grt FAIL GRT-0116 after 30 extra iterations: overflow 11111 (a) / 9266 (b),
  average usage 28.4% / 28.2%, wirelength 1.87M / 1.85M um vs r8 0.94M (r8 GRT overflow 0, usage 14.9%).
- Classification: placement legality, not routing capacity. Releasing every kernel net lets 4_1_cts hold repair insert
  17,147 buffers (r8 11,858, 10,642 hold endpoints at margin 30) on intra-kernel paths; the 16 EXCLUSIVE lane fences admit
  only group members, so those buffers are legalised outside their kernel: DPL negotiation stuck at 23,540 violations
  (r8 11,707), HPWL 838k vs 716k, congestion at the fence edges / SRAM E+W faces (x 240-280 and 80-100 um, 3,616 g-cells
  over capacity-0 macro area), sources mostly resizer nets (net*) and u_native kernel nets. Tight clustering (r9b) only -17%.
- r10 (structural): r9 + the lane fences dropped at PRE_CTS (r10/pvm11_drop_fences.tcl, after the kernel release).
  The fences only serve global placement (kernel-pin nets local); after 3_place the kernels stay where placed and DPL can
  legalise CTS/hold buffers beside their sinks. Dry run on the r6c 3_place.odb: groups=16 regions=16 members=58160.
  r10a = kit CTS (main), r10b = r9b tight sink clustering (fallback), both from r6c 3_place.odb (bf10a/bf10b, ep6).
