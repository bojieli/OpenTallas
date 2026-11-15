# MERGE-CENSUS handoff (lane MERGE-CENSUS, FABLE-GENBUG brief 4.2 / G5)

Status 11-15: census DONE on 347 current kits (newest kit per die x type, epyc2/7/8/9/10 + intel1, kw4x waves; tool = merged_replica_census.py @4e7f20bccb, 0 NOINPUT, 0 ERR). Generator keep + proofs: READY (below).
Raw rows: ~/coord/lanes/handoff/MERGE-CENSUS-rows.txt (MRGSUM/MRG per kit).

## Census (kits with >= 64 flops missing in a short sibling)
| die (kit dir) | kits scanned | kits >=64 missing | 
|---|---|---|
| KV (qwen_kvsys) | 37 | 20 |
| QC (qwen_compute) | 78 | 21 |
| S81 | 196 | 7 |
| HEAD (s81_head) | 15 | 2 |
| HBM | 21 | 5 |

## Candidates from the brief
| candidate | verdict | evidence |
|---|---|---|
| `ti_b` (qkh_head_tstage / qkh_head_gather_stage) | CONFIRMED, MERGE | 12 KV kits, 4,677 flops (kv3_hgi_v8 etc), same-module banks, D from same chain (FABLE-KVOVF measured). Fix OT_KEEP_WIRES=ti_b; FABLE-KVOVF owns the per-core last-stage copies and r_hgi2 / r_hg. |
| kv3_hub_Eo / Wo `qkd_seq_fan_s` | CONFIRMED, MERGE | 1 of 2 instances lost 1,142 of 1,151 flops (qd 512, qd2 512, kc 32). RTL (bound.sv): u_seq_g_fan_0/1 take the SAME q, kc_i, aqm; only `af` differs (feeds a1/af_o which survive). Not pruning: outputs are all used. Keep names: qd qd2 kq kq2 am am2. |
| S81 lep `ot_sram_oldread_wreg.wdata` | CONFIRMED, MERGE | 4 per-lane write regs (g_tx[0..3].g_safe_write.u_m); wd = {sq[t/2], hf0/hf1}: netlist has wdata flops tx0 553, tx1 552, tx2 1, tx3 0 (only the hf bit differs). 4 kits: lepw_mus_LP__t2, lepe_mu_LP__t2, lepw_mu_LP__t2 (1,106 each) + lepe_nh_mus_LP__t1 (1). |
| HEAD hd_mesh wdata (1,106) | CLEARED in current kits | hd_mesh_e: 0 short siblings (483 flops). The current HEAD hit is hd_host_w `ot_sram_oldread_b64.wdata` 553 (2 insts, 1 short): same family as the S81 lep wdata (same module pattern), treated as MERGE-LIKELY, to be proven with the keep. `ot_s81hd_lsc_t9 txd_p` (485): not in current kits. |
| HEAD hd_ctl `ot_dsrom_mtp_ltx l_data` 117 | UNCONFIRMED (looks like ROM constant pruning) | not kept. |

## Other hits >= 64 (not in the brief; no keep applied, owners decide)
| die | module / regs | kits | max missing | note |
|---|---|---|---|---|
| QC | ot_qfd_xs_leaf wo_d 2048, wctl 216 (also _fo32_w, _fo32) | 15 | 2,632 | slw_hc2/hc3: 8 insts, 6 short; likely replica, unclassified |
| QC | qfd_dv_s8_vm8q_rp1_twc/vrd/vwr q | 3 each | 2,084 | slw_su_c: unclassified |
| QC | qfd_dv_s8_station_tail1_* r / cfg_payload | 4 | 276 | sle_st_b / slw_st_b: unclassified |
| QC | coll_core qfd_static_ch546, ot_qkvd_llr_replay_sram_leaf | 2 | 193 | unclassified |
| KV | ot_async_fifo mem 768 (kv3_pc) | 5 | 788 | unclassified |
| KV | ot_dp_dly q 112 (kv3_pc), ot_hdc_w11_cut, fp32 add/mul, nearhbm_qmul (hub_C, hg_v3) | 3-4 | 540 | width-parameter siblings likely (KVOVF note) |
| S81 | ot_hdc_f12_cut / qmul / fp32_mul_f12 r (ot_s81sl_kv_leaf__t5 ...) | 12 | 2,716 | 21-46 instances, per-instance constants; likely pruning, unclassified |
| HBM | ot_hnx_su_exp/plain4 g_compose_m*_q (q_su00/q_su21) | 5 | 9,674 | unclassified |
| HBM | ot_hdc_delay q 512 | 2 | 512 | unclassified |

## Rule violations to note
Before the COORD reminder I ran read-only git (git show, git status) in intel2 ~/OpenTallas and started a git clone that read from it; the clone was killed by PID and removed. No state changed. Own clone: intel2 /srv/opentallas-scratch2/claude/merge-census/wt (from GitHub; branch claude/fable-genbug-1115-1 is not on GitHub, so the census tool is added to my branch from the saved copy).

## Next
1. generator keep list derived from the RTL replica pattern (instances of one module with identical data inputs), branch + tests.
2. proof, one kit per die: synth census then place.

## QC classification (same RTL test: identical inputs = merged, distinct surviving bits = intended)
| module / regs | verdict | evidence |
|---|---|---|
| qfd_dv_s8_vm8q_rp1_vwr / vrd / twc `q` (slw_su_c) | MERGE | sibling instances take the same d bits; only one copy's q survives |
| qfd_dv_s8_station_tail1_* (orq3, nb0_orq, nb0_orq_mrep) `r`, cfg_payload0/1 (sle_st_b, slw_st_b) | MERGE | r4..r7 take the same cfg/rs/nb inputs; only r4 keeps flops |
| qfd_dv_s8_pad `r`,`q` | MERGE | nb_c identical in all 4 instances |
| ot_qfd_xs_leaf (+_fo32, _fo32_w) wo_d/wctl | INTENDED | last leaf of each chain has wo_d unconnected; wctl shrinks 72/54/36/18 |
| qfd_static_ch546, ot_qkvd_llr_replay_sram_leaf (coll_core) | INTENDED | constant-tied padding bits |
| kv3_pc ot_async_fifo mem, ot_dp_dly q | INTENDED (inspection) | HAS_SEAL / width params differ |
Not classified: S81 ot_hdc_f12_cut / qmul / fp32_mul_f12 (ot_s81sl_kv_leaf__t5 ...), KV hub_C / hg_v3 hdc fp32 + w11_cut, HEAD hd_host_w ot_sram_oldread_b64 wdata (same family as lep wdata, no b64 synth proof). HBM skipped (parked).
Note: kv3_hub_Eo/Wo residual `sync_q:2` is a reset synchronizer, not a data replica.

## READY: generator keep (branch claude/merge-census-1115-1, intel2 clone /srv/opentallas-scratch2/claude/merge-census/wt, commits ea5c7f9261, 6f0c8e1765; NOT pushed)
replica_keep.py derives Module:reg from the kit RTL (module instantiated >= 2 times, generate-for counts 2, unconditional port-staging regs); gen_phys.replica_keep_wires exports OT_KEEP_WIRES (OT_REPLICA_KEEP=0 opts out); ot_keep_regs.tcl takes `Module:wire` (paramod-aware). Tests: test_replica_keep.py + test_kit_keep_gpl.py, 8 passed.
| proof kit | die | census before -> after | flops | place | LEC |
|---|---|---|---|---|---|
| dsdv_slice_lepw_mus_LP__t2 (epyc7) | S81 | 1,106 missing -> 0 | 41,899 -> 43,005 (+1,106 = wdata) | 3_place.odb, no FAIL | async LEC exit 0 |
| kv3_hub_Eo (kvgeom4, epyc2) | KV | 1,142 -> 2 (sync_q) | 73,041 -> 82,251 (fan_1 copy + its dp_dly chain) | 3_place.odb, no FAIL | UNPROVEN, identical to baseline (frontend elaboration) |
| kv3_hub_Wo (kvgeom6) | KV | 1,142 -> 2 | 76,897 -> 88,797 | FAIL OT_CLAND BAND FAIL x2 in global_place, identical in the unmodified baseline | n/a |
Not proven: HEAD/QC die (no confirmed-merge generator target there yet), ot_sram_oldread_b64 synth census, ti_b by my own run (FABLE-KVOVF measured it; derive gives qkh_head_tstage:ti_b on kv3_hgi_v8). r_hgi2/r_hg untouched.

## Round 2 proofs (HEAD, QC, b64) 11-15 -- branch claude/merge-census-1115-1 pushed @6f0c8e1765 (COORD approved)
| proof kit | die | census before -> after | flops | place | LEC |
|---|---|---|---|---|---|
| hd_host_w (hdw_base vs hdw_keep, intel1) | HEAD | ot_sram_oldread_b64 wdata 553 missing -> 0 (short siblings 1 -> 0) | 30,175 -> 30,760 (+585) | 3_place.odb, no FAIL | not read |
| slw_su_c__cl19bb38ef (epyc8) | QC | 3,574 missing in 4 modules (vm8q vwr 2,084, twc 1,088, vrd 400, dp_dly 2) -> 2 (dp_dly r:2) | 41,720 -> 46,239 (+4,519) | 3_place.odb, no FAIL | EQUIVALENT, 100,672 compare points proved, 0 differ, exit 0 |
ot_sram_oldread_b64 is now proven at synth+place (same derivation as ot_sram_oldread_wreg). Residual QC dp_dly r:2 (1 of 354 instances) is not a data replica. Remaining unproven: ti_b by my own run, S81 ot_hdc_* / KV hub_C leftovers unclassified.

## RESULT 11-15 (close-out of the three open items)
1. HEAD hd_host_w LEC: still RUNNING (async LEC started 07:29 host clock, no result line yet; a watcher is armed). Equivalence not known yet; the line will be appended when it lands.
2. Leftovers classified (RTL sibling-input test; hub_C is inferred from repo RTL because its kit rtl/netlist are deleted):
 - S81 ot_hdc_f12_cut:r (nested in fp32_mul_f12, qmul_lat): MERGE, b operand shared by the 4 lanes; already derived by replica_keep. ot_hdc_f12_cut:v (26 valid bits): minor MERGE, not derived (OT_ARST macro hides the reset block). u_sq (a==b), u_scale (const b), u_w: HARMLESS.
 - KV hub_C ot_hdc_w11_cut:r inside fp32_mul_lat (15 lanes x 34+1): MERGE (shared u_mul .b(rzh), DRST=1). NOT derived: derive drops r because the {W{1'b0}} reset concat fails its staging test. FIX (next generator edit): replica_keep.qual accepts a replicated constant {N{1'bx}} as a constant and accepts the OT_ARST reset block as the async-reset form; then ot_hdc_w11_cut:r, ot_hdc_f12_cut:v and ot_hdc_fp32_add_lat:s1_v,s2_v (valid only, 60 regs) are derived. Until then OT_KEEP_WIRES=ot_hdc_w11_cut:r can go in per-item env.
 - KV hg_v3 fp32_mul_lat / nearhbm_qmul / fp32_add_lat / w11_cut: HARMLESS (constants from POLY / K_LOG2E prune flops, per-instance operands differ).
3. claude/merge-census-1115-1 @6f0c8e1765 is IN origin/main (merge-base --is-ancestor true; origin/main b89ba8df4f). No READY re-post needed.
Unverified: hub_C on a netlist, DRST in the actual build, whether the extra keeps remove the merge.

## RESULT 11-15 (HEAD hd_host_w LEC, for HEAD-100)
HEAD hd_host_w with the derived keep (hdw_keep, intel1): async LEC EQUIVALENT, ot_s81hd_host_w_ep cp=82590 proved=82590 differs=0 undecided=0 (39,294 key points matched by name, 32,272 register pairs / merges and 664 constant registers proved inductively), LEC exit 0 at 11:30 PST. Census: ot_sram_oldread_b64 wdata 553 missing -> 0; flops 30,175 -> 30,760; 3_place.odb, no FAIL.
Also: generator branch is now claude/merge-census-1115-3 @6e33128851 (hdc keep + generate-scoped *.wire fix), READY follows after the S81 hdc census/place.

## READY 11-15 (hdc keep fix) -- GATE main=dd656c7acb39b9df25ba511bf302f412ee022131
Branch claude/merge-census-1115-4 @5f235e68e04837ea078cc8c6c82c091c3b046761 (on the lane mirror; replaces -2/-3, same two commits rebased on main). FULL working tree (sparse-checkout disabled): tools/die_plan/test_replica_keep.py + test_kit_keep_gpl.py + test_kit_contract.py all pass (0 failures).
Change: replica_keep.qual takes a replicated constant {W{1'b0}} as a constant and accepts the `OT_ARST(rst_n) async-reset block; ot_keep_regs.tcl `Module:wire` also matches generate-scoped regs (*.wire, e.g. ot_hdc_w11_cut g_r.r). Derives ot_hdc_w11_cut:r, ot_hdc_f12_cut:r/v, ot_hdc_fp32_add_lat:s1_v/s2_v.
Proofs:
| proof | before -> after |
|---|---|
| S81 ot_s81sl_kv_leaf__t1 (intel1, ot-run to place) | flops 49,875 -> 53,303 (+3,428); missing-in-short-siblings 14,328 -> 6,815; OT_KEEP_REGS 5,593 cells; f12_cut r (2,675 missing) now 0 on r, residual rows are `q:` (1,704 / 1,164 / 557 / 469) = pruned/different-operand bits, not r replicas |
| KV hub_C proxy: qkd_pv_fin_s module synth (epyc2, ot-run) | kept cells 0 -> 750; flops 42,910 -> 43,760 (+850). No real hub_C kit exists (cleaned, reports only), so this is a module-level proof, not a kit |
Old hook (before *.wire fix) kept 0 hdc cells on the same kit: 2,675 missing unchanged.
Not shown: S81 place/route result of the hdc kit (run was relaunched with the fixed hook; place status in ~/mc_proof_s81hdc.log on intel2), real hub_C kit, the residual `q` rows are classified only by the agent's RTL argument.
Until merged: WAVE-HOLDS-1115 asked (post fcfa-time) to set OT_KEEP_WIRES=ot_hdc_w11_cut:r on kv3_hub_C items; with this fix the Module:wire form also reaches g_r.r.
