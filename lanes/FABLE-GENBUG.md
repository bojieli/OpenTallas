# FABLE-GENBUG: kit generator and hook defects of the QC cb class, all dies

2026-11-15 PST, FABLE-GENBUG. Pattern hunted: a kit-generator hook that silently handles only part of its input (FABLE-QC-CB: `core_input_chain.tcl` head hop, `core_input_anchor.tcl` 0 of 6,148).

Scope read: the hooks under `tools/die_plan/` of the four live die srcs in `autopilot/kit_wave.json` (S81 B3x2b, HEAD rp21z c327, QC qc-s29-tree2, KV kvgeom6_pgL) and main 22c217df54.
Evidence: every `OT_*` hook line of every wave kit log on intel1, epyc2, epyc7, epyc8, epyc9, epyc10 (498,272 lines, 99 hook tags; S81 362 kits, QC 107, KV 54, HEAD 18, HBM 59), plus placed-database queries on 19 kits (S81 9, QC 3, KV 4, HEAD 3) through ot-run.
Work dir: epyc8 and epyc9 `/srv/opentallas-scratch2/claude/fable-genbug/` (`stq/` queries and outputs, `proof/` builds, `wt/` clone). Logs: intel2 `~/fable-genbug/`.

All numbers are MEASURED unless marked INFERENCE or COORD (reported to me, not re-measured).

## 1. Defect table

| id | hook, line | symptom | measured coverage | dies / types | fix | owner / branch | status |
|---|---|---|---|---|---|---|---|
| G1 | `kit_istations.py:1556` (emits `is_place {*u_lpad_<bus>[./]r\[j\]\[*}`), and `:190` exact bank | Yosys names the LAST register of an `ot_dp_dly` after its output port: `<inst>.q[b]`, never `<inst>.r[D-1][b]`. The last planned station of every packed lane pad matches no flop and is left to global placement. The log only says `missing: N {pattern}` and passes | Kits with at least one last stage unplaced: S81 297 of 343, QC 26 of 106, KV 4 of 52, HBM 15 of 45, HEAD 0. Placed database: c1x_C__t1 2,882 flops on 7 pads, q50 442-965 um from their planned site (q90 758-1,279), hops into them up to 2,201 um; col_h9_r1 1,167 flops q50 924 um; col_h10_r2 1,230 flops q50 523 um; kv3_hub_Eo 170 flops q50 250-613 um; kv3_sys_c 1,121 flops q50 165-654 um; leaf t11/t14/t54 595 flops q50 175-351 um; cbf_q01 514 flops q50 224 um | S81 all col, leaf, slice, eng types with a lane pad; QC cbn/cbf, stm; KV hub, sys_c, phy; HBM q_b, q_su | `is_place_alt`: try the stage glob, then the `q[b]` alias; exact bank accepts `q[bit]` as stage D-1 | FABLE-GENBUG, `claude/fable-genbug-1115-1` @4e7f20bccb | FIXED on branch, proof in section 3 |
| G2 | `face_flops.tcl` (pin registers "within 2 buffers" of a port) and `landing_placement.tcl` (no `u_bin` handling) | On a landed input bus the capture register `u_bin_<bus>` sits BEHIND the landing ring, so no hook gives it a site. Global placement pulls it to its loads. The ring is FIRM at the pin, so ring -> `u_bin` becomes a long zero-logic hop. This is the S2 "pure distance" class of FABLE-METHOD (`u_cland_cmd_wi ... -> u_bin_cmd_wi/q`, 40 buffers) | Hops ring -> `u_bin` over 405 um: c1x_C__t1 1,924 of 2,004 (max 2,183 um, 31 buffers); cbf_q01 1,024 of 1,032 (721 um); kv3_hgi 501 of 1,559 (1,006 um, 488 cross a core); kv3_sys_c 475 of 548; lepw_mu_LP tp_i 276 of 276 (951 um); sle_st_b_v2 368 of 1,168 (742 um); kv3_hub_Eo 119 of 256; sle_sc_v2 32 of 160. "Ports without a flop within 2 buffers": median share QC 0.56, KV 0.63, HEAD 0.47, S81 0.04 | all dies, every type with landed (clock-landing) input buses that are not ft slots | place `u_bin_<bus>` FIRM beside its ring read outputs (brief 4.1) | NEEDS-LANE (Sonnet), brief 4.1 | OPEN |
| G3 | `die_trial.py:4794` `psm_pdn_tcl` | With `die.pg.domains` the one `{parts}` macro grid is defined in the default Core domain, which has no stripes; the stripes are in the `ot_pg_*` region domains. Every partition grid is empty (PDN-0233) | COORD: KV kvgeom5, likely HEAD. Fix form proven by DIE-KV-ROUTE-1 (`pdn2.py`, epyc7): pdngen clean, 160 of 160 partitions | every die with PG region domains (KV, HEAD, QC, S81) | one macro grid per region, partitions by centre, `touched == expected` assertion | FABLE-GENBUG, same branch @4e7f20bccb; unit test `test_die_pg_parts_region.py` | FIXED on branch (generator form of the proven post-edit); a die pdngen run of the generator output is the remaining proof |
| G4 | live die srcs vs main (`tools/die_plan/*`) | Kits copy hooks from the die src tree, and the trees have drifted from main in both directions. Fixes merged to main never reach the kits; hand patches in the trees are not on main | Files that differ from main 22c217df54: S81 8, KV 11, QC 14, HEAD 14. Main-only lines missing in the tree: QC `core_input_anchor.tcl` 87 (the 11-13 fixes fe86e6ab12, 6d5f095842: this is why QC still logs `pipe_regs 0`: 17 kits, 98,368 latches, 0 anchored), `core_input_chain.tcl` 260 (QC, KV, HEAD), `reset_tree.py` 221 (QC, KV, HEAD), `face_flops.tcl` 42 QC / 21 KV, `hold_gate.tcl` 35 (QC, HEAD). Tree-only lines not on main, same in all trees: `landing_placement.tcl` 152, `postcts_gate.tcl` 15, `subtree_balance.tcl` 8 | all 4 dies | hook manifest in every kit + wave preflight against main (section 5.3); refresh the trees after proof | MERGE-QUEUE-1 src refresh + KIT-OPS; TYPE-QCCB-GEN for anchor/chain | OPEN |
| G5 | synth flow (`ot_keep_regs.tcl` only keeps wires named in `OT_KEEP_WIRES`) | Yosys `opt_merge` folds intentionally duplicated register banks; one bank then drives loads far apart. `reg_fanout` does not see it (2-8 loads) | New census `merged_replica_census.py` (sibling instances of one elaborated module with fewer flops than their twin) reproduces FABLE-KVOVF exactly: kv3_hg_v1 and 7 kv3_hgi kits, `qkh_head_tstage` 6 instances, 3 short, `ti_b` 4,677 flops missing (9,356 with the gather stage). Other hits, cause not yet separated from constant pruning (INFERENCE): kv3_hub_Eo/Wo `qkd_seq_fan_s` 1 of 2 fan copies lost 1,142 of 1,151 flops (`qd`, `qd2`, `kc`); S81 lepe/lepw_mu_LP `ot_sram_oldread_wreg` 3 of 4 lost `wdata` 1,106; HEAD hd_mesh `ot_sram_oldread_b64` `wdata` 1,106 and `ot_s81hd_lsc_t9` `txd_p` 485; kv3_pc `ot_dp_dly` 112 + fifo 788; QC sle_st_b 342. Kits with >= 64 flops missing: KV 16 of 34, S81 2 of 160, HEAD 2 of 15, QC 3 of 15 (only kits that still had the RTLIL) | KV hg, hgi (setup -586/-753, -366 with keep: FABLE-KVOVF); candidates KV hub, pc; S81 lep slices; HEAD mesh | census as a kit gate after synth; the generator sets keep on replicated station/bank registers (brief 4.2) | KV-102 (generator default), KIT-OPS-5 (wave env); census on my branch | tool on branch; wiring OPEN |
| G6 | `face_flops.tcl:800` `OT_FT_LANE` | ft stations are placed beyond the plan reach and the hook only prints the count | Kits with placed station hops > 405 um: S81 23 of 149 (12,510 hops, max 505 um; leaf t56 2,377, leaf t1 1,376, kv_leaf t1 1,351), KV 11 of 47 (3,612 hops, max 508; hgi_v8 1,231, hgi_v6 1,015), QC 9 of 93 (884, max 425), HEAD 0 of 9 | S81 leaf, KV hgi, QC sle_fe | cause not traced (plan sites vs nearest free site); make the line a gate at reach + 5 % | NEEDS-LANE with G2 | OPEN |
| G7 | `relay_mid.tcl` FIT fallback; `kit_istations.py:286` relay_sites | Stations fall back to the old nearest-free point; plan relay keys match no flop | S81 col: 15 of 18 kits with FIT use the fallback, 150 stations (15 of 79 on col_h10_r1). `OT_RELAY_SITES plan keys unmatched`: QC sle_fw_v3 524 of 5,678; KV kv3_pc 2 of 7 | S81 col_h9/h10; QC sle_fw; KV pc | fail when fallback share > 5 %; list unmatched keys | S81-COLGEN-1; DIE-QC-103 | OPEN |
| G8 | no hook: `ot_dp_dly u_d<N>_*` transport pipes (bind.py) | Intra-partition transport stages get no site outside the QC NK chain hook; GPL clumps them | col_h9_r1 `u_d10_6_Y` 9 stages over 1,695 um, worst hop 1,268 um (ideal 170); cbf_q01 `u_d16_u_t_1_3_n_y` worst hop q50 865 um (ideal 120), `u_d6_..a_d` 841 (ideal 153); c1x_C__t1 `u_d1_u_s_1S_u_lp_*_Y` 667 bits, worst hop q50 709-854 um with one stage over 913-1,120 um (this one is a stage-count shortfall, a plan item) | S81 col, slice; QC cb (cb part is TYPE-QCCB-GEN) | generic chain spreader keyed on the master (`ot_dp_dly`), not on a die name (brief 4.3) | NEEDS-LANE | OPEN |
| G9 | `leaf_affinity.tcl` | The hook moves almost nothing and reports success | groups moved / groups: S81 2.0 %, QC 3.8 %, KV 4.9 %, HEAD 0.8 %; `skip_far` share 83-99 %; cross-leaf pairs after / before 0.98-0.997 (median per die) | all dies | advisory only (clock quality, not a gate): print coverage, review the 30-um radius | R-CLOCK rule owner | OPEN, low |
| G10 | plan-shape abstract generator | Emits a 0.032-um M7 pin (`nst4/arst_n`, hd_st_n4), below minimum width | COORD (DIE-HEAD-ROUTE-1). Same width class seen before on S81 station t51 clock pins (review queue 11-12) | HEAD hd_st_n4; INFERENCE: any abstract with a 1-track M7 pin | clamp pin width to the layer minimum in the generator, assert in the abstract check | DIE-HEAD-ROUTE-1 | OPEN, not re-measured |
| G11 | `proto_die.sh` / die chains | `--count-align` not passed | COORD: HEAD and KV | HEAD, KV | pass the flag from the plan; chain fails when the plan has count-aligned buses and the flag is absent | DIE-HEAD-ROUTE-1 (fixing on main) | OPEN, not re-measured |
| G12 | `forest_recluster.tcl:267` reset chains | The chain regexp needs `g_reg.r[k]`; the last stage is `q` (same naming as G1) | `OT_RESET_CHAIN 0 chains` in all 4 S81 slice kits that ran it. Their netlists hold no `lpr_root` / `frl_rst` flops, so 0 may be correct here (INFERENCE: latent) | S81 | add the `q` alias as in `txl_mid.tcl` | with G8 lane | LATENT |

Checked and clean on the wave logs: `OT_RESET_TREE` (0 missing in 508 kits; 3 kits with 2 hops over), `OT_CORE_OUT_LAND` (2 pins left to GPL in 17 kits), `OT_FACE_FLOPS` ft stations j>=1 (S81 77 missing in 30 kits, small), landed line (0 missing), hop latches (0), `OT_CLAND_EXPORT_CHECK` (0 dead).

## 2. Answer to COORD: where the long hops come from

The plan caps hops at 405 um; the kits do not keep them. Zero-logic register hops over 405 um on placed databases (`hop_census.py`): c1x_C__t1 17,826 of 47,071 (2,696 cross a hard core); lepw_mu_LP__t2 4,872; col_h9_r1 4,493; kv3_sys_c 4,062; cbf_q01 3,583; leaf t54 1,358; sle_st_b_v2 1,043; leaf t14 1,014; kv3_hgi 879 (629 cross a core); col_h10_r2 874; kv3_hub_Eo 627; leaf t11 528; sle_sc_v2 308; HEAD hd_st_str, hd_turn_a, hd_spn_eshim_rx 0.

By cause, largest first: G2 (ring -> `u_bin`), G1 (last pad stage), G8 (`u_d` pipes), then core pin -> first station (`u_ist_leafup`, 250-276 hops per leaf kit, 576-912 um) and core -> `u_bout` (sle_sc_v2 `u_core.* -> u_bout_x_*`, 510-673 um), which are station sites the plan does not have (plan items, not hook defects).

## 3. Proof of G1

Kits copied to epyc8 `fable-genbug/proof/`, only `istations.tcl` rewritten to the new generator output (`xform.py`), place re-run from the floorplan through ot-run.

| ot_s81sl_leaf__t11 (pad `u_lpad_leafdn_i0`, D2, 595 bits) | wave kit | patched hook |
|---|---|---|
| `OT_ISTATIONS placed` | 5,109 (missing: 1 `r\[1\]`) | 5,704 (missing: 0) |
| `OT_HOOK_COVERAGE` | - | `touched=5704 missing=0 packed_stage_unmatched=0` |
| last stage FIRM | 0 of 595 | 595 of 595 |
| last stage to its planned site, q50 / q90 | 175 / 207 um | 13 / 27 um |
| hop into the last stage, max | 721 um | 296 um |
| `r[0] -> q` hops over 405 um | 35 | 0 |
| zero-logic hops over 405 um, whole type | 528 | 427 |

Measured on the global-placement database of the proof (`pq/`), baseline on the wave `3_place.odb`. The 427 left are core pin -> `u_ist_leafup` and the pad's loads (plan sites, section 2).

dsdv_slice_c1x_C__t1 (7 pads, 2,882 last-stage flops, the worst kit) is running in the same form (epyc8 `proof/dsdv_slice_c1x_C__t1`, log intel2 `~/fable-genbug/proof_dsdv_slice_c1x_C__t1.log`); at 00:40 it was in the pre-floorplan lint. Pass: `missing: 0`, last stage within 30 um of its site (q90), `u_bin -> u_lpad` and `r[k] -> q` hops over 405 um gone (656 and the `r -> q` rows today). Check with `bash pq/stq_run.sh` after copying its `3_3_place_gp.odb`.

Not proven: timing and GRT effect (place only). The patch changes no stage count and no plan site.

## 4. Implementation briefs (Sonnet lanes)

### 4.1 CLAND-BIN (G2, with G6)
In `landing_placement.tcl`, after a ring is placed: for each landed input bus that is not an ft slot, find the first non-ring flop on each ring read output (through BUF/INV only; match by master `DFF*`, never by name) and place it FIRM at the nearest free site to its ring read bit (reuse `ff_put_near`), record it in `ot_face_flops.txt` so `face_flops_release.tcl` releases it. Print `OT_CLAND_BIN bus <b> placed N of W` and fail under 95 %. Proof: c1x_C__t1 (1,924 hops -> 0), cbf_q01 (1,024 -> 0), kv3_hgi (501 -> 0), each with `hop_census.py` on `3_place.odb`; setup at CTS on QC slw_fw_v2 (-446) and sle_stm_v3 (-444). Same lane: make `OT_FT_LANE` hops over reach a gate and trace S81 leaf t56 (2,377 hops, 496 um).

### 4.2 MERGE-CENSUS (G5)
Run `merged_replica_census.py KIT` after synth in `run_kit.sh` (2 s per kit). Write `merge_census.json`. For each short sibling whose missing register names are listed, append them to `OT_KEEP_WIRES` and re-synthesise once; fail if the second census still shows the same names. In the generator, set `(* keep *)` on the registers of replicated station and bank modules (`ot_dp_dly`, `ot_dp_st`, per-destination stage modules). Separate constant pruning from merging by checking that the short instance's output net is driven by the twin's flop. First targets: kv3_hub_Eo/Wo `qkd_seq_fan_s`, S81 lep `ot_sram_oldread_wreg.wdata`, HEAD hd_mesh.

### 4.3 DLY-SPREAD (G8, G12)
One hook for every `ot_dp_dly` chain that has no plan site: stages on the route from the driver pin to the load centroid at j/(n+1), buffers of every hop included (head hop too), stage identity from connectivity (D of stage k is Q of stage k-1), names only for the log. Report `chains, stages_moved, max_hop before/after` and fail when a chain's worst hop exceeds its ideal hop by 50 %.

## 5. Generic guard

### 5.1 `OT_HOOK_COVERAGE` in every hook
One line per hook, same format: `OT_HOOK_COVERAGE hook=<name> touched=<N> expected=<M> [class counts]`, where `expected` is counted from the design by cell master and connectivity, independently of the name patterns the hook uses to do its work. The hook fails closed when `touched / expected` is below its threshold (default 0.95; 1.0 for station, anchor and PG hooks); `OT_HOOK_COVERAGE=warn` in config.mk downgrades it for one kit and is logged. Implemented on the branch for `istations` and `die_pg_parts`. Expected counts for the others:

| hook | expected M | today's line that hides the gap |
|---|---|---|
| `core_input_chain` | hops of every chain, head hop included | `stages_moved` (no hop count) |
| `core_input_anchor` | latches | `latches 6148 pipe_regs 0` |
| `istations` | planned stages x live bits | `missing: N {pattern}` |
| `face_flops` | signal ports minus declared ring/ft ports | `N ports without a flop` |
| `relay_mid` / `relay_sites` | planned stations / plan keys | `NOFIT (old fallback)`, `unmatched k of n` |
| `landing_placement` | ring flops + capture registers per bus | none for capture registers |
| `ft lane` | slot bits x stations, hops <= reach | `N hops > 405` |
| `clock_taps` | planned taps with >= 1 sink | `0 clock pin(s)` |
| `leaf_affinity`, `tap_pair` | pairs in reach | `skip_far` |
| die PG | hard instances with a grid | PDN-0233 warning |

### 5.2 Placed-database preflight for every die (the conn6.py form)
`hop_census.py` on `3_place.odb` (40-120 s, 2 threads): zero-logic register hops over reach, hops crossing a hard core, by source/sink class. Gate before CTS: crossing hops <= 20 and over-reach hops <= 1 % of zero-logic hops; the report names the classes, so the failure is assigned to a hook and not to the plan.

### 5.3 Source guards
- `merged_replica_census.py` after synth (5 above, 4.2).
- Hook manifest: gen writes `hooks.manifest` (sha of every hook file copied into the kit, the tree sha and main's sha for the same path); the wave preflight flags a hook that is older than main or not on main (G4).
- Wave-level: `tools/failure_breakdown.py` adds one row per die with the kits whose `OT_HOOK_COVERAGE` is below threshold, so a silent hook shows up as its own class.
