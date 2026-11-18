# FABLE-CLOSURE-STRATEGY 2026-11-17 19:20 PST (1920): delta on 17:20

Reviewer: FABLE-CLOSURE-STRATEGY-1920 (Fable). Read-only, no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
The intel2 root disk read 0 B free at 19:10 and 32 GB free at 19:19, so this is written to the hub as asked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal or estimate, not measured.

## 0. Headline

1. **The 17:20 hold lever is approved and merged but is in no kit (V).** `tools/die_plan/hold_margin_family.py` (r641) is absent from every live or about-to-apply tree: HEAD `..._nf15f_d2`, QC `..._s4q9n1b_d2` and `..._s4q9n2b_d3`, KV `..._d21b`, S81 `..._d6z_1117_work`. The same three trees on epyc9 have no r650 pad siting and no r644 hook. Every kit launched tonight repeats the post-route hold ECO path, and every cb kit on N2B stops again at RSZ-3006.
2. **New class, 6 of 6 QC st_a kits at CTS (5 on N1B, 1 on L2), posted by no lane (V): hard-core boundary nets.** TT setup after CTS and repair -266 to -671 ps, 2,987 violating ends per kit, tns about -103 k. Three shapes: one pad-chain tail driving the same pin on all four hard station rows over one unbuffered net; hard core to hard core direct; hard core to a boundary register. It is the same root cause FABLE-FIX-KV-HG-CHAIN measured on KV PV at 19:10 (pad tail fans out to 8 cores). N3 and N4 as scoped do not touch it.
3. **KV PV is not a siting problem (V on the chain-proof output).** kv3_pv_v12: 1,073 pad chains fail at the tail; 1,822 chains in three other families cannot meet 405 um even with ideal spacing, so they need stages in the plan. TT wns -1,197, tns -4.60 M. D22 as described (clock band, pc keepout, pad siting) will not close PV or PC.
4. **tap[0] pad class: explained by unsited pads on the one end I could open, with about 100 to 150 ps left after siting (V path, P estimate).** Three HB4 take 488 ps in a 430 ps window because they sit apart; see section 3.
5. **Cross-tap skew: no die clock change on QC (V).** On 11 N1B kits at CTS the cross-tap class is 37 to 2,267 ends at -27 to -83 ps; pre-GRT hold cells are 0.5 to 2.7 % of instances where the pass has ended (4.3 % worst on L2). HEAD has no NF15f number yet; see section 3.
6. **Not finished at 19:20:** H17 route-only r3 (iteration 0 at 50 %, 47,299 violations); no NF15f hd_lep0N or hd_mesh kit directory exists on epyc8, epyc9, epyc10 or intel1; N2B publish gate; D21b replication; no D6z col kit past placement that I found.

## 1. Outcome of the 17:20 levers

| 17:20 lever | outcome at 19:20 |
|---|---|
| 1 hold margin at GRT | r641 merged (40 ps QC / KV / HEAD, 15 ps cores) (R). In no tree (V). S81 type kits are excluded by the rule itself: `FAMILY_PS` lists three dies, the file comment says "S81 runs its own 10" (V). Of 415 S81 `item_env` rows 76 carry `OT_HOLD_FF_MARGIN`; S81 `gen_args` has `--hold-ff-margin 0` (V, `autopilot/kit_wave.json`). 6 QC L2 kits signed through the post-route ECO (R) |
| 2 pad / relay chain siting | Wrong as the main fix for KV. R-REACH-5 moved 18 of 1,342 chains on pv_v12 and made wns worse; the long hop is the tail fan-out (R, output V). QC: 5 one-cycle hops became N3 (2 stations) and N4 (3 landing-contract stations) (R) |
| 3 hd_lep0N fault flag | The -3,897 ps kit was NF13a, not NF15d2r1; NF15f has 174 registered stations on those chains (R). My 17:20 event label was wrong. No NF15f kit exists to confirm on |
| 4 tap split by extent | coll_core: 43 taps at radius 230 um, cap 4,800, farthest sink 227 um, estimated insertion <= 238 ps against 677 (R); moved to N4 because it re-solves the landing contract. Serdes cap 1,700 in D8 (R) |
| 5 S81 die | D6z applied 19:01 (R). Cut census found 10 over-limit segments on 5 lines; D8 has 12 rigid y moves, census after = 0 segments over 0.58, t43 0.923 -> 0.513 (R). t51 native_w repointed to signed rc51f in D7w (R) |
| 6 cbn_q01 | Stretch fixed by r648 (R). Next stop RSZ-3006 on the tap[0] pad chain, fixed by r650 (R). Kit then reached CTS (V) |
| 7 svc shell | no new data read |
| 8 PHY types | H17 r2 reached DRC 0 at iteration 5, then "unrouted nets" on 1,089 pad-on-macro-pin nets; r644 adds the in-pin segment; r3 running (R, progress V). Generator parts 1 and 2 merged as r638 / r643; h-form PASS not posted (R) |

## 2. Evidence I opened this round

Job dirs are `<host>:/srv/opentallas-scratch2/claude/ot-jobs/<item>-route-*/work` unless a path is given.

| item | file | result |
|---|---|---|
| Trees | `kw45/<tree>/tools/die_plan/{hold_margin_family.py,pad_abut_wire.tcl,core_input_anchor.tcl}` on epyc9, epyc10 | hold_margin_family.py missing in all 5 trees named in headline 1; no `hdly_lk` siting and no pad_abut_wire in the HEAD and both QC trees |
| r641 rule | intel2 `rt/current/tools/die_plan/hold_margin_family.py` | `FAMILY_PS = {qwen_compute: 40, qwen_kvsys: 40, s81_head: 40}`, `CORE_PS = 15`; GRT margin = max(caller, family); setup guard stops the GRT hold repair below min(setup before, 0) |
| QC st_a, 6 kits: 5 N1B, slw_st_a_v1 on L2 (epyc8, epyc9) | `tt_setup_repair.log`, `pregrt_ff_hold.log`, `4_cts_final.rpt`, `1_synth_odb.v` | TT setup after repair: sle_st_a_v1__cl989804f6__cl18eece69 -671.1; __cled3c1d7b -654.4; sle_st_a_v1__cl67389ecd -580.7; slw_st_a_v2__cl9f076a5c -569.1; slw_st_a_v1__clb036e152 -568.7; sle_st_a_v2__pv4242de79 -266.1. tns -102.6 k to -110.2 k. `RSZ-0094 Found 2987 endpoints`, `RSZ-0062 Unable to repair` |
| st_a path shape 1 | sle_st_a_v1__cl67389ecd `4_cts_final.rpt` | `u_pd5_x_hc1_i_3.q` -> BUFx24 -> `u_u_r0/rs_n_c_p[3]`: one net, 149.8 fF, wire delay 1,589 ps, slew 5,030 ps, core setup 106.9. Netlist: the same net feeds `rs_n_c_p` of `u_u_r0`, `r1`, `r2`, `r3` (4 instances of `qfd_dv_s8_station_tail1_h17_n9_s10`). -901 before the TT repair |
| st_a path shape 2 | slw_st_a_v2__cl9f076a5c | `u_u_r2/flt_bank_o[0]` -> `u_u_r0/flt_bank_i[0]`, core to core, no cell: core clock-to-output 466 ps, wire 1,015 ps on 116 fF, core setup 120.7. slack -569.1 |
| st_a path shape 3 | sle_st_a_v2__pv4242de79 | `u_u_r3/nb_od[22]` (clock-to-output 436 ps) -> 25 buffers, 806 ps -> `u_bout_x_fe_o/q[216]`. slack -342.5 |
| QC N1B at CTS, 11 kits | `pregrt_ff_hold.log` class lines, `4_1_cts.log` `OT_TAP_BALANCE` | cross_tap ends / ws: coll_s 445 / -28.9; sle_sc_v1 37 / -27.3; st_a 103-228 / -35.9 to -83.3; slw_fe_v1 170 / -74.8; slw_fe_v2 2,267 / -67.6; tt_ctlm 1,461 / -40.7; cbn_q00 1,296 / -55.2. same_tap worst -85.8 (slw_fe_v1, 265 ends). port_in 3 to 3,817 ends at -143 to -179 (advisory). hold cells 1,573 to 5,315 of 179 k to 305 k. Tap means 206 to 346 for a 250 target; st_a kits have one tap at 307 to 346 |
| QC L2 for comparison | slw_sc_v2, slw_stm_v1, coll_core (epyc8) | slw_sc_v2 cross_tap 1,278 / -110.7, 8,998 cells of 447 k; slw_stm_v1 1,628 / -60.4, 20,297 of 471 k (4.3 %); coll_core 4,186 / -453.8, 18,477 cells. slw_sc_v2 `run_route.log`: GRT hold repair start ws -9.53, 37 ends, margin 0 -> +0.15 with 32 buffers, then `OT_TT_SETUP_REPAIR` 13 cells |
| QC other N1B setup | same logs | tt_ctlm TT -150.9, tns -57.7 k (75 cells added, not closed); cbn_q00 -49.7, tns -12.4 k after 1,914 cells (from -309.3) |
| cbn_q01 N1B pilot at CTS | epyc9 `/srv/opentallas-scratch2/claude/qc-types-r3-lane/n1b_cbn_q01/run/reports/.../4_cts_final.rpt` (18:33 PST) | worst -200.24, tns -277.1: `u_pc_nk_u_t_0_2_tap.q[0]` -> BUFx6f -> INVx1 -> 3 x HB4xp67 -> `u_t02/tap[0]`. HB4 delays 164.2, 176.7, 146.6 = 487.5 ps at input slews 110 to 217 ps and loads 7.5 to 14.2 fF. Launch clock at 144.1; core clock `clk_c0` source latency -410.3; core setup 212.0; required 634.9, arrival 835.1 |
| cbn tap tables | cbn_q01 and cbn_q00 `4_1_cts.log` | cbn_q01: tap means 173 to 428, 18 empty taps; `clk_c0..c3` 412 to 428 (one sink each, the tile cores); `clk_t50` mean 184, range 155 to 354 on 1,200 sinks. cbn_q00: `clk_c0..c3` 398, 434, 446, 493; `clk_t115` 330 (316 to 402), 1,200 sinks; 28 empty taps |
| KV chain proof | epyc10 `/srv/opentallas-scratch2/claude/fable-fix-kv-hg2/chainproof/kv3_pv_v12/reach/chainproof/out/{before,after}_{chains,sta}.log` | before: wns -1,197.5, tns -4.598 M. Chains over 405 um / chains (ideal spacing still over): `u_pd.r` 1,079 / 1,342 (0), 1,078 at the tail, tail kind core 1,280; `u_bin.q` 1,773 / 2,238 (150), 1,734 mid-chain; `u_bout.q` 1,669 / 2,312 (774); `u_vport.d_q` 1,057 / 2,048 (896); `u_ist.q` 363 / 916 (0). After R-REACH-5: `u_pd.r` 1,073, all other families unchanged, wns -1,986.9 |
| Wave config | intel2 `autopilot/kit_wave.json` | every die has `--hold-ff-margin 0` in `gen_args`; S81 76 of 415 item_env rows with a margin; QC, KV, HEAD 0 rows |
| H17 r3 | epyc9 `fable-fix-s81-serdes2/H17/serdes__t13/gen/serdes__t13/run/logs/.../5_2_route.tmp.log` | iteration 0: 24,591 (20 %), 29,295, 47,205, 47,299 (50 %) |
| failure_breakdown | intel2 `~/coord/tools/failure_breakdown.py`, 19:11 | signed types: S81 42 / 394, HEAD 23 / 26, QC 10 / 130, KV 6 / 56. Technical rows: KV CLAND ring band 3, KV detail route error 1 (kv3_io_cor_v1), QC waits on child core 12. The rest of the rows are flow classes |

Not opened: N2B, N3, D7w, D8, D21b trees and gates; the S81 cut census itself; any col kit on D6z; any NF15f kit (none exists); the HEAD NF13a job dir (no longer on epyc10); sle_sc M5 EOL report; the GPL-0305 log; any die GRT or die STA run.

## 3. The three questions

**(a) Is the tap[0] pad class fully explained by unsited pads?** On the end I opened, yes for the size of the miss, with a thin result after the fix.
- Measured (V): the path has 430 ps between launch (144 + 61) and required time (635), because the tile core is clocked 410 ps early and has 212 ps setup at `tap[0]`. The three HB4 take 488 ps. Each runs at 147 to 177 ps because its input slew is 110 to 217 ps and it drives 7 to 14 fF of wire to the next pad (73 um apart, R).
- Estimate (P): sited 2 to 4 um apart, slews fall to about 30 to 40 ps and an HB4xp67 runs at roughly 60 to 70 ps at TT, so the chain is about 190 to 210 ps and the end lands near +80 to +100. That does not reach the family's own acceptance line (TT >= +60 and hold >= +50) with much room, and it is placement RC.
- Not explained by siting: the entry cells. `_81681_` is an INVx1 driving 10.7 fF at 106 ps output slew (54 ps); r650 sites the pads and the pipe register, I did not check that it resizes or removes the buffer and inverter in front of the first pad.
- I could not match the four values in the brief (-282, -178, -96, -69) to a file; the 18:33 report has one tap[0] end at -200.2. The other negative end in that report (-150.3 at latch `u_lk_nk_u_t_1_2_n_b/q[495]`) is in the hold section, before hold repair.
- Check on the first r650 kit: HB4 delay per stage, slew at `tap[0]`, TT and FF slack at the four pins, after CTS and again after route.

**(b) Does cross-tap skew need a structural clock change beyond the hold margin?**
- QC: no (V). Cross-tap worst -27 to -83 ps on N1B, pre-GRT hold cells 0.5 to 4.3 %, taps within 250 +/- 50 except named outliers. The routed 105 to 118 ps pairs (hc0 t104 / t110, hc2 t124 / t58, sle_hc2 t121 / t110) (R) are three tap pairs, a tap-pair assignment in those types, not a tree change. Exceptions that are structural and already owned: coll_core (N4). Exceptions not owned: cbn `clk_t50` and `clk_t115` (a 1,200-sink tap with a 199 ps range inside it, or 80 ps over target), st_a taps at 307 to 346.
- HEAD: undecided, no data. NF13a had 25,840 cross-tap ends at -194.5 and the 40 ps cross-tap guard alone added 21,737 of the 76,299 cells (R). A cross-tap worst of -194 is four times the tap tolerance, so that tree was out of balance; margin does not cure that and its cells land in the corridor windows that hold the 367 unassigned nets. Decide on the NF15f pilot with two numbers: tap mean spread after the last `OT_TAP_BALANCE` iteration, and hold cells as a share of instances. P criterion: spread over 100 ps or hold cells over 8 % means re-cut taps along the zero-logic chains before GRT; under both, the 40 ps margin is enough.
- KV: pv_v12 had 7,892 cross-tap ends at -217.6 (17:20, V then). That number comes from stacked chain stages and will move with lever 2; do not re-cut KV taps before it.

**(c) Biggest unaddressed technical risk per die**
- S81: routed hold on the col family. 236 col items run a GRT margin of 10 on 76 rows and 0 on the rest, and S81 is outside r641. The measured loss between GRT repair and the routed gate on QC is 23 to 42 ps, and S81 svc cores landed -5 to -11 at margin 0. No routed col kit exists to compare. Second: no die GRT has ever run; the cut census is a track model.
- HEAD: hd_lep0N on NF15f has never been placed. The lep_pair core has to be re-signed in the vE form (777.6 x 492.48) and bound with its measured insertion; the pilot's CTS numbers are not valid for hold at `g_pp[*].u_pair` before that.
- QC: the st_a hard-core boundary class (lever 2), 2,987 ends per kit, in no event.
- KV: PV and PC need pad-tail copies and plan stages (levers 2 and 3); D22 does not carry them.

## 4. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all | get r641, r648, r650, r644 into the trees that generate kits; S81 col margin | every routed kit; 18 cb types | QC-PLAN-R3, HEAD-PLAN-R4, FABLE-FIX-KV-HG, S81-DIE-R3, CAPSKEW-ECO |
| 2 | QC, KV | hard-core boundary nets: per-core copy of the last pad stage, register on core-to-core buses | QC st_a (11 types, 44 hard rows), KV PV and PC families | WAVE-FLOW-R2 (generator), QC-PLAN-R3, FABLE-FIX-KV-HG |
| 3 | KV | D22 scope: plan stages for 1,822 chains, evening for `u_bin` / `u_bout` / `u_vport` / `u_ist` | KV PV family (and PC bin-to-core) | FABLE-FIX-KV-HG, KV-R3 |
| 4 | QC | cb family: r650 pad chain result, cbn tap outliers | 18 cb types | QC-TYPES-R3, FABLE-FIX-QC-N |
| 5 | HEAD | NF15f pilot read before volume; lep_pair vE | hd_lep0N, hd_mesh, then the 3 unsigned HEAD types | HEAD-PLAN-R4, HEAD-TYPES-R4 |
| 6 | S81 | D8 cut moves, then a die GRT prototype on the worst cut | 10 segments on 5 cut lines; die route | S81-DIE-R3 |
| 7 | QC | N4 coll_core 43 taps + 3 landing-contract stations; tt_ctlm | coll family, su_l1, sc_v1, fe / hc / st_b shared hop | QC-PLAN-R3 |
| 8 | S81 | serdes: H17 r3 to sign-off numbers, then t13 from the generator | 11 serdes types | FABLE-FIX-S81-SERDES2, S81-SERDES-GEN |

### Lever 1. Approved fixes are not in the generating trees

Evidence (V): headline 1 and section 2 rows 1 to 2 and the wave-config row.
Root cause. A kit carries a knob only if its die tree's `tools/` has it. HEAD NF15f was built on main 8569788b, QC N1B and N2B_d3 on rt 1e0504fe, KV D21b on main 24c7347c; all predate r641. N3 has them (R) but is hours away, and N2B applies first.
Fix.
1. QC-PLAN-R3: build N2B as `_d4` on rt d9bbb638 tools before its apply (FABLE-FIX-QC-N's handoff has the 5-minute link-delta command), or run a tools refresh right after the apply and before the wave launches rows. Otherwise all 130 QC types launch once more without the margin and the 18 cb types stop at RSZ-3006.
2. HEAD-PLAN-R4: tools refresh of `..._nf15f_d2` to current main before the hd_lep0N and hd_mesh pilots generate. They have not launched, so nothing is lost.
3. FABLE-FIX-KV-HG: D21b is tools 24c7347c; put the refresh in the D22 build, not a separate event.
4. S81-DIE-R3 with CAPSKEW-ECO: S81 type kits are outside the rule. Set `die.hold_ff_margin_ps` in the D7w or D8 plan (the rule reads it) to 40 for col and slice types, or show one routed col kit at margin 10 with internal hold >= 0 first. The first is cheaper: the padded ends are zero-logic pairs with setup room.
5. CAPSKEW-ECO: the order fix stays needed. On slw_sc_v2 the GRT hold repair ends at +0.15 and `OT_TT_SETUP_REPAIR` runs after it (V); FABLE-FIX-QC-N measured -22.9 and -31.3 at the gate a few lines later (R). Run the hold repair last and in the gate's RC frame. Until then 40 ps leaves about 0 to +17 on the worst kits measured (-40.6, -42).
6. First kit of each die: `hold_margin_family.py check KIT DIE`, then HB4 count, TT on padded ends, routed internal hold.

### Lever 2. Hard-core boundary nets (QC st_a, KV PV, KV PC)

Evidence (V): section 2 st_a rows and the KV chain-proof row.
Root cause. A count-aligned pad chain ends in one flop whose output goes to the same pin on several hard cores: 4 station rows in st_a, 8 `kv3_pv_pair` cores 644 to 1,761 um apart on PV (R). No single site reaches all loads, and the net is left as one wire (slew 5 ns in st_a). The st_a cores also spend 436 to 466 ps clock-to-output and 107 to 121 ps setup at their pins, so a core-to-core net has about 246 ps and a core-to-register net about 390 ps for wire.
Fix.
1. WAVE-FLOW-R2, generator: for a pad chain whose tail has more than one hard-core load, emit one copy of the last pad stage per core (per group of loads within one hop), each sited at its core pin; the stages before it stay shared and are spaced along the trunk. Cycle count is unchanged, so LATCHECK is unchanged. Flop cost on pv_v12 about 1,073 x 7. This is the per-branch form FABLE-FIX-KV-HG-CHAIN named.
2. QC-PLAN-R3: st_a core-to-core `flt_bank_o` -> `flt_bank_i` (r2 to r0) and core-to-`u_bout_x_fe_o` (r3) need a register. First read the plan for the row spacing: if r2 to r0 is over about 250 um, one station on the bus (a latency row, N4 with the other landing-contract edits); if the cores abut, the 1,015 ps wire is a detour and the fix is a routing channel or pin-side. I did not read the geometry.
3. QC-TYPES-R3: the six st_a kits now in GRT are measurement only; do not relaunch unchanged. The two st_a types held for MPL-0034 will show the same class after N2B.
4. FABLE-FIX-KV-HG: PC `u_bin` -> `qkd_kvs_pcc` direct (619 chains, 0 free stages, up to 1.5 mm, 26 or more core pins per bit) (R) is the same fan-out with no stage to copy: it needs the ring-to-bin stations of PC-DELTA item B plus bin copies.
5. The class predates N1B: the L2 kit slw_st_a_v1__clb036e152 shows it (-568.7). Not checked: whether the st_a core clock ports should carry an early offset as the cb tile cores do (`clk_c*` at -4 to +37 in st_a against -410 on cbn). An early core clock would move budget from the output side to the input side; it does not create any.

### Lever 3. KV D22 scope

Evidence (V): chain-proof row. Beyond the pad tails, kv3_pv_v12 has 1,822 chains whose stage count cannot span their distance at 405 um per hop (`u_vport.d_q` 896, `u_bout.q` 774, `u_bin.q` 150, `u_vport.t_q` 2) and 3,037 more that would meet it if spaced evenly (`u_bin.q` 1,623, `u_bout.q` 895, `u_ist.q` 358, `u_vport.d_q` 161) but are not touched by `chain_even.tcl`, whose patterns cover `u_pd` and `u_lpad` only.
Fix.
1. FABLE-FIX-KV-HG: D22 = PV clock-landing band + pc keepout rows + (i) stage rows for the 1,822, with LATCHECK, + (ii) tool refresh carrying lever 2 item 1 and an evening pass extended to `u_bin.q`, `u_bout.q`, `u_ist.q`, `u_vport.*` with the 16-stage cap removed only together with per-branch tails (the cap-lifted run went to -5,085).
2. Size it across the family first: run the chain summary on one kit per PV and PC type from existing placed DBs (the tool is in `chainproof/tools`). pv_v12 is one type.
3. Keep the two PV types with the ft26 N-face band refused until D22 (R).
4. kv3_hub_Wo at 528 k cells and the hroot ring band are unchanged from 17:20.

### Lever 4. QC cb family

1. tap[0] pads: section 3 (a). Acceptance on the first r650 kit, at the four pins.
2. cbn tap outliers (V): `clk_t50` in cbn_q01 has a 199 ps range inside one 1,200-sink tap (152 to 354), `clk_t115` in cbn_q00 sits at 330 (316 to 402). 1,200 is the cap, so these taps are full and cover too much area: same extent rule as coll_core. FABLE-FIX-QC-N: split those two taps in the N4 rows (18 and 28 taps of these types are empty, so capacity exists nearby).
3. cbn_q00 TT -49.7 after 1,914 repair cells from -309 (V): read its worst group after r650 before calling it closed.
4. sle_sc M5 EOL (44) and GPL-0305: I agree with the posted decisions (no abstract change; region-guide boxes of 18 um for 247 cells diverge) (R). Both are per-type or tool items, not family blockers.

### Lever 5. HEAD

1. Pilots have not started (V: no kit dir on any gen host). Refresh tools first (lever 1 item 2).
2. HEAD-TYPES-R4: lep_pair in the vE form with KCRED 28; the 388.8 x 432 signed record cannot bind (R). hd_lep0N's hold at the pair pins is meaningless until the bound view carries the measured insertion.
3. HEAD-PLAN-R4 on the pilot's first CTS: tap spread and hold-cell share (section 3 b), the `u_fault_port` group, tns. Then GRT decides the 367 nets; post the gcell map for x 880 to 1160 and 1230 to 1472.
4. sd9g3 routed result and the die STA on the NF15f clock tree2 were not read this round.

### Lever 6. S81 die

1. D8's 12 rigid y moves are the right kind of fix for macro walls (R: t43 has 1,218 of 1,443 um of M5 blocked). Two checks before bind (P): each moved hard core keeps its clock landing and tap reach (t43 `u_vn.u_a` moves 680 um, t14 `g_ln[6]` 691 um), and the ft stations that pair with the moved cores stay within one hop.
2. After D8, run the die GRT prototype on the s_4N_L1 line. 0.51 on a track model that excludes PG and clock is not a route result.
3. Lever 1 item 4 for col hold.
4. Unchanged from 17:20 and still without an event: c1x_C t7 / t9 `GRTM edge_outline`.

### Lever 7. QC N4 and the remaining setup hops

N3 = tools + 2 internal stations (su_l1 lane7, fw_v1 rd_wi) (R). N4 = coll_core 43 taps + 3 landing-contract hops (R). Add to N4: lever 2 item 2 (st_a) and lever 4 item 2 (cbn taps). tt_ctlm at -150.9 with tns -57.7 k (V) is in neither event; QC-TYPES-R3 to name its worst group.

### Lever 8. S81 serdes

H17 r3 is the first run that can reach finish and sign-off STA. Read from it: DRC with the r644 segments, RCX on them, routed TT, internal hold. The five construction blockers so far were each found one run at a time, so expect one more at finish. The 10 other types wait on a clean generated t13 from D6z (R).

## 5. Stop list (changes; the 17:20 list otherwise stands)

1. Launching N2B rows, HEAD pilots or D21b kits on trees without r641 / r650 and reading their hold or cb results as a test of those fixes.
2. KV: `budgets.r_reach_even` or `r_dly_spread` in D22; lifting the 16-stage cap alone; calling D22 the PV / PC closure event while it has no stage rows and no tail copies.
3. QC: relaunching st_a kits unchanged; treating N3 + N4 as covering every QC setup class; a die clock change for the 105 to 118 ps hc pairs.
4. HEAD: more hold margin as the answer to 76 k hold cells; any hd_lep0N hold conclusion before lep_pair vE is bound.
5. S81: raising `ft_track_frac`; reading the cut census as a die route result; assuming col closes hold at margin 10.
6. All: a relaunch of any kit whose post-CTS TT is below about -250 ps with tns in the 100 k range; route cannot recover it.

## 6. Corrections to the 17:20 report

1. Headline 3 and lever 3 named the hd_lep0N kit as NF15d2r1. It was NF13a (R, HEAD-PLAN-R4 from `kit_rtl_paths`). The fault-flag finding does not apply to NF15f.
2. Lever 2 said KV was "a generator siting fix, not relay rows". Wrong for both halves: siting does not fix the tails, and 1,822 chains on pv_v12 need stages.
3. Lever 6 said the kept station `u_x_1_2` was next to the stretched path; the stretch was inside the moved station `u_x_1_3` and the keep was a false positive (R).
4. The 17:20 review did not look at st_a at all, although one L2 st_a kit was already past CTS.

## 7. Not checked

- That siting brings HB4 delay to 60 to 70 ps; it is an estimate from the slew dependence in one path.
- Whether r650 handles the buffer and inverter ahead of the first pad.
- st_a row geometry and whether the class exists on st_b or other families with several hard rows.
- KV chain counts on any type other than pv_v12; PC numbers are the lane's.
- HEAD NF15f at any stage; S81 col on D6z at any stage; D8 plan contents; H17 r3 beyond iteration 0.
- Whether main at D6z's tool sha contains r641 at all (S81 is excluded by the rule either way).
- The brief's four tap[0] values and the "L2 GRT hold repair then -23 to -31" numbers are the lanes'; I opened one of each kind (cbn_q01 -200.2; slw_sc_v2 GRT repair to +0.15).
