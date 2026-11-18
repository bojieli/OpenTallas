# FABLE-CLOSURE-STRATEGY 2026-11-17 21:20 PST (2120): delta on 19:20

Reviewer: CLOSURE-STRATEGY-2120 (Opus, standing in for Fable, out of quota until 11-24). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

## 0. Headline

1. **Splitting the pad tails does not help unless the copies are also sited (V).** QC st_a proof `sle_st_a_v1__cl67389ecd` (epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/{base,split}`, `4_cts_final.rpt`): wns -901.39 -> -912.09, tns -160,939 -> -159,509. The new copy `u_pd2_x_hc1_i_0_u_r0_5` drives one load, `u_u_r0/rs_n_c_p[0]`, but still has 1,585 ps of wire at 5,017 ps slew. The KV pv_v12 split kit (epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12`, still in GPL) has no anchor or relay-site knob for the `u_pd*_c*` copies in `config.mk`, and its GPL already added 153,615 buffers on 40,945 nets. It will show the same result. This is now the largest lever: about 27 QC and KV types depend on it.
2. **S81 has no die GRT result, although both proto arms "RAN exit 0" (V).** On epyc10, in `s81-die-r3-proto/s81/{d7w,d8c}`, the kit built, then all three GRT arms died in under 1 s at `mk_combo_kv.py: ModuleNotFoundError: No module named 'die_sta'`, because `OT_DIE_PLAN_TOOLS` is unset. TTA_TT and TTA_FF have no `arr_*.txt`, and CHAIN_DONE still ran. The s_4N_L1 congestion question is unanswered.
3. **HEAD hd_lep0N p2 is dead at global place since 20:19 PST, and no lane has posted it (V).** `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` stops with `OT_CLAND no mapped cells found under u_core.u.g_plw.g_s\[0\][/.].*`. The cells do exist in `1_synth_odb.v` (`\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_`), so the CTS read HEAD-LEP0N-OPUS is waiting for will never come.
4. **H17 serdes reached DRC 0, fill and fillcell, then stopped at `6_report` (V):** `[ERROR ODB-0420] tmg_conn::detachTilePins: tilepin inside iterm` (final_report.tcl:13). The r644 in-pin segment ends inside the pin shape, and RCX/tmg_conn refuses it.
5. **Other technical place-stop classes in the last 12 h (V, `kit_wave_state.json`):**
   - S81 `OT_VPW_BANK distance exceeds 100um` on leaf t10, t45 and t74 (+1), up to attempt a9;
   - S81 `explicit FT site is not on a row/site` on t7 and t53;
   - `PLACE-HPWL` divergence on hd_tile (2.26x) and S81 leaf t37 (1.40x);
   - QC GPL-0305 on slw_st_b_v1__cle6023ec2;
   - `SPLIT-NEEDED` over 400 k cells on 7 QC types (hc0, hc2, st_b, 453 k to 487 k) and on kv3_hub_Wo (528 k).

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | QC, KV | Site the split tail copies at their consumer pins | QC st_a 11 types (44 hard rows); KV PV 16 types; PC bin-to-core | KV-HG-OPUS (r657 code), TAIL-REPL (st_a proof) |
| 2 | S81 | Get a real die GRT (fix the proto env), then D8d = re-sited stations + lattice snap + reset write-back + ist_rows | die route verdict; 8 G0 geometry ERRORs; col_h9_r1; t1/t15 serdes reset | S81-DIE-R3 |
| 3 | HEAD | hd_lep0N CLAND stage-row stop; lep_pair vE28 contract; related-pair windows | hd_lep0N, then hd_mesh and the last 3 HEAD types | HEAD-LEP0N-OPUS, HEAD-PLAN-R4 |
| 4 | all | Hold repair must reach the asked margin: no area-guard cut below the target, repair last, in the gate RC frame | S81 svc smc/hslice, S81 col family (236 items), QC N3 at 40 ps | CAPSKEW-ECO, S81-TYPES-R3 |
| 5 | S81 | Pad abut segment ends at the pin edge, not inside it (ODB-0420) | H17 sign-off, then 11 serdes types | S81-SERDES-GEN, S81-FIX-OPUS |
| 6 | S81 | Leaf place stops: VPW_BANK distance, FT site off row, CLAND band | about 8 to 10 leaf types | S81-TYPES-R3 |
| 7 | QC | N4 content: st_a flt_bank 2 stations, clk_t115 split, tt_ctlm pipe stage, coll_core offsets measured before apply, plus the >400 k splits | st_a, cbn_q00, tt_ctlm, coll family, 7 split types | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | KV | D22 = 612 stations + facegrow + tap spill + tail split **with siting** | PV family, kv3_hroot/pv_v2/v2n band (5), pc pilot4 caps | KV-HG-OPUS, KV-R3 |

### Lever 1. Site the split tail copies (QC st_a, KV PV)

**Evidence (V).**
- In the st_a split kit, every `rs_n_c_p` end keeps its wire and slew: base 1,589 ps / 5,030 ps, split 1,585 ps / 5,017 ps.
- The bind and LEC are correct: 35 of 803 pads were split, giving 140 copies and +123 flops (R, TAIL-REPL 20:33).
- KV pv_v12: the split bind gives 7,044 copies and +19,382 flops (R). The kit has `PRE_DETAIL_PLACE_TCL = face_flops_release.tcl` only, with no anchor for the copies (V).

**Root cause.** r657 `land_pad_tail_split` changes the netlist only. GPL places each copy flop at the timing/wirelength optimum of its fan-in, which is the shared D-K trunk near the clock tap region (clk_t386 in st_a). The copy-to-pin hop stays at the full spread.

**Fix.**
1. KV-HG-OPUS: bind writes a sites record for every copy, at most 20 um from its consumer-core pin centroid (for QC st_a, the soft-leaf centroid from TAIL-REPL's 617dd4d9). The shared trunk stage goes at the pin-spread centroid.
2. The kit loads that record FIRM at 3_3, using the same anchor path as r650 `core_input_anchor.tcl`, so that both dies use one mechanism. A two-pass `type_relay_sites.py` regeneration is the slower fallback.
3. K from the r657 formula keeps each hop at or under `hop_um` 380.

**Acceptance.** On the st_a proof DB, `rs_n_c_p` wire under 150 ps and CTS wns better than -250. Then the same test on pv_v12 (before: reg-to-core -1,197).
4. TAIL-REPL runs the st_a proof as soon as the anchor exists. Do not wait for N4.

### Lever 2. S81 die GRT and D8d

**Evidence.**
- Lever-2 proto chain (V): `CHAIN.log` shows KIT 0, three GRT arms, each `mk.log` with `ModuleNotFoundError die_sta`, TTA 1 FileNotFoundError, CA_CHAIN 1, STA_DROOP 1, then `CHAIN_DONE`. `ot-run` reports exit 0. The same applies to d8c.
- D8c (R, FABLE-PD-S81-2100):
  - moved macros cover 2,296 ft station bits in 8 slots;
  - t1 `rst_rl_170` is gone and t15 `rst_rl_244` is 690 um away;
  - `ist_rows.py` and `cut_census.py` are not in the tree;
  - the 12 moved origins are off the 8.64 um lattice.

**Fix.**
1. S81-DIE-R3: in `proto_die.sh`, export `OT_DIE_PLAN_TOOLS=<tree>/tools/die_plan`. Make the chain exit non-zero when any GRT arm has no `arr_*.txt`. Rerun the D7w arm now; it is the applied plan and needs no D8.
2. Read three things from that run:
   - total overflow;
   - the gcell map over s_4N_L1 (y 19.77 to 21.0 mm), and over s_5S_L0, where the new worst cut segment (0.577) sits;
   - routed clock skew on related pairs.
3. D8d:
   - choose each core's dy so that it clears both the cut line and the station rows of that slot, as a multiple of 8.64 um;
   - otherwise re-site the 8 slots' stations with the generator;
   - build with r666 + gen4 (bind, then `local_reset_writeback.py`, then G0);
   - carry r652 `ist_rows` and r645 `cut_census`;
   - expect G0 with 0 geometry ERRORs, bind rc 0 and LATCHECK 873/873.
4. Run the D8d die GRT A/B against D7w before D8d applies. If the D7w die GRT shows s_4N_L1 below 100 % with no overflow, D8 is not needed for the route, and only the station and reset fixes matter.

### Lever 3. HEAD hd_lep0N

**Evidence (V).**
- p2 failed at 3_3 with the `OT_CLAND` error above. `landing_placement.tcl` lines 323 to 325 hold three `stage:plw_s0..s2` rows. The error is raised when `hit` stays 0 (line 2492).
- The cell names exist in the netlist, so either the escaped regex does not match the ODB names, or every flop was already in `cland_done` from an earlier entry (P: in that case the `continue` leaves `hit` at 0). Both are tool defects on a placement hint, not a plan fault.
- lep_pair vE28 (epyc9 `head-lep0n-opus/lep_ve28`) is in 5_1 GRT hold repair: `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03 at margin 10. Insertion is 586 ps against a 450 target (R).
- tree2 die GRT is at extra iteration 11/50 with a 75 % derate on M4 to M7, so it is congested. Result not yet available.
- tree2 placement-RC clock STA: 195 lep0N taps span 62.9 ps TT (R, 20:22); the kit SDC gives each port a 89 to 96 ps window.

**Fix.**
1. HEAD-LEP0N-OPUS: in `landing_placement.tcl`, count already-placed members as a hit, or test the regex on the 3_2 ODB with `get_cells`. Relaunch p2 from 3_2, not from synth.
2. Replace the stale rp21x per-port windows with related-pair windows from tree2 (`die_sta_related --kit-window-related`). That is the only cure for the cross-tap hold class; more margin is not.
3. HEAD-PLAN-R4: re-derive the four pair-clock tap offsets from the vE28 `clock_contract.json` (about 586 ps) when it signs.
4. When tree2 GRT ends, post the overflow and the gcells for x 880 to 1160 and 1230 to 1472.
5. hd_tile PLACE-HPWL (2.26x) is the same divergence class as S81 t37 and QC cle6023ec2 (lever 6, item 3).

### Lever 4. Hold repair that reaches its target

**Evidence.**
- (R, S81-FIX-OPUS 20:30) smc mm3b r2r FF -10.62 and hslice -5.92. The ORFS hold guard cut HM from 30 to 19 (a projected +8.9 util points over the 8-point limit), then MET-FIRST repaired at HM 0 and stopped.
- (V, 19:2x) The same order problem exists on QC: on slw_sc_v2 the GRT hold repair ends at +0.15, then TT setup repair runs after it.
- (R) Col item_env `OT_HOLD_FF_MARGIN_PS` 10 replaces the die key (25) and the family floor (`_fam = None if _hm`).

**Fix.**
1. CAPSKEW-ECO:
   - when the area guard trips, lower the margin no further than the gate target (0 plus the 20 to 40 ps routed loss already measured), and log it;
   - never fall back to HM 0;
   - run the final hold pass after the setup repair, in the gate RC frame.
2. The mm4 runs (guards off) are the A/B for this. If they sign, make guards-off the svc default.
3. S81-TYPES-R3: the 10 -> 25 change on all col item_env rows. Confirm `OT_HOLD_FF_MARGIN = 25` in the first col `config.mk`.

### Lever 5. Serdes: ODB-0420 at finish

**Evidence (V).** H17 `6_report.log:27` shows ODB-0420 after `5_3_fillcell` and `6_1_fill` passed. Route was DRC 0 at iteration 5, with 1,089 pad nets carrying the r644 segment (R).

**Root cause.** The hook draws a wire whose endpoint lies inside the macro iterm's pin shape. tmg_conn, which RCX and `estimate_parasitics` use, rejects a tile pin inside an iterm.

**Fix (S81-SERDES-GEN).**
- Preferred: end the segment exactly on the pin boundary (the pin-edge point on the access layer), so tmg_conn sees a normal connection.
- Alternative: the strip-before-RCX hook in test, but it must not leave these nets "unrouted" for RCX.
- Prove it on the H17 `6_1_fill.odb` copy; do not route again.
- Then run t13 from the D6z generator (running, epyc10 unit 306723) with the fix, and the TAP-CAP-CENSUS on the first CTS of each of the 11 types.

### Lever 6. S81 leaf place stops

**Evidence (V).** In `autopilot/kit_wave/s81_ot_s81sl_leaf__t10_*/a9` the error is `OT_VPW_BANK distance exceeds100um at u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0[0]`. The same error appears on t45 and t74 at attempts a4 to a9. Leaf t7 and t53 stop on an FT site off a row (`ft3,1,0 82.9376 176.8544`).

**Root cause (P).**
- OT_S81_VPW_BANK (r-strip, opt-in) clusters the VPW flops beside "both real SRAMs" and fails hard when the bank is over 100 um away. In lf4 sub-leaves the SRAM it chooses is not in the same sub-leaf.
- The FT site x is not snapped to the 0.054 um site grid (82.9376 is off-grid).

**Fix (S81-TYPES-R3).**
1. VPW_BANK chooses the SRAM of the same `u_u_lfN` instance. Under R-MINIMAL, a bank over 100 um gives a WARN and the flops are left to GPL.
2. The generator snaps the FT station xy to the row/site grid.
3. The PLACE-HPWL stops (t37 1.40x, hd_tile 2.26x, QC cle6023ec2 GPL-0305) get one retry of the converged DB without region guides and with the r496 td 0.25/0.30 GPL setting, not another unchanged relaunch.

### Lever 7. QC N4 content

**Evidence (R, QC-N-OPUS 19:5x).**
- st_a `flt_bank` r2 -> r0 runs about 1,000 um. The r1 -> r0 (482 um) and r2 -> r1 / r3 -> r2 (516 um) pairs are also over 405 um.
- clk_t115 has two clusters 200 um apart (W 330 to 359 ps, E 321 to 326 ps). clk_t50 is one hop latch: no split.
- tt_ctlm: 949 ps of data over 31 cells, about 700 ps of it logic. The period is 833 ps.
- The coll_core and cbn_q00__cldbcda913 clock-chain inputs are gone from every host (R, QC-PLAN-R3 19:48).

**Fix.**
1. QC-PLAN-R3, in N4:
   - 2 stations on r2 -> r0;
   - check the three other flt_bank pairs for live nets and add stations where they are live;
   - split clk_t115 at about (600, 2390) and (820, 2470);
   - add 1 pipeline stage in tt_ctlm `u_core`. A region alone removes at most about 250 ps of wire against a 760 ps budget for 700 ps of logic, so it cannot close.
2. QC-N-OPUS: regenerate the clock-chain inputs from the N3 plan before N4 applies. coll_core is `clock.source`, so all 43 new taps start unmeasured.
3. QC-TYPES-R3 with QC-PLAN-R3: the 7 types over 400 k cells need a partition split in N4. The +1,032 head-pad flops on hc in N3 make them larger, not smaller.
4. Carry the halo fix `claude/qc-pad-chain-halo-1117` into N3 by a tools refresh before the cb kits generate. Without it the third HB4 and the pipe register sit inside the r648 strip.

### Lever 8. KV D22

**State (R, KV-HG-OPUS 20:48 to 21:07).** D22 is composed on plan f9eeac833487 with:
- 189 PV stage rows and 612 stations (+99.5 k flops, +612 cycles on 187 lanes);
- `tap_spill_um 600` on 3 kv3_pc_v1 (this answers pc pilot4: 10 taps over the 1,200 cap, clk_t4 at 9,664);
- 6 raw-branch band rows;
- tail split `^kv3_pv`.

The tools refresh is applied (src `_t2509079`, with r641 and r657). Facegrow fix b917b3be is READY for the writer-face band class (kv3_hroot, pv_v2, pv_v2n, pv_v6: 5 rows). The build is moving to epyc7 because epyc10 scratch is full.

**Fix.**
1. Add lever 1 siting before the D22 kits generate. Without it, D22 PV kits repeat the st_a -912 result.
2. Merge b917b3be into the D22 tools.
3. On the first pc kit, run `tap_cap_census.py` on its CTS log and expect no tap over 1,200.
4. kv3_hub_Wo (528 k) needs a split row in D22, or it stays REFUSED.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| QC st_a tail split | epyc9 `tail-repl-qc-kit/{base,split}/run/reports/.../4_cts_final.rpt` | wns -901.39 / -912.09; tns -160,939 / -159,509; copy `u_pd2_x_hc1_i_0_u_r0_5` -> `u_u_r0/rs_n_c_p[0]`, slew 5,017.47, wire 1,585.02 |
| KV split kit | epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12/{config.mk,3_3_place_gp.tmp.log}` | no copy anchor; RSZ-0038 153,615 buffers in 40,945 nets; still in GPL (unit 229217 active) |
| S81 die GRT proto | epyc10 `s81-die-r3-proto/s81/d7w/{CHAIN.log,grt_*/mk.log,tta_TT.log}` | `ModuleNotFoundError die_sta` in all 3 arms; no `arr_TT.txt`; chain reported done; d8c the same |
| hd_lep0N p2 | epyc9 `fable-fix-head-lep0n/p2/hd_lep0N/{run_cts.log,landing_placement.tcl,1_synth_odb.v}` | GPL stop at 04:19 UTC (20:19 PST), OT_CLAND `g_plw.g_s[0]`; flop `\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_` present |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/.../5_1_grt.tmp.log` | `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03, margin 10, repair in progress |
| tree2 die GRT | epyc9 `head-die-r/nf15e_e10/hr4/clock_rs8/tree2/kit/grt/grt.log` | derate 75 % on M4 to M7, extra iteration 11/50 at 05:10 UTC |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.log` | ODB-0420 tilepin inside iterm, after fill |
| wave FAIL rows, last 12 h | intel2 `autopilot/kit_wave_state.json` | technical: VPW_BANK 4 (S81), FT off-row 2, PLACE-HPWL 2, MPL-0041 2 (kv_leaf t1/t3), GRTM edge_outline 3 (c1x_C t7/t9, slw_sc_v2), MPL-0034 2 (st_a), GPL-0305 1, SPLIT-NEEDED 8, KV CLAND band 5 |
| failure_breakdown 21:10 | intel2 | signed S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |

## 3. Stop list (the 19:20 list stands, plus these items)

1. Do not relaunch any tail-split kit (QC st_a, KV PV, D22) without copy siting. It is proven a no-op: -901 -> -912.
2. Do not read an `ot-run ... exit 0` from `proto_die.sh` as a die GRT result. Check that `arr_*.txt` exists.
3. Do not change region-guide box size or registers per region for GPL-0305. It was proven not to be the lever (QC-TYPES-R3 19:44).
4. tt_ctlm: a region-only fix cannot close 700 ps of logic. No clk_t50 split (one hop latch).
5. HEAD: no tree re-cut for lep0N (63 ps whole-set spread). No hd_lep0N relaunch from synth. No hold margin increase.
6. H17: no new route attempt. The defect is at finish (ODB-0420); test the fix on the routed/fill ODB copy.
7. S81: no D8d apply without a die GRT number on D7w. No hand edit of `rst_rl_N`. No VPW_BANK relaunch unchanged (t10 is at a9).
8. QC N3 cb kits: no generation before the halo fix is in the tree.
9. svc: do not raise the hold margin again while the area guard still cuts it. Fix the guard first (lever 4).

## 4. Not checked

- The S81 D8d build. I found no d8d directory on epyc8 or on the hub.
- smc/hslice mm4 results.
- The N3 bind result.
- The kv3_pv_v12 split kit past GPL.
- The tree2 GRT overflow numbers.
- Whether the hd_lep0N CLAND miss is the regex or `cland_done` (both are P).
- The VPW_BANK root cause beyond the error text (P).
- The 4 KIT_PREFLIGHT issues on dsdv_slice_c1x_C (14 rows; the class may be technical).
