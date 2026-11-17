# S81-TYPES-R-IFN0 handoff (IFN0 halves fork of S81-TYPES-R; started 11-16 17:1x PST)

W = epyc2 /srv/opentallas-scratch2/claude/s81-ifn0-halves. My tools: W/read_types_r (run_stage2.sh KIT cts|grt|route|finish MEM CPUS; run_probe3.sh KIT ODB TAG GRT(0|1); run_look.sh KIT ODB TAG; dump_cts.py; render.py; clock_probe_split_v3.tcl = Codex v2 + IFN0_INTERNAL / IFN0_PORT lines; face_capture_release_splitbal.tcl). Launch: intel2 `ot-run --mem N --threads N --hosts epyc2 --dir W -- bash W/read_types_r/...` (data only on epyc2; disk 58 GB free). Client logs intel2 ~/s81-types-r-ifn0-*.log.

## COORD rulings (FABLE-CLOSURE-STRATEGY lever 2), 17:2x
- (b) Close the halves in CTS: the 512 IR flops go in a balance group next to the QB cohort (no hold buffers for that class). Both halves. Sibling kit dirs, never patch a running kit.
- (d) STOP LIST: no number from the old ICG-bypass halves (he1p / hw1p / hw0 / he0, as-built pin contract, face CK 390-398, old leads) in rows, tap insertion, pin contracts or comparisons. Rows to S81-DIE-R come only from split-form measurements.

## Kits
- he_splitclk1 (Codex): 57 root / 547 same-ICG / IR unchanged. Post-CTS LOOK PASS (review/postCTS_split_review.txt). GRT started 17:1x as EVIDENCE ONLY (client 210044, unit 2069104-1794878108, run_split_grt.log); not to be routed.
- hw_splitclk1 (mine, from hw1p original 3_place 6d0c9785e350): same form, CTS done, ancestry PASS; evidence only.
- he_splitbal1 / hw_splitbal1 (MAIN): split form + IR 512 on its own BUFx12 root child (face_capture_release_splitbal.tcl). Ancestry PASS all 29928 FF both. LOOK PASS both (review/postCTS_splitbal_review.txt + png).
- hw uses he's orfs_hold_mm.{py,tcl} (16:24 version, reg2reg hold scope); hw1p versions kept as *.hw1p.

## CTS reads (placement RC, clock_profiles_r/cts/{TT,FF}/probe.log; slack numbers in the IFN0_INTERNAL line are ps x 1e12, divide)
- HE bal: QB 364..371 TT / 286..293 FF; IR 388..403 / 300..315 (was 407..470 / 326..386); root57 395 / 305. FF hold: QB->IR -22.9 (was -97.1); IR->fw_q -58.9 (was -24.2); worst internal -133.2 is main-tree u_add r->r (2494 endpoints, same in every form). TT setup +17.8.
- HW bal: QB 369..375 / 291..297; IR 412..423 / 318..329; root57 415 / 320. FF hold: QB->IR -32.8; IR->fw_q -96.2; main tree -100.5 (2455). TT setup -84.6 (g_wen u_we -> f_q1, 122 endpoints, pre-repair).
- QB->IR + IR->fw_q deficits sum to about 82 (he) / 129 (hw) FF: fw_q sits late on the main tree, so no IR position clears both; the rest is GRT hold repair (reg2reg scope).

## Running
- GRT he_splitbal1: intel2 client 338348, log ~/s81-types-r-ifn0-he-bal1-grt.log. GRT hw_splitbal1: client 339327, ~/s81-types-r-ifn0-hw-bal1-grt.log. Kit log KIT/run_split_grt.log.

## Next
1. GRT done -> run_probe3.sh KIT 5_1_grt.odb grt 1 (TT setup, internal FF hold, QB->IR, IR->fw_q, per-port table).
2. run_stage2.sh KIT route, then finish; pin_audit, corners.tcl, signoff.py (copied from he1p into he_splitclk1; copy to the bal kits), gates DRC 0 / TT >= -42 / internal FF hold >= 0.
3. Views (lib TT/FF, LEF, pin contract from THIS routed DB), export AGIdock /archive/opentallas-signed-1114 + rtx-pro, INDEX.tsv append.
4. Rows to S81-DIE-R (post.sh S81-IFN0-HALVES): views + hashes, .IFN(0) at gb_split (claude/s81-gotag-setup-1115 @a6fe65df8ac), core tap insertion from the split-form per-port table, sequencer lead 0, ROM lead measured.

## 18:4x GRT reads (reloaded 5_1_grt.odb, global-routing RC, clock_profiles_r/grt)
- HE bal (GRT 3229 s): internal reg2reg setup and hold 0 violators at TT and FF. Port only: TT input setup -17.24 (6), FF input hold -30.00 (560, parent side). CK TT: gated547 421..431, root57 403, IR 401..415; FF 338..347 / 313 / 313..326.
- HW bal: internal 0 violators at TT and FF. Port only: TT input setup -4.77 (5), FF input hold -34.22 (541). CK TT: gated 430..436, root 426..428, IR 422..437; FF 345..351 / 330..333 / 328..343.
- he_splitclk1 evidence GRT (unbalanced) ended rc 0; not routed.
- Route: HE client 1008865 (~/s81-types-r-ifn0-he-bal1-route.log), HW client launched 18:4x (~/s81-types-r-ifn0-hw-bal1-route.log). Kit log KIT/run_split_route.log.

## 19:4x routed (6_final.odb + 6_final.spef; clock_profiles_r/routed; R-MINIMAL internal = reg2reg, ports excluded)
- HE bal: DRC 0 ANT 0. TT WNS -29.57 (port: 6 input setup); internal setup -2.35 (1). Internal FF hold -22.45 (221), all IR -> fw_q (fw_q on the late main tree); QB->IR +31 (lever 2b class closed). Port FF hold -51.5 (559, parent side).
- HW bal: DRC 0 ANT 0. TT WNS -15.97 (52 internal setup, inside -42). Internal FF hold -50.52 (406). Port FF hold -51.4 (550).
- Routed CK TT: gated547 443..455 (HE) / 445..455 (HW), up from 365..375 at CTS (gated branch picks up route RC + GRT hold buffers); root57 399 / 422, IR 398..417 / 423..441.
- Both: eco_loop check = ECO_ELIGIBLE (R-MINIMAL only internal FF hold). ONE hold ECO each (reg2reg scope, margin 5, max_iter 1; force_pa_reset.tcl replaced by Codex reentry-guarded version, originals kept *.pre_guard): HE client 1610335 (~/s81-types-r-ifn0-he-bal1-eco.log, KIT/eco_hold1), HW client 1762340 (~/s81-types-r-ifn0-hw-bal1-eco.log). Tools W/read_types_r/rmin_tools (copy of Codex rmin_hold_inventory1116).
- Legacy signoff.py verdicts NOT SIGNED (all-path hold incl ports, DRV slew advisory, face_guard NOT RUN: no 1_synth.v in these kits).

## 20:3x ONE-ECO RESULTS (eco_loop EXHAUSTED both; no second ECO by OWNER 11-07 rule) -> NOT SIGNED, nothing exported, no rows posted
- HE he_splitbal1/eco_hold1/i1: DRC 0 ANT 0; TT WNS -25.45 (6 input-port setup; internal setup 0 viol); internal FF hold -0.21 ps on ONE endpoint u_h.u_e.g_mac[0].g_ch3.u_c1.u_add.u_c6.g_r.r[37] -> u_c8.g_r.r[31] (main CF1 tree, pair skew TT 171); port FF hold -51.5 (559, parent). IFN classes all closed (QB->IR, IR->fw_q). Signoff minimal profile says hold_ff -10.19 because it counts 308 input-port starts at the in_min -40 overlay; non-port -0.21/1.
- HW hw_splitbal1/eco_hold1/i1: DRC 0; internal FF hold 0 viol (closed), but TT setup -144.30 (was -15.97). Worst: g_l3.u_l1.u_tag line[336] -> g_ch3.u_c1.acc_r[10], data path now carries 7 HB4 hold buffers. ROOT CAUSE (structural, main tree, not IFN): clkbuf_6_55_0_..u_c0.clk_regs drives 67 fF and its child clkbuf_leaf_336 stage is 230.6 ps, so acc_r captures sit 230 ps late; related-pair skew TT 264 (HE 171). Hold repair on those pairs necessarily breaks setup.
- Fix proposal (needs a new CTS on the IR-balanced kits, not an ECO): rebuild the main clk_regs tree with the leaf_336 region rebalanced (drop -sink_clustering_size 24 / max_diameter 30 + -obstruction_aware for automatic clustering, or cap the 6_55 wire), check pair skew < ~100 ps at CTS before GRT. Same for HE (171). Candidate for a Fable PD review (repeat closure failure on this core).
