# Die completeness, 2026-10-15 22:23 PDT

Measured inventory per die (tools/die_completeness.py). Every number comes from a bind record, the element registry, a native pin audit of the committed view, or a die-run log; the source of each is listed. Re-run daily.

## Summary

| die | netlist instances | distinct masters | non-real-RTL instances | instances without a closed view | open inputs (ports) | netlist masters closed+native PASS | netlist masters not closed+native | contract masters absent | remaining work units | masters left after DEDUPE ph-1 rebinds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen compute die | 1,638 | 37 | 0 | 840 | 71 | 4 | 28 | 10 | **118** | 32 of 37 |
| Qwen KV/system die | 19,342 | 58 | 132 | 7,707 | 25 | 13 | 39 | 4 | **78** | 20 of 43 |
| S81 (DeepSeek ROM) die | 84,387 | 255 | 0 | 8,836 | 7 | 151 | 99 | 38 | **167** | 108 of 122 |
| HBM accelerator die | 83 | 39 | 0 | 74 | 1,070 (= exposed inputs; 1,660 unresolved ports incl. outputs) | 1 | 37 | 16 | **1,139** | 44 of 53 |

Remaining work units = masters not closed + native PASS (netlist and contract-absent, hard macros excluded) + placeholders to replace (non-real-RTL masters + contract masters absent from the netlist) + inputs to bind (unconnected input ports + width mismatches + die ports missing in RTL). A contract master absent from the netlist counts once to close it (unless already closed + native PASS) and once to integrate it. HBM additionally carries its exposed input ports and unresolved source ports, listed per die below.

## Qwen compute die (Q-COMPUTE-DIE)

Contract: C19 / wide27 (PM-H-S blocked, chain runs without it) on contract v1.3 + static successors (complete=True).
Netlist / bind: `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/c23s/chain/port_bind/port_bind.json` (2026-10-15 20:01 PDT, opentallas.die_port_bind.v2), die.v `/srv/opentallas-scratch/claude/qwen-split-compute/c23s/chain/case_r22k/die.v`.

| item | value |
|---|---|
| (1) instances / distinct masters | 1,638 / 37 |
| bind verdict | FAIL (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 24 / 840 |
| (2) latest die run on real views | 8 masters / 793 inst (of 1,637); `/srv/opentallas-scratch/claude/qwen-split-compute/c23s/chain/bind.json` |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 71 / 0 / 0 (on 8 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 0 / 0 / 0 / 0 |
| (4) masters by view state | closed + native PASS 4; closed, native FAIL 1; closed, native unmeasured 3; routed-failed 3; RTL only (no route yet) 21; hard macro / PHY (allowed model) 5 |
| (5) contract masters absent from the netlist | 10: ot_qfd_x3_mux_native (closed + native PASS), qfd_io_collective_static (RTL only (no route yet)), qfd_io_serdes_static (RTL only (no route yet)), qfd_io_ucie_static (RTL only (no route yet)), qfd_io_xfifo_static (parent: leaves closed, not hardened), qfd_seq_su (closed, native unmeasured), qfd_seq_su_gateway (RTL only (no route yet)), qfd_tile_nl (RTL only (no route yet)), qfd_tt_up4 (closed, native unmeasured), qfd_ucie_gearbox_r10 (RTL only (no route yet)) |
| remaining work units | **118** = 37 masters not closed+native (28 in netlist + 9 absent) + 10 placeholders + 71 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 5 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/c23s/chain/STATUS.log` | 2026-10-15 20:39 PDT | src 711ec663b; GEN 6,385 inst | 2026-10-15 20:39:27 PDN PG OPEN -- DIAGNOSTIC ONLY (GRT/STA continue): islands by class: io_serdes=3 up4_sel_s |
| `repo:results/arch/qwen_split_compute_1014/c16s_terminal/STATUS.log` | 2026-10-15 01:43 PDT | src 675166521; GEN 1,630 inst; GRT overflow 0 | 2026-10-15 01:19:59 STA ff:  |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| qfd_xs_tap | 1 | closed, native FAIL | closed (TT era) | Q-DVM | launch 240.5246 > 220 (1 pins); capture 502.71927 > 190 (4 pins) |  |  |
| qfd_crom_g | 8 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_su_cbuf_g | 8 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_sp_band_lanes | 3 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_tile_nk | 768 | routed-failed | flow failure (no live job) | Q-COMPUTE-ELEM | flow failure (no live job); 2 failed job(s) | n_a, n_b |  |
| qfd_d2d_static | 1 | routed-failed | needs redesign (no live job) | Q-LINK | needs redesign (no live job); 5 failed job(s) | admit_ready, cal_seg, cal_start, cfg_addr, cfg_data, cfg_rx_we, cfg_tx_we, colle |  |
| qfd_sp_su64_sfu | 1 | routed-failed | flow failure (no live job) | Q-COMPUTE-ELEM | flow failure (no live job); 1 failed job(s) | fill_begin, fill_epoch, fill_token, preload_data, preload_epoch, preload_scale,  |  |
| qfd_xcol_e | 24 | RTL only (no route yet) | not started (open) | Q-DVM | 0 of 3 contract leaves closed |  | ph1: STANDARD (route once) |
| qfd_xcol_w | 24 | RTL only (no route yet) | not started (open) | Q-DVM | 0 of 3 contract leaves closed |  | ph1: REPLACE by qfd_xcol_e mirrored (MX/MY), the second copy |
| qfd_band_upper_tp8 | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_clkrx | 1 | RTL only (no route yet) | not started (open) | Q-LINK | no closure-loop job yet |  |  |
| qfd_collective_static_io_production | 1 | RTL only (no route yet) | not started (open) | Q-COLL | 0 of 1 contract leaves closed | die_ps, pkg_s |  |
| qfd_native59_compute_service | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | no closure-loop job yet | complete_slot, host_epoch, host_epoch_valid, host_fused_capability, host_generat |  |
| qfd_port_tiles_0 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| qfd_port_tiles_0_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| qfd_port_tiles_1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_1_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_2 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_2_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_res_train_issue | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_rly_26_NE_9x9 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_seq_su_static | 1 | RTL only (no route yet) | - | - | no registry row | dh |  |
| qfd_sp_res_train_par_0 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_sp_res_train_par_1 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_sp_res_train_par_2 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_sp_vector_memory_par | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| qfd_tt_ctlm_static_s | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 0 of 1 contract leaves closed | fab, kok, kwd, pw |  |
| qkd_embedding_static_core_provider | 1 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | beat_data, beat_epoch, beat_half, beat_scale, beat_slot, beat_token, beat_v, bea |  |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| ot_qfd_x3_mux_native | closed + native PASS | closed (TT era) | Q-DVM | launch 188.7 / capture 154.4 |
| qfd_io_collective_static | RTL only (no route yet) | not started (open) | Q-COLL | no closure-loop job yet |
| qfd_io_serdes_static | RTL only (no route yet) | not started (open) | Q-COLL | no closure-loop job yet |
| qfd_io_ucie_static | RTL only (no route yet) | not started (open) | Q-COLL | no closure-loop job yet |
| qfd_io_xfifo_static | parent: leaves closed, not hardened | not started (open) | Q-COLL | 1 of 1 contract leaves closed |
| qfd_seq_su | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |
| qfd_seq_su_gateway | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | no closure-loop job yet |
| qfd_tile_nl | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 1 of 2 contract leaves closed |
| qfd_tt_up4 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |
| qfd_ucie_gearbox_r10 | RTL only (no route yet) | not started (open) | Q-COLL | no closure-loop job yet |

</details>

Unknowns: no die-level TT/FF STA exists for the current netlist | 3 closed masters have no committed Liberty view to audit: qfd_crom_g, qfd_sp_band_lanes, qfd_su_cbuf_g

## Qwen KV/system die (Q-KVSYS-DIE)

Contract: v1.4.1 bind (kvs7c, HOST north + v1.4 HOST partition) + static IO / static D2D successors; v1.4.2 in progress (complete=True).
Netlist / bind: `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs10-v143p/port_bind_launch.json` (2026-10-15 22:18 PDT, opentallas.qwen_kv_die_port_bind.v1), die.v `/srv/opentallas-scratch/claude/qwen-kvsys/kvs10-v143p/case_kv/die.v`.

| item | value |
|---|---|
| (1) instances / distinct masters | 19,342 / 58 |
| bind verdict | FAIL (not the strict v2 bind) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 6 masters, 132 inst - qkd_d2ds x1 (mismatch), qkd_embgw x1 (mismatch), qkd_host_rt x1 (mismatch), qkd_hslice x64 (mismatch), qkd_hslice_dn x64 (mismatch), qkd_seq x1 (mismatch) |
| (2) masters / instances with no closed view (die must window them) | 34 / 7,707 |
| (2) latest die run on real views | 15 masters / 11,496 inst (of 19,342); `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs8/classify_kvs8.json` |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 25 / 0 / 0 (on 6 masters) |
| (4) masters by view state | closed + native PASS 13; closed, native FAIL 5; parent: leaves closed, not hardened 3; RTL only (no route yet) 31; hard macro / PHY (allowed model) 6 |
| (5) contract masters absent from the netlist | 4: qkd_d2d_static (routed-failed), qkd_embedding_static_core_provider (RTL only (no route yet)), qkd_kv_static_writer_native (closed, native FAIL), qkd_static_kv_return_slots (closed, native FAIL) |
| remaining work units | **78** = 43 masters not closed+native (39 in netlist + 4 absent) + 10 placeholders + 25 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 23 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs10-v143p/STATUS.log` | 2026-10-15 22:18 PDT | src 5f554a767 |  |
| `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs8/STATUS.log` | 2026-10-15 15:36 PDT | src 390b51430; GEN 27,810 inst; GRT overflow 0; TT WNS -1762.84 ps; FF setup -1574.60; FF hold -80.60 ps; PDN SKIPPED (diagnostic) | 2026-10-15 15:36:37 STA ff: tns max -56830016.00 wns max -1574.60 worst slack min -80.60  |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| ot_qkh_lane8 | 2048 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 233.12933 > 220 (30 pins) |  |  |
| qkd_cdc_wleaf | 128 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 396.96114 > 190 (1 pins) |  |  |
| qkd_ctrl_pc | 128 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 273.1797 > 220 (27 pins) |  |  |
| qkd_ectl_a_tp8_epoch_direct | 32 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 220.98393 > 190 (913 pins) |  |  |
| qkd_embgw | 1 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 311.96606 > 220 (1072 pins) | r_ea |  |
| qkd_ahub | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 5 of 5 contract leaves closed |  |  |
| qkd_host_rt | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-DIE | 3 of 3 contract leaves closed | ctrl_completion_fault |  |
| qkd_seq | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 3 of 3 contract leaves closed | r_kvd, r_sd, r_x3_d, t_ar_cr |  |
| qkd_rly_t1 | 4126 | RTL only (no route yet) | - | - | no registry row |  |  |
| qkd_rly_32 | 936 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_1 | 451 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_hgs | 320 | RTL only (no route yet) | - | - | no registry row |  |  |
| qkd_rly_17 | 244 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_1025 | 242 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_1136_<flow> |
| qkd_hss | 192 | RTL only (no route yet) | - | - | no registry row |  |  |
| qkd_rly_33 | 161 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_291 | 154 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_293 | 123 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_2 | 119 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_289 | 85 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_521 | 85 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_1048 | 81 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_1136_<flow> |
| qkd_rly_540 | 66 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_hslice | 64 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | ctrl_completion_v, ctrl_completion_we | ph1: STANDARD (route once) |
| qkd_hslice_dn | 64 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | ctrl_completion_v, ctrl_completion_we | ph1: REPLACE by qkd_hslice mirrored (MX/MY), the second copy |
| qkd_rly_2089 | 61 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 2 x hbfd_rly_1136_<flow> |
| qkd_rst_region | 50 | RTL only (no route yet) | - | - | no registry row |  |  |
| qkd_rly_520 | 24 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_563 | 16 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_36 | 13 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_21 | 12 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_13 | 3 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_astk | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: STANDARD (route once) |
| qkd_astk_n | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: REPLACE by qkd_astk mirrored (MX/MY), the second copy n |
| qkd_land | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: STANDARD (route once) |
| qkd_land_n | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: REPLACE by qkd_land mirrored (MX/MY), the second copy n |
| qkd_rly_284 | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_d2ds | 1 | RTL only (no route yet) | - | - | no registry row | att_tx_payload, att_tx_v, cal_seg, cal_start, cfg_addr, cfg_data, cfg_rx_we, cfg |  |
| qkd_rly_93 | 1 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_136_<flow> |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| qkd_d2d_static | routed-failed | needs redesign (no live job) | Q-LINK | needs redesign (no live job); 3 failed job(s) |
| qkd_embedding_static_core_provider | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |
| qkd_kv_static_writer_native | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 268.01032 > 190 (1 pins) |
| qkd_static_kv_return_slots | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 268.77205 > 220 (290 pins) |

</details>

Unknowns: the strict die_port_bind.py v2 check (undriven / multi-driven net bits, stub bodies, tied inputs) has not been run on this die netlist; the record used is opentallas.qwen_kv_die_port_bind.v1 | the only die-level STA ran with PDN skipped (diagnostic)

## S81 (DeepSeek ROM) die (S-DIE)

Contract: v20 contract + v21 GEN18 candidate (GEN18c static seams/collective, S-BIND bind5) (complete=True).
Netlist / bind: `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/port_bind.json` (2026-10-15 20:40 PDT, opentallas.die_port_bind.v2), die.v `/srv/opentallas-scratch/claude/s81-die-iter/c21h/nl/die.v`.

| item | value |
|---|---|
| (1) instances / distinct masters | 84,387 / 255 |
| bind verdict | FAIL (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 79 / 8,836 |
| (2) latest die run on real views | 18 masters / 31,916 inst (of 84,387); `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/STATUS.log` |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 7 / 0 / 0 (on 2 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 0 / 0 / 0 / 0 |
| (4) masters by view state | closed + native PASS 151; closed, native FAIL 19; closed, native unmeasured 1; routed-failed 2; parent: leaves closed, not hardened 9; RTL only (no route yet) 58; superseded but in netlist 10; hard macro / PHY (allowed model) 5 |
| (5) contract masters absent from the netlist | 38: dsfd_bf_front (RTL only (no route yet)), dsfd_engram_c (closed, native unmeasured), dsfd_engram_mix4_c (parent: leaves closed, not hardened), dsfd_l2r_vr_564x1__hx_E (closed + native PASS), dsfd_l2r_vr_564x1__hx_W (closed + native PASS), dsfd_mtp_hrow_cbe (closed, native FAIL), dsfd_mtp_hrow_cbw (closed, native FAIL), dsfd_mtp_hrow_hub (closed, native FAIL), dsfd_mtp_hrow_ing (closed + native PASS), dsfd_rly_1_WE (closed + native PASS), dsfd_rly_266_SN (closed, native FAIL), dsfd_rly_266_WE (closed, native FAIL), dsfd_rly_283_SN (closed, native FAIL), dsfd_rly_283_WE (closed, native FAIL) ... |
| remaining work units | **167** = 122 masters not closed+native (99 in netlist + 23 absent) + 38 placeholders + 7 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 14 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/STATUS.log` | 2026-10-15 22:02 PDT | src aa9e7cfae; GEN 84,387 inst | 2026-10-16T05:02:20 PLACE rc=0 |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c18/STATUS.log` | 2026-10-15 21:25 PDT | src d8072c747 | 2026-10-16T04:25:09 GEN_FAIL  |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c19b/STATUS.log` | 2026-10-15 19:53 PDT | src d8072c747; GEN 80,654 inst | 2026-10-16T02:47:35 PLACE_FAIL |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c19b/DIAG_STATUS.log` | 2026-10-15 17:44 PDT | GEN 80,654 inst | 2026-10-16T00:44:16 DIAG_PLACE_OK |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21/STATUS.log` | 2026-10-15 14:41 PDT | src f22723676 | 2026-10-15T21:41:39 GEN_FAIL  |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/grt/grt.log` | 2026-10-15 22:16 PDT | GRT RUNNING (extra iteration 3/12) | GRT log |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c19b/grt_p/grt.log` | 2026-10-15 22:01 PDT | GRT RUNNING (extra iteration 7/12) | GRT log |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| dsfd_rly_63_WE | 8471 | closed, native FAIL | closed (TT era) | S-DIE | capture 198.8976 > 190 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_rly_63_WS | 5538 | closed, native FAIL | closed (TT era) | S-DIE | launch 220.61793 > 220 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_qbank_S | 1898 | closed, native FAIL | closed (TT era) | S-DIE | launch 222.07801 > 220 (2 pins); capture 303.47967 > 190 (1 pins) |  |  |
| ot_s81_cfg7_seq | 1898 | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 221.58581 > 220 (3 pins); capture 300.55874 > 190 (189 pins); 20 combinational pins |  |  |
| dsfd_rly_266_EW | 1521 | closed, native FAIL | closed (TT era) | S-DIE | launch 237.41262 > 220 (126 pins); capture 271.72626 > 190 (1 pins) |  | ph1: REBIND NOW to 1 x dsfd_rly_283_EW |
| dsfd_rly_283_EW | 1521 | closed, native FAIL | closed (TT era) | S-DIE | launch 243.32915 > 220 (132 pins); capture 293.90512 > 190 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_node_LLfd | 1265 | closed, native FAIL | closed (TT era) | S-DIE | capture 207.34828 > 190 (1 pins) |  | ph1: REBIND NOW to dsfd_node_LLfu (identical RTL) |
| dsfd_node_NNfu | 1265 | closed, native FAIL | closed (TT era) | S-DIE | capture 191.90194 > 190 (1 pins) |  | ph0: CANONICAL (keep, replicate) |
| dsfd_node_LLfu | 1024 | closed, native FAIL | closed (TT era) | S-DIE | capture 246.41196 > 190 (1 pins) |  | ph0: CANONICAL (keep, replicate) |
| dsfd_node_NNfd | 1024 | closed, native FAIL | closed (TT era) | S-DIE | capture 242.6733 > 190 (1 pins) |  | ph1: REBIND NOW to dsfd_node_NNfu (identical RTL) |
| dsfd_rly_63_WN | 993 | closed, native FAIL | closed (TT era) | S-DIE | launch 223.74778 > 220 (2 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_rly_63_SE | 636 | closed, native FAIL | closed (TT era) | S-DIE | capture 216.96895 > 190 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_rly_66_EW | 236 | closed, native FAIL | closed (TT era) | S-DIE | capture 200.14293 > 190 (1 pins) |  | ph1: REBIND NOW to 1 x dsfd_rly_68_EW |
| dsfd_cfifo | 128 | closed, native FAIL | closed (TT era) | S-ELEM-A | launch 263.29628 > 220 (252 pins); capture 205.69189 > 190 (1 pins) |  |  |
| dsfd_node_LLd | 128 | closed, native FAIL | closed (TT era) | S-DIE | capture 267.72869 > 190 (1 pins) |  |  |
| dsfd_rly_66_ES | 127 | closed, native FAIL | closed (TT era) | S-DIE | capture 243.78442 > 190 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_rly_66_WS | 9 | closed, native FAIL | closed (TT era) | S-DIE | capture 195.00153 > 190 (1 pins) |  | ph0: STANDARD (keep, replicate) |
| dsfd_xstg_515 | 2 | closed, native FAIL | closed (TT era) | S-DIE | capture 355.9881 > 190 (515 pins) |  |  |
| dsfd_m2l_vr_68x11__hr_E4 | 1 | closed, native FAIL | closed (TT era) | S-DIE | launch 380.2777 > 220 (13 pins); capture 485.08003 > 190 (22 pins) |  | ph1: REBIND NOW to dsfd_m2l_vr_68x11__hr_W1 (identical RTL) |
| dsfd_hstnh_515 | 16 | closed, native unmeasured | closed (TT era) | S-DIE | NO_VIEW |  | ph0: KEEP (different RTL body from the family generator; not |
| dsfd_bf_front_static | 519 | routed-failed | needs redesign (no live job) | S-ELEM-B | needs redesign (no live job); 3 failed job(s) |  |  |
| dsfd_host_c | 1 | routed-failed | needs redesign (no live job) | S-ELEM-B | needs redesign (no live job); 1 failed job(s) |  |  |
| dsfd_bk_collector_c1 | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 2 of 2 contract leaves closed |  |  |
| dsfd_ctrl | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 2 of 2 contract leaves closed |  |  |
| dsfd_sp_capture_c | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-A | 6 of 6 contract leaves closed |  |  |
| dsfd_sp_collective_static_c | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 1 of 1 contract leaves closed |  |  |
| dsfd_sp_gather_c | 1 | parent: leaves closed, not hardened | not started (open) | S-GATHER | 1 of 1 contract leaves closed |  |  |
| dsfd_sp_pq_n | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 3 of 3 contract leaves closed | f_iss |  |
| dsfd_sp_vm | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-A | 26 of 26 contract leaves closed | f_mx_rq, f_mx_rqv, f_mx_wq, f_mx_wqd, f_mx_wqm, f_mx_wqv |  |
| dsfd_svc_c | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 10 of 10 contract leaves closed |  |  |
| dsfd_wfc_stg | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 3 of 3 contract leaves closed |  |  |
| dsfd_bf_col | 1038 | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |  |  |
| dsfd_stnv_538x1 | 932 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_536_SN | 898 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sstn_e0e1c0c1si_x2 | 746 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_stnh_538x1 | 628 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_38_WN | 519 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_s81_cfg7_seq_bfp | 519 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sstn_e0c0si_x2 | 476 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_536_SW | 403 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sstn_e0e1c0c1sinf_x2 | 99 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_536_EN | 79 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_17 | 76 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_15_WE | 73 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_17 | 69 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_63_EW | 44 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_16 | 31 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sstn_e0c0_x2 | 30 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sstn_e0c0sinf_x2 | 29 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_66_WE | 26 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_3056 | 11 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_2164 | 10 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_1 | 8 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_s81_pq_rwbc15 | 8 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_12 | 5 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_48 | 5 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_s81_pq_rwbc2 | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_16 | 2 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_bk_selector_c1 | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | 3 of 4 contract leaves closed |  |  |
| dsfd_hstnh_1027 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_138_sp10 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_138_sp3 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_207_sp13 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_207_sp2 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp0 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp1 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp11 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp12 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp4 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp5 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp8 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_276_sp9 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_292 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_2_sp6 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_3 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_512 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_69_sp7 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnh_84 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_292 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_692 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_hstnv_84 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_l2r_vr_1100x1__hx_E | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_l2r_vr_1100x1__hx_W | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_lkck_EE | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_rly_15_NE | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| dsfd_sp_hc_c | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | 19 of 27 contract leaves closed |  |  |
| dsfd_sp_hc_t | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | 16 of 20 contract leaves closed |  |  |
| dsfd_sp_su_c | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | 15 of 18 contract leaves closed |  |  |
| dsfd_stage_seq_static_c8 | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |  |  |
| dsfd_stnv_70x2 | 580 | superseded but in netlist | superseded | - | 2 x dsfd_stnv_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph1: REBIND NOW to 2 x dsfd_stnv_86x1 |
| dsfd_stnv_70x4 | 321 | superseded but in netlist | superseded | - | 4 x dsfd_stnv_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph1: REBIND NOW to 4 x dsfd_stnv_86x1 |
| dsfd_stnv_70x3 | 243 | superseded but in netlist | superseded | - | 3 x dsfd_stnv_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph1: REBIND NOW to 3 x dsfd_stnv_86x1 |
| dsfd_stnh_70x2 | 210 | superseded but in netlist | superseded | - | 2 x dsfd_stnh_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph0: KEEP (different RTL body from the family generator; not |
| dsfd_stnh_70x4 | 135 | superseded but in netlist | superseded | - | 4 x dsfd_stnh_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph0: KEEP (different RTL body from the family generator; not |
| dsfd_stnh_70x3 | 12 | superseded but in netlist | superseded | - | 3 x dsfd_stnh_70x1 along the flow (die generator --stn70-split, tools/dsrom_s81_fulldie.py |  | ph0: KEEP (different RTL body from the family generator; not |
| dsfd_lkck_SW | 3 | superseded but in netlist | superseded | - | die-top wire (generator --lkck-wire: tx-chain tail fo0 drives the link macro ck directly) |  | ph0: CANONICAL (keep, replicate) |
| dsfd_lkck_SE | 2 | superseded but in netlist | superseded | - | die-top wire (generator --lkck-wire: tx-chain tail fo0 drives the link macro ck directly) |  | ph1: REPLACE by replica of dsfd_lkck_SW (identical RTL) |
| dsfd_lkck_NE | 1 | superseded but in netlist | superseded | - | die-top wire (generator --lkck-wire: tx-chain tail fo0 drives the link macro ck directly) |  | ph1: REPLACE by replica of dsfd_lkck_SW (identical RTL) |
| dsfd_lkck_NW | 1 | superseded but in netlist | superseded | - | die-top wire (generator --lkck-wire: tx-chain tail fo0 drives the link macro ck directly) |  | ph1: REPLACE by replica of dsfd_lkck_SW (identical RTL) |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| dsfd_bf_front | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| dsfd_engram_c | closed, native unmeasured | closed (TT era) | S-ELEM-C | NO_VIEW |
| dsfd_engram_mix4_c | parent: leaves closed, not hardened | not started (open) | S-ELEM-C | 11 of 11 contract leaves closed |
| dsfd_l2r_vr_564x1__hx_E | closed + native PASS | closed (TT era) | S-DIE | launch 99.3 / capture 120.2 |
| dsfd_l2r_vr_564x1__hx_W | closed + native PASS | closed (TT era) | S-DIE | launch 98.5 / capture 117.2 |
| dsfd_mtp_hrow_cbe | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 398.99666 > 220 (971 pins); capture 505.86272 > 190 (870 pins) |
| dsfd_mtp_hrow_cbw | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 422.79547 > 220 (991 pins); capture 440.43333 > 190 (962 pins) |
| dsfd_mtp_hrow_hub | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 315.99785 > 220 (202 pins); capture 357.34624 > 190 (2436 pins) |
| dsfd_mtp_hrow_ing | closed + native PASS | closed (TT era) | S-ELEM-B | launch 155.7 / capture 119.5 |
| dsfd_rly_1_WE | closed + native PASS | closed (TT era) | S-DIE | launch 192.1 / capture 79.8 |
| dsfd_rly_266_SN | closed, native FAIL | closed (TT era) | S-DIE | launch 228.94545 > 220 (18 pins); capture 204.6891 > 190 (1 pins) |
| dsfd_rly_266_WE | closed, native FAIL | closed (TT era) | S-DIE | launch 222.16645 > 220 (1 pins); capture 234.10383 > 190 (1 pins) |
| dsfd_rly_283_SN | closed, native FAIL | closed (TT era) | S-DIE | launch 226.89903 > 220 (10 pins); capture 199.50453 > 190 (1 pins) |
| dsfd_rly_283_WE | closed, native FAIL | closed (TT era) | S-DIE | launch 222.74221 > 220 (7 pins); capture 235.91917 > 190 (1 pins) |
| dsfd_rly_2_SN | closed + native PASS | closed (TT era) | S-DIE | launch 196.2 / capture 78.4 |
| dsfd_rly_54_EW | closed + native PASS | closed (TT era) | S-DIE | launch 218.4 / capture 165.9 |
| dsfd_rly_68_EW | closed + native PASS | closed (TT era) | S-DIE | launch 219.8 / capture 160.6 |
| dsfd_sstn_e0c0 | closed + native PASS | closed (TT era) | S-DIE | launch 181.5 / capture 182.9 |
| dsfd_sstn_e0c0si | closed + native PASS | closed (TT era) | S-DIE | launch 180.4 / capture 177.7 |
| dsfd_sstn_e0c0sinf | closed, native FAIL | closed (TT era) | S-DIE | capture 216.18467 > 190 (1 pins) |
| dsfd_sstn_e0e1c0c1sinf | closed + native PASS | closed (TT era) | S-DIE | launch 180.4 / capture 183.0 |
| ot_mtp_p2_prefix_path | closed, native unmeasured | closed (TT era) | S-ELEM-B | NO_VIEW |
| ot_s81_cfg7_seq_bf | closed, native FAIL | closed (TT era) | S-ELEM-B | capture 238.89939 > 190 (234 pins); 20 combinational pins |
| ot_s81_embed_expand | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| ot_s81_engram_dispatch | RTL only (no route yet) | not started (open) | S-ELEM-C | no closure-loop job yet |
| ot_s81_hc_caq | closed, native FAIL | closed (TT era) | S-ELEM-B | capture 253.62576 > 190 (1 pins) |
| ot_s81_hc_ccf | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 408.2241 > 220 (1502 pins); capture 544.34652 > 190 (1848 pins) |
| ot_s81_hc_ccr | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 264.06348 > 220 (27 pins); capture 191.644 > 190 (1 pins) |
| ot_s81_hc_cntree | closed + native PASS | closed (TT era) | S-ELEM-B | launch 149.5 / capture 128.6 |
| ot_s81_hc_crx | closed + native PASS | closed (TT era) | S-ELEM-B | launch 217.7 / capture 133.3 |
| ot_s81_hc_cseq | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 305.29711 > 220 (88 pins) |
| ot_s81_hc_pad_f8 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 155.3 / capture 125.6 |
| ot_s81_hc_pad_fv4fd5r2 | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| ot_s81_hc_pad_meta2 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 149.2 / capture 110.0 |
| ot_s81_hc_pad_r5 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 153.7 / capture 114.0 |
| ot_s81_hcx_controller | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| ot_s81_hcx_gatherpack | RTL only (no route yet) | not started (open) | S-GATHER | no closure-loop job yet |
| ot_s81_hcx_projection_leaf | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |

</details>

Unknowns: no die-level TT/FF STA exists for the current netlist | 1 closed masters have no committed Liberty view to audit: dsfd_hstnh_515

## HBM accelerator die (H-DIE)

Contract: v15.1 source contract (+ v14 die masters carried until re-contracted) (complete=False).
Netlist / bind: `repo:results/arch/hbm_die_v15/source_contract/contract.json` (645d2cf9e 2026-10-15T13:55:13-07:00, opentallas.hbm.actual-v15-source-contract.v1), die.v `(no full HBM die netlist: v15 source contract instances)`.

| item | value |
|---|---|
| (1) instances / distinct masters | 83 / 39 |
| bind verdict | FAIL_UNBOUND_NATIVE_PORTS (not the strict v2 bind) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 33 / 74 |
| (2) view inventory by status (mm2) | {"REAL": 53.3, "NO_CONTRACT_INSTANCE": 376.0, "PARTITION": 98.7, "INCOMPLETE": 0.7, "SYNTH": 6.5} (`results/arch/hbm_die_v15/views_v5/inventory.json` 259a3600a 2026-10-15T13:56:20-07:00) |
| die chain readiness | {"masters": 38, "instances": 83, "verdict": "NOT LAUNCHED: 37/38 current source-contract masters (79/83 instances) lack composed physical views. Source contract is incomplete, not a full die: native SM/HC/host joins and real view composition remain open.", "masters_with_view": ["ot_hbm3e_phy_v41x_aw |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 1070 / 0 / 0 (on 36 masters) |
| (3) exposed die inputs (views_v5) | 1,070 ports / 177,247 bits; by owner H-DIE 816/90,772; H-SU 85/16,763; H-SM 77/60,630; H-COLL+IDX 47/7,346; H-HARDEN 36/1,416; H-DIE (host_cp) 9/320 |
| (3) after the service engine (1815) | {"delivery": {"ports": 48, "bits": 36048, "status": null}, "svc": {"ports": 748, "bits": 54528, "status": null}, "phy": {"ports": 20, "bits": 196, "status": null}, "engine_new_inputs": {"ports": 288, "bits": 17504}} |
| (3) unresolved source ports (source contract) | 1,660; pin-only placeholders 0; service-band rejections 21 |
| contract qualification | {"native_complete": false, "pins": false, "station_benches": true, "clock_views": false, "TT": false, "FF": false, "DRC": false} |
| (4) masters by view state | closed + native PASS 1; closed, native FAIL 4; parent: leaves closed, not hardened 2; RTL only (no route yet) 27; superseded but in netlist 4; hard macro / PHY (allowed model) 1 |
| (5) contract masters absent from the netlist | 16: hfd_cmdproc (parent: leaves closed, not hardened), hfd_hc (closed, native unmeasured), hfd_hc_eng (RTL only (no route yet)), hfd_hgi_am (parent: leaves closed, not hardened), hfd_host_slab (RTL only (no route yet)), hfd_idx_score_native_grid (RTL only (no route yet)), hfd_lk_ep (routed-failed), hfd_loader (closed, native unmeasured), hfd_quant (closed, native unmeasured), hfd_serdes_slab (RTL only (no route yet)), hfd_sm (RTL only (no route yet)), hfd_stn_v15_cc2224 (RTL only (no route yet)), hfd_stn_v15_cc2248 (RTL only (no route yet)), hgi_mtp_native (closed, native FAIL) ... |
| remaining work units | **1,139** = 53 masters not closed+native (37 in netlist + 16 absent) + 16 placeholders + 1070 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 9 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc1tb:/srv/opentallas-scratch/claude/hdie-1705/diecase_b/out/run.log` | 2026-10-15 20:03 PDT | case service_engine+SM (whole HBM->SM datapath): {'ot_hbm3e_phy_rc_e8p5': 4, 'ot_hbm_svc_pc_ctrl_leaf': 128, 'ot_hbm_svc_sm_group': 32, 'ot_hbm_accel_smh_static': 32}; GRT overflow 0; TT WNS -237369.42 ps; FF hold -185.95 ps | OT_DONE |
| `ot-epyc1tb:/srv/opentallas-scratch/claude/hdie-1705/diecase_a/out/run.log` | 2026-10-15 19:43 PDT | case service_engine+SM (whole HBM->SM datapath): {'ot_hbm3e_phy_rc_e8p5': 4, 'ot_hbm_svc_pc_ctrl_leaf': 128, 'ot_hbm_svc_sm_group': 32, 'ot_hbm_accel_smh_static': 32}; GRT overflow 0; TT WNS -237468.36 ps; FF hold -657.66 ps | OT_DONE |
| `results/arch/hbm_die_v15/views_v5/pcrow_c_die_clock/run_summary.txt` | e30a0484c 2026-10-15T18:02:47-07:00 | {"kind": "region_run", "grt_s": ["17"], "tns_max": ["0.00"]} | committed receipt |
| `results/arch/hbm_die_v15/grt27_collected/receipt.json` | 2e47f6a43 2026-10-15T00:07:58-07:00 | {"kind": "full_grt", "status": "FAIL_CONGESTION_DIAGNOSTIC_HISTORICAL_MODEL", "overflow": 51123} | committed receipt |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| hfd_hgi_vm_calendar_NE | 1 | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 228.95632 > 190 (1 pins) | calendar_NE.cfg_we[1b], calendar_NE.cfg_addr[10b], calendar_NE.cfg_data[256b], c | ph1: REBIND NOW to hfd_hgi_vm_calendar_SE (identical RTL) |
| hfd_hgi_vm_calendar_NW | 1 | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 257.46845 > 190 (1 pins) | calendar_NW.cfg_we[1b], calendar_NW.cfg_addr[10b], calendar_NW.cfg_data[256b], c |  |
| hfd_hgi_vm_calendar_SE | 1 | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 228.95632 > 190 (1 pins) | calendar_SE.cfg_we[1b], calendar_SE.cfg_addr[10b], calendar_SE.cfg_data[256b], c | ph0: CANONICAL (keep, replicate) |
| hfd_hgi_vm_calendar_SW | 1 | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 268.06103 > 190 (1 pins) | calendar_SW.cfg_we[1b], calendar_SW.cfg_addr[10b], calendar_SW.cfg_data[256b], c |  |
| ot_hgi_sfu_scheduled_engine | 4 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed | hb_sfu_SW.rst_lane_n[16b], hb_sfu_SW.rst_map_n[16b], hb_sfu_SW.cfg_we[1b], hb_sf |  |
| hfd_ckgen | 1 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed |  |  |
| ot_hbm_vm_lg_static_split | 8 | RTL only (no route yet) | not started (open) | H-ELEM-A | no closure-loop job yet |  |  |
| ot_hbm_su_static_vm_ports | 4 | RTL only (no route yet) | not started (open) | H-ELEM-B | no closure-loop job yet | hb_su_SW.su_rq[136b], hb_su_SW.su_wq[2248b], hb_su_SE.su_rq[136b], hb_su_SE.su_w |  |
| ot_hbm_svc_static_vm_delivery | 4 | RTL only (no route yet) | not started (open) | HBM-V15-HARDEN | no closure-loop job yet | delivery_SW.begin_v[1b], delivery_SW.begin_bank[1b], delivery_SW.begin_epoch[16b |  |
| ot_hbm_vm_lg_static_split_term | 4 | RTL only (no route yet) | - | - | no registry row | lg_SW_2.local_rq[136b], lg_SW_2.local_wq[2248b], lg_SE_2.local_rq[136b], lg_SE_2 |  |
| ot_hgi_dma_back_static | 4 | RTL only (no route yet) | - | - | no registry row | hb_dbk_SW.cycle[32b], hb_dbk_SW.mv_v[1b], hb_dbk_SW.mv[227b], hb_dbk_SW.issue_at |  |
| ot_hfd_coll_q2_static | 3 | RTL only (no route yet) | not started (open) | H-COLL | 2 of 3 contract leaves closed | hb_coll_SE.qid[2b], hb_coll_SE.hgi_start[1b], hb_coll_SE.hgi_start_pc[6b], hb_co |  |
| hfd_svc_v15_SE_s0 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s0.open_v[4b], svc_SE_s0.open_bank[4b], svc_SE_s0.open_epoch[64b], svc_SE | ph1: REPLACE by replica of hfd_svc_v15_SW_s0 (identical RTL) |
| hfd_svc_v15_SE_s1 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s1.open_v[5b], svc_SE_s1.open_bank[5b], svc_SE_s1.open_epoch[80b], svc_SE | ph1: REPLACE by replica of hfd_svc_v15_SW_s1 (identical RTL) |
| hfd_svc_v15_SE_s2 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s2.open_v[4b], svc_SE_s2.open_bank[4b], svc_SE_s2.open_epoch[64b], svc_SE | ph1: REPLACE by replica of hfd_svc_v15_SW_s2 (identical RTL) |
| hfd_svc_v15_SE_s3 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s3.open_v[5b], svc_SE_s3.open_bank[5b], svc_SE_s3.open_epoch[80b], svc_SE |  |
| hfd_svc_v15_SE_s4 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s4.open_v[4b], svc_SE_s4.open_bank[4b], svc_SE_s4.open_epoch[64b], svc_SE |  |
| hfd_svc_v15_SE_s5 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s5.open_v[4b], svc_SE_s5.open_bank[4b], svc_SE_s5.open_epoch[64b], svc_SE |  |
| hfd_svc_v15_SE_s6 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SE_s6.open_v[3b], svc_SE_s6.open_bank[3b], svc_SE_s6.open_epoch[48b], svc_SE |  |
| hfd_svc_v15_SW_s1 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s1.open_v[5b], svc_SW_s1.open_bank[5b], svc_SW_s1.open_epoch[80b], svc_SW | ph0: CANONICAL (keep, replicate) |
| hfd_svc_v15_SW_s2 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s2.open_v[4b], svc_SW_s2.open_bank[4b], svc_SW_s2.open_epoch[64b], svc_SW | ph0: CANONICAL (keep, replicate) |
| hfd_svc_v15_SW_s3 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s3.open_v[4b], svc_SW_s3.open_bank[4b], svc_SW_s3.open_epoch[64b], svc_SW |  |
| hfd_svc_v15_SW_s5 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s5.open_v[4b], svc_SW_s5.open_bank[4b], svc_SW_s5.open_epoch[64b], svc_SW |  |
| hfd_svc_v15_SW_s6 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s6.open_v[4b], svc_SW_s6.open_bank[4b], svc_SW_s6.open_epoch[64b], svc_SW |  |
| hfd_svc_v15_SW_s7 | 2 | RTL only (no route yet) | - | - | no registry row | svc_SW_s7.open_v[4b], svc_SW_s7.open_bank[4b], svc_SW_s7.open_epoch[64b], svc_SW |  |
| hfd_hgi_vms_static_NE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 0 of 4 contract leaves closed | hb_vms_NE.rq[408b], hb_vms_NE.wq[4496b] | ph1: STANDARD (route once, replicate) |
| hfd_hgi_vms_static_NW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 0 of 4 contract leaves closed | hb_vms_NW.cq[1352b], hb_vms_NW.rq[272b], hb_vms_NW.wq[2248b] | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 0 of 4 contract leaves closed | hb_vms_SE.rq[136b] | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 0 of 4 contract leaves closed | hb_vms_SW.cq[338b], hb_vms_SW.rq[136b] | ph1: MERGE into the family master (no route of its own); NOT |
| ot_hbm_argmax_static_sw | 1 | RTL only (no route yet) | - | - | no registry row | hb_argmax.die_id[8b], hb_argmax.go[1b], hb_argmax.mode[1b], hb_argmax.imm_a[18b] |  |
| ot_hbm_idx_client_static_sw | 1 | RTL only (no route yet) | - | - | no registry row | hb_idx.program_we[1b], hb_idx.program_addr[8b], hb_idx.program_data[256b], hb_id |  |
| ot_hfd_coll_q3_static | 1 | RTL only (no route yet) | not started (open) | H-COLL | 2 of 3 contract leaves closed | hb_coll_SW.qid[2b], hb_coll_SW.hgi_start[1b], hb_coll_SW.hgi_start_pc[6b], hb_co |  |
| ot_hgi_qdq_host_static | 1 | RTL only (no route yet) | - | - | no registry row | hb_quant_NW.cfg_v[1b], hb_quant_NW.cfg_target[8b], hb_quant_NW.cfg_addr[12b], hb |  |
| hfd_svc_v15_SE_s7 | 2 | superseded but in netlist | superseded | Claude:HBM-V15-HARDEN | 128 die-level ot_hbm_svc_static_pc leaf instances; service bands are soft groups | svc_SE_s7.open_v[2b], svc_SE_s7.open_bank[2b], svc_SE_s7.open_epoch[32b], svc_SE |  |
| hfd_svc_v15_SE_s8 | 2 | superseded but in netlist | superseded | Claude:HBM-V15-HARDEN | 128 die-level ot_hbm_svc_static_pc leaf instances; service bands are soft groups | svc_SE_s8.open_v[1b], svc_SE_s8.open_bank[1b], svc_SE_s8.open_epoch[16b], svc_SE |  |
| hfd_svc_v15_SW_s0 | 2 | superseded but in netlist | superseded | Claude:HBM-V15-HARDEN | 128 die-level ot_hbm_svc_static_pc leaf instances; service bands are soft groups | svc_SW_s0.open_v[4b], svc_SW_s0.open_bank[4b], svc_SW_s0.open_epoch[64b], svc_SW | ph0: CANONICAL (keep, replicate) |
| hfd_svc_v15_SW_s4 | 2 | superseded but in netlist | superseded | Claude:HBM-V15-HARDEN | 128 die-level ot_hbm_svc_static_pc leaf instances; service bands are soft groups | svc_SW_s4.open_v[3b], svc_SW_s4.open_bank[3b], svc_SW_s4.open_epoch[48b], svc_SW |  |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| hfd_cmdproc | parent: leaves closed, not hardened | not started (open) | H-DIE | 9 of 9 contract leaves closed |
| hfd_hc | closed, native unmeasured | closed (TT era) | H-DIE | NO_VIEW |
| hfd_hc_eng | RTL only (no route yet) | not started (open) | H-DIE | 1 of 3 contract leaves closed |
| hfd_hgi_am | parent: leaves closed, not hardened | not started (open) | H-DIE | 3 of 3 contract leaves closed |
| hfd_host_slab | RTL only (no route yet) | not started (open) | H-DIE | no closure-loop job yet |
| hfd_idx_score_native_grid | RTL only (no route yet) | not started (open) | H-IDX | 0 of 1 contract leaves closed |
| hfd_lk_ep | routed-failed | needs redesign (no live job) | H-ELEM-A | needs redesign (no live job); 13 failed job(s) |
| hfd_loader | closed, native unmeasured | closed (TT era) | H-DIE | NO_VIEW |
| hfd_quant | closed, native unmeasured | closed (TT era) | H-ATTQ | NO_VIEW |
| hfd_serdes_slab | RTL only (no route yet) | not started (open) | H-DIE | no closure-loop job yet |
| hfd_sm | RTL only (no route yet) | not started (open) | H-ELEM-A | 4 of 9 contract leaves closed |
| hfd_stn_v15_cc2224 | RTL only (no route yet) | not started (open) | H-DIE | no closure-loop job yet |
| hfd_stn_v15_cc2248 | RTL only (no route yet) | not started (open) | H-DIE | no closure-loop job yet |
| hgi_mtp_native | closed, native FAIL | closed (TT era) | H-DIE | launch 266.0817 > 220 (239 pins); capture 345.51357 > 190 (51 pins) |
| ot_hbm_idx_client_static | parent: leaves closed, not hardened | not started (open) | H-IDX | 1 of 1 contract leaves closed |
| ot_hbm_idx_scheduled_static | parent: leaves closed, not hardened | not started (open) | H-IDX | 1 of 1 contract leaves closed |

</details>

Unknowns: HBM has no full-die netlist: SM (32 tiles, ~362 mm2), attention halves, LK EP, host/SerDes are carried from the v14 die and are not instances of the v15 source contract | the strict die_port_bind.py v2 check (undriven / multi-driven net bits, stub bodies, tied inputs) has not been run on this die netlist; the record used is opentallas.hbm.actual-v15-source-contract.v1

## Largest unknowns

- HBM: there is no full-die netlist. The v15 source contract has 83 instances / 39 masters; the 32 SM tiles (~362 mm2), attention halves, LK EP and host/SerDes are carried from v14 and are not instances. Only the PHY + 128 PC region (53.3 mm2) is on real views; the largest die case (diecase_b, SYNTH ETMs) is TT -237,369 ps. Integration of the SM has not started, so its failures are not yet visible.
- S81: the die physical run binds closed views for only 18 masters / 31,916 of 84,387 instances (OT_VIEW_BINDING); the other closed masters enter as generated abstracts, so their die-context timing is unmeasured. No S81 die STA has ever run (c19b GRT in extra iteration 3/12), and the adopted wide hub C5 (rm5_p1973) needs a new GEN, so the netlist will change again.
- Qwen compute: qfd_tile_nk (768 of 1,638 instances) has no closed view and is being re-packed (64 lanes); 71 open inputs come from 7 producers that are not built; no compute-die STA has ever produced numbers (C16s STA flow error, C23s in PDN); contract v1.3 predates the fpq_s6 homes, so the 10 contract masters absent from the netlist may be stale names rather than missing blocks.
- Qwen KV/system: the strict die_port_bind.py v2 check has never run on the KV netlist (the KV tool does not count undriven / multi-driven bits); the measured open inputs are 27 (the logged "25" is arithmetic after the HOST fix, not a bind). The only die STA is PDN-skipped (TT -1,762.84 ps, 299,285 real-to-real violators). The v1.4.3 PV-wide pair (new masters, 1,024 SRAM macros) is not yet in the netlist.
- Native audit: closed views that fail the native launch/capture budget (compute 1, KV 4, S81 19 in the netlist, HBM 4) need re-kits; each one found at die level so far has cost a re-route.

