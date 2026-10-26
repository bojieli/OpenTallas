# Die completeness, 2026-10-16 02:12 PDT

Measured inventory per die (tools/die_completeness.py). Every number comes from a bind record, the element registry, a native pin audit of the committed view, or a die-run log; the source of each is listed. Re-run daily.

## Summary

| die | netlist instances | distinct masters | non-real-RTL instances | instances without a closed view | open inputs (ports) | netlist masters closed+native PASS | netlist masters not closed+native | contract masters absent | remaining work units | masters left after DEDUPE ph-1 rebinds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen compute die | 1,638 | 37 | 0 | 840 | 71 | 4 | 28 | 4 | **137** | 27 of 32 |
| Qwen KV/system die | 20,610 | 53 | 0 | 8,975 | 25 | 13 | 39 | 3 | **70** | 19 of 42 |
| S81 (DeepSeek ROM) die | 84,387 | 255 | 0 | 8,836 | 7 | 164 | 86 | 36 | **146** | 92 of 103 |
| HBM accelerator die | 1,418 | 55 | 0 | 403 | 17 | 8 | 43 | 24 | **108** | 61 of 67 |

Remaining work units = masters not closed + native PASS (netlist and contract-absent, hard macros excluded) + placeholders to replace (non-real-RTL masters + contract masters absent from the netlist) + inputs to bind (unconnected input ports + width mismatches + die ports missing in RTL). A contract master absent from the netlist counts once to close it (unless already closed + native PASS) and once to integrate it. HBM additionally carries its exposed input ports and unresolved source ports, listed per die below.

## Qwen compute die (Q-COMPUTE-DIE)

Contract: v1.4 (Q-NETLIST 2026-10-16): r2h floorplan (575.3 mm2), dp tree hosts, held45 tile, system face; strict port-bind PASS (complete=True).
Netlist / bind: `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/r2b2/chain/port_bind/port_bind.json` (2026-10-15 22:57 PDT, opentallas.die_port_bind.v2), die.v `/srv/opentallas-scratch/claude/qwen-split-compute/r2b2/chain/case_r22k/die.v`.

| item | value |
|---|---|
| (1) instances / distinct masters | 1,638 / 37 |
| bind verdict | FAIL (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 24 / 840 |
| (2) latest die run on real views | 8 masters / 793 inst (of 1,637); `/srv/opentallas-scratch/claude/qwen-split-compute/r2b2/chain/bind.json` |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 71 / 0 / 30 (on 8 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 0 / 0 / 0 / 0 |
| (4) masters by view state | closed + native PASS 4; closed, native FAIL 1; closed, native unmeasured 3; routed-failed 3; parent: leaves closed, not hardened 3; RTL only (no route yet) 18; hard macro / PHY (allowed model) 5 |
| (5) contract masters absent from the netlist | 4: qfd_embedding_word_provider (RTL only (no route yet)), qfd_seq_su_gateway (RTL only (no route yet)), qfd_sys_face (RTL only (no route yet)), qfd_tile_nl (RTL only (no route yet)) |
| remaining work units | **137** = 32 masters not closed+native (28 in netlist + 4 absent) + 4 placeholders + 101 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 5 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/r2b2/chain/STATUS.log` | 2026-10-16 01:04 PDT | src b61ebe451; GEN 6,385 inst; GRT overflow 0; TT WNS -13341309.00 ps; FF setup -13306412.00; FF hold -79.95 ps | 2026-10-16 01:01:08 STA ff: tns max -16203448320.00 wns max -13306412.00 worst slack min -79.95  |
| `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/c23s/chain/STATUS.log` | 2026-10-15 22:47 PDT | src 711ec663b; GEN 6,385 inst; GRT overflow 0; TT WNS -19511688.00 ps; FF setup -19471496.00; FF hold -79.95 ps | 2026-10-15 22:44:49 STA ff: tns max -24327211008.00 wns max -19471496.00 worst slack min -79.95  |
| `repo:results/arch/qwen_split_compute_1014/c16s_terminal/STATUS.log` | 2026-10-15 01:43 PDT | src 675166521; GEN 1,630 inst; GRT overflow 0 | 2026-10-15 01:19:59 STA ff:  |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| qfd_xs_tap | 1 | closed, native FAIL | closed (TT era) | Q-DVM | launch 240.5246 > 220 (1 pins); capture 502.71927 > 190 (4 pins) |  |  |
| qfd_crom_g | 8 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_su_cbuf_g | 8 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_sp_band_lanes | 3 | closed, native unmeasured | closed (TT era) | Q-COMPUTE-ELEM | NO_VIEW |  |  |
| qfd_tile_nk | 768 | routed-failed | flow failure (no live job) | Q-TILE45 | flow failure (no live job); 2 failed job(s) | n_a, n_b |  |
| qfd_d2d_static | 1 | routed-failed | failed, re-running | Q-DVM+LINK | failed, re-running; 5 failed job(s) | admit_ready, cal_seg, cal_start, cfg_addr, cfg_data, cfg_rx_we, cfg_tx_we, colle |  |
| qfd_sp_su64_sfu | 1 | routed-failed | flow failure (no live job) | Q-COMPUTE-ELEM | flow failure (no live job); 1 failed job(s) | fill_begin, fill_epoch, fill_token, preload_data, preload_epoch, preload_scale,  |  |
| qfd_band_upper_tp8 | 4 | parent: leaves closed, not hardened | not started (open) | Q-ELEM | 1 of 1 contract leaves closed |  |  |
| qfd_collective_static_io_production | 1 | parent: leaves closed, not hardened | not started (open) | Q-DVM+LINK | 2 of 2 contract leaves closed | die_ps, pkg_s |  |
| qfd_sp_vector_memory_par | 1 | parent: leaves closed, not hardened | not started (open) | Q-VMWB | 5 of 5 contract leaves closed |  |  |
| qfd_xcol_e | 24 | RTL only (no route yet) | not started (open) | Q-DVM | 0 of 3 contract leaves closed |  | ph1: STANDARD (route once) |
| qfd_xcol_w | 24 | RTL only (no route yet) | not started (open) | Q-DVM | 0 of 3 contract leaves closed |  | ph1: REPLACE by qfd_xcol_e mirrored (MX/MY), the second copy |
| qfd_clkrx | 1 | RTL only (no route yet) | not started (open) | Q-LINK | no closure-loop job yet |  |  |
| qfd_native59_compute_service | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | no closure-loop job yet | complete_slot, host_epoch, host_epoch_valid, host_fused_capability, host_generat |  |
| qfd_port_tiles_0 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| qfd_port_tiles_0_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| qfd_port_tiles_1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_1_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_2 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_port_tiles_2_f1 | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 2 of 3 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| qfd_res_train_issue | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet |  |  |
| qfd_rly_26_NE_9x9 | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet |  |  |
| qfd_seq_su_static | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet | dh |  |
| qfd_sp_res_train_par_0 | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet |  |  |
| qfd_sp_res_train_par_1 | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet |  |  |
| qfd_sp_res_train_par_2 | 1 | RTL only (no route yet) | not started (open) | Q-ELEM | no closure-loop job yet |  |  |
| qfd_tt_ctlm_static_s | 1 | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | 0 of 1 contract leaves closed | fab, kok, kwd, pw |  |
| qkd_embedding_static_core_provider | 1 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | beat_data, beat_epoch, beat_half, beat_scale, beat_slot, beat_token, beat_v, bea |  |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| qfd_embedding_word_provider | RTL only (no route yet) | not started (open) | Q-NETLIST | no closure-loop job yet |
| qfd_seq_su_gateway | RTL only (no route yet) | not started (open) | Q-COMPUTE-ELEM | no closure-loop job yet |
| qfd_sys_face | RTL only (no route yet) | not started (open) | Q-NETLIST | no closure-loop job yet |
| qfd_tile_nl | RTL only (no route yet) | not started (open) | Q-TILE45 | 1 of 2 contract leaves closed |

</details>

Unknowns: 3 closed masters have no committed Liberty view to audit: qfd_crom_g, qfd_sp_band_lanes, qfd_su_cbuf_g

## Qwen KV/system die (Q-KVSYS-DIE)

Contract: v1.4.1 bind (kvs7c, HOST north + v1.4 HOST partition) + static IO / static D2D successors; v1.4.2 in progress (complete=True).
Netlist / bind: `repo:results/arch/qwen_split_1014/kvsys_v1_4_3_design/port_bind_v2/current/port_bind_v2.json` (2026-10-16 02:09 PDT, opentallas.die_port_bind.v2), die.v `/home/ubuntu/scratch/qkvsys-netlist-0045/kvs13/port_bind_v2/die_bound.v`.

| item | value |
|---|---|
| (1) instances / distinct masters | 20,610 / 53 |
| bind verdict | FAIL (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 34 / 8,975 |
| (2) latest die run on real views | 15 masters / 11,496 inst (of 20,610); `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs8/classify_kvs8.json` |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 25 / 0 / 0 (on 6 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 0 / 0 / 0 / 0 |
| (4) masters by view state | closed + native PASS 13; closed, native FAIL 5; parent: leaves closed, not hardened 5; RTL only (no route yet) 29; hard macro / PHY (allowed model) 6 |
| (5) contract masters absent from the netlist | 3: qkd_embedding_static_core_provider (RTL only (no route yet)), qkd_kv_static_writer_native (closed, native FAIL), qkd_static_kv_return_slots (closed, native FAIL) |
| remaining work units | **70** = 42 masters not closed+native (39 in netlist + 3 absent) + 3 placeholders + 25 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 23 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs10-v143p/STATUS.log` | 2026-10-16 02:09 PDT | src 5f554a767; GEN 27,814 inst; GRT overflow 0 | 2026-10-16 02:09:46 full-die GRT exit=0 overflow=0 ([INFO GRT-0018] Total wirelength: 898355006 um) |
| `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs11-v143c/STATUS.log` | 2026-10-16 00:02 PDT | src 0a7391147; GEN 29,013 inst | 2026-10-16 00:02:42 real case: OT_LEGAL instances=29013 overlaps=0 outside=0 OT_ASSERT PASS OT_PA DONE  |
| `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/kvs8/STATUS.log` | 2026-10-15 15:36 PDT | src 390b51430; GEN 27,810 inst; GRT overflow 0; TT WNS -1762.84 ps; FF setup -1574.60; FF hold -80.60 ps; PDN SKIPPED (diagnostic) | 2026-10-15 15:36:37 STA ff: tns max -56830016.00 wns max -1574.60 worst slack min -80.60  |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| ot_qkh_lane8 | 2048 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 233.12933 > 220 (30 pins) |  |  |
| qkd_cdc_wleaf | 128 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 396.96114 > 190 (1 pins) |  |  |
| qkd_ctrl_pc | 128 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 273.1797 > 220 (27 pins) |  |  |
| qkd_ectl_a_tp8_epoch_direct | 32 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 220.98393 > 190 (913 pins) |  |  |
| qkd_embgw | 1 | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 311.96606 > 220 (1072 pins) | r_ea |  |
| qkd_hgs | 320 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 2 of 2 contract leaves closed |  |  |
| qkd_hss | 192 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 2 of 2 contract leaves closed |  |  |
| qkd_ahub | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 5 of 5 contract leaves closed |  |  |
| qkd_host_rt | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-DIE | 3 of 3 contract leaves closed | ctrl_completion_fault |  |
| qkd_seq | 1 | parent: leaves closed, not hardened | not started (open) | Q-KVSYS-ELEM | 3 of 3 contract leaves closed | r_kvd, r_sd, r_x3_d, t_ar_cr |  |
| qkd_rly_t1 | 5418 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  |  |
| qkd_rly_32 | 934 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_1 | 438 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_1025 | 252 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_1136_<flow> |
| qkd_rly_17 | 228 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_33 | 162 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_291 | 155 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_293 | 124 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_2 | 118 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_289 | 86 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_rly_521 | 85 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_1048 | 82 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_1136_<flow> |
| qkd_rly_540 | 67 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_hslice | 64 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | ctrl_completion_v, ctrl_completion_we | ph1: STANDARD (route once) |
| qkd_hslice_dn | 64 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet | ctrl_completion_v, ctrl_completion_we | ph1: REPLACE by qkd_hslice mirrored (MX/MY), the second copy |
| qkd_rly_2089 | 61 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 2 x hbfd_rly_1136_<flow> |
| qkd_rst_region | 42 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  |  |
| qkd_rly_520 | 23 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_563 | 16 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_624_<flow> |
| qkd_rly_36 | 14 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_21 | 12 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_rly_13 | 3 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_48_<flow> |
| qkd_astk | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: STANDARD (route once) |
| qkd_astk_n | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: REPLACE by qkd_astk mirrored (MX/MY), the second copy n |
| qkd_land | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: STANDARD (route once) |
| qkd_land_n | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | 13 of 14 contract leaves closed |  | ph1: REPLACE by qkd_land mirrored (MX/MY), the second copy n |
| qkd_rly_284 | 2 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_304_<flow> |
| qkd_d2ds | 1 | RTL only (no route yet) | not started (open) | Q-LINK | no closure-loop job yet | att_tx_payload, att_tx_v, cal_seg, cal_start, cfg_addr, cfg_data, cfg_rx_we, cfg |  |
| qkd_rly_93 | 1 | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |  | ph1: REPLACE by replica 1 x hbfd_rly_136_<flow> |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| qkd_embedding_static_core_provider | RTL only (no route yet) | not started (open) | Q-KVSYS-ELEM | no closure-loop job yet |
| qkd_kv_static_writer_native | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | capture 268.01032 > 190 (1 pins) |
| qkd_static_kv_return_slots | closed, native FAIL | closed (TT era) | Q-KVSYS-ELEM | launch 268.77205 > 220 (290 pins) |

</details>

Unknowns: the only die-level STA ran with PDN skipped (diagnostic)

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
| (4) masters by view state | closed + native PASS 164; closed, native FAIL 6; closed, native unmeasured 1; routed-failed 2; parent: leaves closed, not hardened 8; RTL only (no route yet) 59; superseded but in netlist 10; hard macro / PHY (allowed model) 5 |
| (5) contract masters absent from the netlist | 36: dsfd_engram_c (closed, native unmeasured), dsfd_engram_mix4_c (parent: leaves closed, not hardened), dsfd_l2r_vr_564x1__hx_E (closed + native PASS), dsfd_l2r_vr_564x1__hx_W (closed + native PASS), dsfd_mtp_hrow_cbe (closed, native FAIL), dsfd_mtp_hrow_cbw (closed, native FAIL), dsfd_mtp_hrow_hub (closed, native FAIL), dsfd_mtp_hrow_ing (closed + native PASS), dsfd_rly_1_WE (closed + native PASS), dsfd_rly_266_SN (closed, native FAIL), dsfd_rly_266_WE (closed, native FAIL), dsfd_rly_283_SN (closed + native PASS), dsfd_rly_283_WE (closed + native PASS), dsfd_rly_2_SN (closed + native PASS) ... |
| remaining work units | **146** = 103 masters not closed+native (86 in netlist + 17 absent) + 36 placeholders + 7 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 11 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c26b/STATUS.log` | 2026-10-16 02:04 PDT | src 17b13fb06 |  |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/nl0030_26n/STATUS.log` | 2026-10-16 01:24 PDT | src a6f08e1bb |  |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/STATUS.log` | 2026-10-16 00:54 PDT | src aa9e7cfae; GEN 84,387 inst | 2026-10-16T05:02:20 PLACE rc=0 |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c19b/DIAG_STATUS.log` | 2026-10-15 23:42 PDT | GEN 80,654 inst | 2026-10-16T00:44:16 DIAG_PLACE_OK |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c18/STATUS.log` | 2026-10-15 21:25 PDT | src d8072c747 | 2026-10-16T04:25:09 GEN_FAIL  |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c21h/grt/grt.log` | 2026-10-16 00:38 PDT | GRT RUNNING (extra iteration 9/12) | GRT log |
| `ot-epyc4:/srv/opentallas-scratch/claude/s81-die-iter/c19b/grt_p/grt.log` | 2026-10-15 23:32 PDT | GRT overflow 0 | GRT log |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| dsfd_qbank_S | 1898 | closed, native FAIL | closed (TT era) | S-DIE | launch 222.07801 > 220 (2 pins); capture 303.47967 > 190 (1 pins) |  |  |
| ot_s81_cfg7_seq | 1898 | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 229.0978 > 220 (7 pins); capture 298.49203 > 190 (147 pins); 20 combinational pins |  |  |
| dsfd_rly_266_EW | 1521 | closed, native FAIL | closed (TT era) | S-DIE | launch 237.41262 > 220 (126 pins); capture 271.72626 > 190 (1 pins) |  | ph1: REBIND NOW to 1 x dsfd_rly_283_EW |
| dsfd_rly_66_EW | 236 | closed, native FAIL | closed (TT era) | S-DIE | capture 200.14293 > 190 (1 pins) |  | ph1: REBIND NOW to 1 x dsfd_rly_68_EW |
| dsfd_cfifo | 128 | closed, native FAIL | closed (TT era) | S-ELEM-A | launch 263.29628 > 220 (252 pins); capture 205.69189 > 190 (1 pins) |  |  |
| dsfd_r2l_vr_1024x1__ha_SW | 1 | closed, native FAIL | closed (TT era) | S-DIE | capture 397.99082 > 190 (2 pins) |  |  |
| dsfd_hstnh_515 | 16 | closed, native unmeasured | closed (TT era) | S-DIE | NO_VIEW |  | ph0: KEEP (different RTL body from the family generator; not |
| dsfd_bf_front_static | 519 | routed-failed | failed, re-running | S-ELEM-B | failed, re-running; 3 failed job(s) |  |  |
| dsfd_host_c | 1 | routed-failed | needs redesign (no live job) | S-ELEM-B | needs redesign (no live job); 1 failed job(s) |  |  |
| dsfd_bk_collector_c1 | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 2 of 2 contract leaves closed |  |  |
| dsfd_ctrl | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 2 of 2 contract leaves closed |  |  |
| dsfd_sp_capture_c | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-A | 6 of 6 contract leaves closed |  |  |
| dsfd_sp_collective_static_c | 1 | parent: leaves closed, not hardened | not started (open) | S-ELEM-B | 1 of 1 contract leaves closed |  |  |
| dsfd_sp_gather_c | 1 | parent: leaves closed, not hardened | not started (open) | S-GATHER | 1 of 1 contract leaves closed |  |  |
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
| dsfd_sp_pq_n | 1 | RTL only (no route yet) | not started (open) | S-ELEM-B | 4 of 5 contract leaves closed | f_iss |  |
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
| dsfd_rly_283_SN | closed + native PASS | closed (TT era) | S-DIE | launch 203.1 / capture 104.7 |
| dsfd_rly_283_WE | closed + native PASS | closed (TT era) | S-DIE | launch 193.1 / capture 103.3 |
| dsfd_rly_2_SN | closed + native PASS | closed (TT era) | S-DIE | launch 196.2 / capture 78.4 |
| dsfd_rly_54_EW | closed + native PASS | closed (TT era) | S-DIE | launch 218.4 / capture 165.9 |
| dsfd_rly_68_EW | closed + native PASS | closed (TT era) | S-DIE | launch 219.8 / capture 160.6 |
| dsfd_sstn_e0c0 | closed + native PASS | closed (TT era) | S-DIE | launch 181.5 / capture 182.9 |
| dsfd_sstn_e0c0si | closed + native PASS | closed (TT era) | S-DIE | launch 180.4 / capture 177.7 |
| dsfd_sstn_e0c0sinf | closed + native PASS | closed (TT era) | S-DIE | launch 180.7 / capture 172.5 |
| dsfd_sstn_e0e1c0c1sinf | closed + native PASS | closed (TT era) | S-DIE | launch 180.4 / capture 183.0 |
| ot_mtp_p2_prefix_path | closed, native unmeasured | closed (TT era) | S-ELEM-B | NO_VIEW |
| ot_s81_cfg7_seq_bf | closed, native FAIL | closed (TT era) | S-ELEM-B | capture 238.89939 > 190 (234 pins); 20 combinational pins |
| ot_s81_embed_expand | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| ot_s81_engram_dispatch | closed + native PASS | closed (TT era) | S-ELEM-C | launch 186.8 / capture 141.4 |
| ot_s81_hc_caq | closed, native FAIL | closed (TT era) | S-ELEM-B | capture 253.62576 > 190 (1 pins) |
| ot_s81_hc_ccf | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 408.2241 > 220 (1502 pins); capture 544.34652 > 190 (1848 pins) |
| ot_s81_hc_ccr | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 264.06348 > 220 (27 pins); capture 191.644 > 190 (1 pins) |
| ot_s81_hc_cntree | closed + native PASS | closed (TT era) | S-ELEM-B | launch 149.5 / capture 128.6 |
| ot_s81_hc_crx | closed + native PASS | closed (TT era) | S-ELEM-B | launch 217.7 / capture 133.3 |
| ot_s81_hc_cseq | closed, native FAIL | closed (TT era) | S-ELEM-B | launch 305.29711 > 220 (88 pins) |
| ot_s81_hc_pad_f8 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 155.3 / capture 125.6 |
| ot_s81_hc_pad_meta2 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 149.2 / capture 110.0 |
| ot_s81_hc_pad_r5 | closed + native PASS | closed (TT era) | S-ELEM-B | launch 153.7 / capture 114.0 |
| ot_s81_hcx_controller | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |
| ot_s81_hcx_gatherpack | RTL only (no route yet) | not started (open) | S-GATHER | no closure-loop job yet |
| ot_s81_hcx_projection_leaf | RTL only (no route yet) | not started (open) | S-ELEM-B | no closure-loop job yet |

</details>

Unknowns: no die-level TT/FF STA exists for the current netlist | 1 closed masters have no committed Liberty view to audit: dsfd_hstnh_515

## HBM accelerator die (H-DIE)

Contract: v15.1 source contract (+ v14 die masters carried until re-contracted) (complete=False).
Netlist / bind: `repo:results/arch/hbm_die_v16/port_bind.json` (2026-10-16 01:41 PDT, opentallas.die_port_bind.v2), die.v `results/arch/hbm_die_v16/die.v (top hbm_v16_die)`.

| item | value |
|---|---|
| (1) instances / distinct masters | 1,418 / 55 |
| bind verdict | FAIL (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 35 / 403 |
| (2) view inventory by status (mm2) | {"REAL": 53.3, "NO_CONTRACT_INSTANCE": 376.0, "PARTITION": 98.7, "INCOMPLETE": 0.7, "SYNTH": 6.5} (`results/arch/hbm_die_v15/views_v5/inventory.json` 259a3600a 2026-10-15T13:56:20-07:00) |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 17 / 0 / 0 (on 7 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 7490 / 0 / 0 / 0 |
| (3) exposed die inputs (v16 full netlist) | 51 ports / 21,737 bits in 10 open gaps (`results/arch/hbm_die_v16/contract.json` c7a7457d3 2026-10-16T01:41:22-07:00); by owner see note per range (not SM) 6/8,842; H-SU (SU quarter inject read) / H-COLL 4/4,096; H-SU / H-COLL 12/1,040; owner / H-DIE (HBM K-port ownership) 8/52; H-SU / H-ELEM-B (s_mtp) 1/523; HC owner (engine) / H-DIE 12/3,088; H-SU 8/4,096 |
| (4) masters by view state | closed + native PASS 8; closed, native FAIL 8; routed-failed 2; parent: leaves closed, not hardened 2; RTL only (no route yet) 31; hard macro / PHY (allowed model) 4 |
| (5) contract masters absent from the netlist | 24: hfd_cmdproc (parent: leaves closed, not hardened), hfd_hc (closed, native unmeasured), hfd_hc_eng (RTL only (no route yet)), hfd_hgi_am (parent: leaves closed, not hardened), hfd_hgi_vm_calendar_NE (closed, native FAIL), hfd_hgi_vm_calendar_NW (closed, native FAIL), hfd_hgi_vm_calendar_SE (closed, native FAIL), hfd_hgi_vm_calendar_SW (closed, native FAIL), hfd_host_slab (RTL only (no route yet)), hfd_idx_score_native_grid (RTL only (no route yet)), hfd_lk_ep (routed-failed), hfd_loader (closed, native unmeasured), hfd_quant (closed, native unmeasured), hfd_serdes_slab (RTL only (no route yet)) ... |
| remaining work units | **108** = 67 masters not closed+native (43 in netlist + 24 absent) + 24 placeholders + 17 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 6 of the masters |

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
| hbfd_rly_624_EW | 165 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 229.66092 > 220 (37 pins) |  |  |
| hbfd_rly_624_WE | 165 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 226.84503 > 220 (21 pins) |  |  |
| ot_hgi_sm_xload_cl2_bfq | 16 | closed, native FAIL | closed (TT era) | Claude H-SM | capture 416.8191 > 190 (3 pins) |  |  |
| hbfd_rly_624_NS | 11 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 288.09088 > 220 (305 pins) |  |  |
| hbfd_rly_624_SN | 11 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 288.23171 > 220 (310 pins) |  |  |
| hfd_ep_static | 9 | closed, native FAIL | closed (TT era) | Claude:H-LKEP | launch 223.22725 > 220 (3 pins); capture 212.70301 > 190 (1 pins) |  |  |
| ot_hgi_sm_xload_cl2_bdring | 4 | closed, native FAIL | closed (TT era) | Claude H-SM | launch 489.59767 > 220 (25 pins) |  |  |
| hfd_lk_ep_face | 1 | closed, native FAIL | closed (TT era) | H-ELEM-A | capture 204.72551 > 190 (21 pins) |  |  |
| ot_hbm_svc_vmdel_lane | 32 | routed-failed | needs redesign (no live job) | Claude:H-NETLIST/kits | needs redesign (no live job); 6 failed job(s) |  |  |
| ot_hgi_sm_xload_cl2_ctl | 4 | routed-failed | needs redesign (no live job) | Claude H-SM | needs redesign (no live job); 4 failed job(s) |  |  |
| ot_hgi_sfu_scheduled_engine | 4 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed | side_y, vi_q |  |
| hfd_ckgen | 1 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed |  |  |
| ot_hbm_svc_pc_ctrl_leaf | 128 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_static_cmd_target | 40 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_accel_smh_static | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_sm_group | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_vm_kshare | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_pgslice | 16 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_static_program_target | 16 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_vm_lg_static_split | 8 | RTL only (no route yet) | not started (open) | H-ELEM-A | no closure-loop job yet |  |  |
| ot_hbm_xp_aq_tree13_fmt | 8 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_static_cfg_collar | 6 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_hc_q_static | 4 | RTL only (no route yet) | - | - | no registry row | result, result_position, result_v |  |
| ot_hbm_su_bridge_release | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_qcore | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_stack_fault | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_vm_lg_static_split_term | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hgi_dma_back_static_vp4_banks | 4 | RTL only (no route yet) | - | - | no registry row | wa, wb_ready |  |
| ot_vms_calendar_static | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hfd_coll_q2_static_host_v4 | 3 | RTL only (no route yet) | - | - | no registry row | inj_d, rc_d, rc_tag, rc_v |  |
| hfd_hgi_vms_static_NE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| hfd_hgi_vms_static_NW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed | cq | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| ot_hbm_argmax_static_sw | 1 | RTL only (no route yet) | - | - | no registry row | am_stream |  |
| ot_hbm_host_landing256 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_host_packet_static | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_idx_client_static_sw | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_lk_ep | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_status_join | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_programme | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hfd_coll_q3_static_host_v4 | 1 | RTL only (no route yet) | - | - | no registry row | inj_d, rc_d, rc_tag, rc_v |  |
| ot_hgi_qdq_host_static | 1 | RTL only (no route yet) | - | - | no registry row |  |  |

</details>

<details><summary>Contract masters absent from the netlist</summary>

| master | state | registry | owner | detail |
|---|---|---|---|---|
| hfd_cmdproc | parent: leaves closed, not hardened | not started (open) | H-DIE | 9 of 9 contract leaves closed |
| hfd_hc | closed, native unmeasured | closed (TT era) | H-DIE | NO_VIEW |
| hfd_hc_eng | RTL only (no route yet) | not started (open) | H-DIE | 1 of 3 contract leaves closed |
| hfd_hgi_am | parent: leaves closed, not hardened | not started (open) | H-DIE | 3 of 3 contract leaves closed |
| hfd_hgi_vm_calendar_NE | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 228.95632 > 190 (1 pins) |
| hfd_hgi_vm_calendar_NW | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 257.46845 > 190 (1 pins) |
| hfd_hgi_vm_calendar_SE | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 228.95632 > 190 (1 pins) |
| hfd_hgi_vm_calendar_SW | closed, native FAIL | closed (TT era) | HBM-V15-HARDEN | capture 268.06103 > 190 (1 pins) |
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
| ot_hbm_su_static_vm_ports | RTL only (no route yet) | not started (open) | H-ELEM-B | no closure-loop job yet |
| ot_hbm_svc_static_vm_delivery | RTL only (no route yet) | not started (open) | HBM-V15-HARDEN | no closure-loop job yet |
| ot_hfd_coll_q2_static | RTL only (no route yet) | not started (open) | H-COLL | 2 of 3 contract leaves closed |
| ot_hfd_coll_q3_static | RTL only (no route yet) | not started (open) | H-COLL | 2 of 3 contract leaves closed |

</details>

## Largest unknowns

- HBM: there is no full-die netlist. The v15 source contract has 83 instances / 39 masters; the 32 SM tiles (~362 mm2), attention halves, LK EP and host/SerDes are carried from v14 and are not instances. Only the PHY + 128 PC region (53.3 mm2) is on real views; the largest die case (diecase_b, SYNTH ETMs) is TT -237,369 ps. Integration of the SM has not started, so its failures are not yet visible.
- S81: the die physical run binds closed views for only 18 masters / 31,916 of 84,387 instances (OT_VIEW_BINDING); the other closed masters enter as generated abstracts, so their die-context timing is unmeasured. No S81 die STA has ever run (c19b GRT in extra iteration 3/12), and the adopted wide hub C5 (rm5_p1973) needs a new GEN, so the netlist will change again.
- Qwen compute: qfd_tile_nk (768 of 1,638 instances) has no closed view and is being re-packed (64 lanes); 71 open inputs come from 7 producers that are not built; no compute-die STA has ever produced numbers (C16s STA flow error, C23s in PDN); contract v1.3 predates the fpq_s6 homes, so the 10 contract masters absent from the netlist may be stale names rather than missing blocks.
- Qwen KV/system: the strict die_port_bind.py v2 check now runs on the BINDINGS-bound netlist (kv_port_bind_v2.sh, 2026-10-16): after the embgw / host_fdi / stack-strap fixes 0 undriven and 0 multi-driven bits, 23 unconnected inputs that are owed RTL (results/arch/qwen_split_1014/kvsys_v1_4_3_design/port_bind_v2/remaining_items.json); the record is a local regeneration, not yet a die trial. The only die STA is PDN-skipped (TT -1,762.84 ps, 299,285 real-to-real violators). The v1.4.3 PV-wide pair (new masters, 1,024 SRAM macros) is not yet in the netlist.
- Native audit: closed views that fail the native launch/capture budget (compute 1, KV 4, S81 19 in the netlist, HBM 4) need re-kits; each one found at die level so far has cost a re-route.

