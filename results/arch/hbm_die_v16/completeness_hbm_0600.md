# Die completeness, 2026-10-16 06:16 PDT

Measured inventory per die (tools/die_completeness.py). Every number comes from a bind record, the element registry, a native pin audit of the committed view, or a die-run log; the source of each is listed. Re-run daily.

## Summary

| die | netlist instances | distinct masters | non-real-RTL instances | instances without a closed view | open inputs (ports) | netlist masters closed+native PASS | netlist masters not closed+native | contract masters absent | remaining work units | masters left after DEDUPE ph-1 rebinds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HBM accelerator die | 1,506 | 62 | 0 | 459 | 0 | 9 | 49 | 24 | **97** | 67 of 73 |

Remaining work units = masters not closed + native PASS (netlist and contract-absent, hard macros excluded) + placeholders to replace (non-real-RTL masters + contract masters absent from the netlist) + inputs to bind (unconnected input ports + width mismatches + die ports missing in RTL). A contract master absent from the netlist counts once to close it (unless already closed + native PASS) and once to integrate it. HBM additionally carries its exposed input ports and unresolved source ports, listed per die below.

## HBM accelerator die (H-DIE)

Contract: v15.1 source contract (+ v14 die masters carried until re-contracted) (complete=False).
Netlist / bind: `repo:results/arch/hbm_die_v16/port_bind.json` (2026-10-16 06:09 PDT, opentallas.die_port_bind.v2), die.v `results/arch/hbm_die_v16/die.v (top hbm_v16_die)`.

| item | value |
|---|---|
| (1) instances / distinct masters | 1,506 / 62 |
| bind verdict | PASS (strict die_port_bind v2) |
| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | 0 masters, 0 inst  |
| (2) masters / instances with no closed view (die must window them) | 41 / 459 |
| (2) view inventory by status (mm2) | {"REAL": 53.3, "NO_CONTRACT_INSTANCE": 376.0, "PARTITION": 98.7, "INCOMPLETE": 0.7, "SYNTH": 6.5} (`results/arch/hbm_die_v15/views_v5/inventory.json` 259a3600a 2026-10-15T13:56:20-07:00) |
| (3) unconnected input ports / width mismatches / die ports not in RTL | 0 / 0 / 0 (on 0 masters) |
| (3) undriven / multi-driven net bits, stub masters, unbound masters | 0 / 0 / 0 / 0 |
| (3) exposed die inputs (v16 full netlist) | 0 ports / 0 bits in 0 open gaps (`results/arch/hbm_die_v16/contract.json` 04fad9220 2026-10-16T06:09:48-07:00); by owner  |
| (4) masters by view state | closed + native PASS 9; closed, native FAIL 8; routed-failed 2; parent: leaves closed, not hardened 2; RTL only (no route yet) 37; hard macro / PHY (allowed model) 4 |
| (5) contract masters absent from the netlist | 24: hfd_cmdproc (parent: leaves closed, not hardened), hfd_hc (closed, native unmeasured), hfd_hc_eng (RTL only (no route yet)), hfd_hgi_am (parent: leaves closed, not hardened), hfd_hgi_vm_calendar_NE (closed, native FAIL), hfd_hgi_vm_calendar_NW (closed, native FAIL), hfd_hgi_vm_calendar_SE (closed, native FAIL), hfd_hgi_vm_calendar_SW (closed, native FAIL), hfd_host_slab (RTL only (no route yet)), hfd_idx_score_native_grid (RTL only (no route yet)), hfd_lk_ep (routed-failed), hfd_loader (closed, native unmeasured), hfd_quant (closed, native unmeasured), hfd_serdes_slab (RTL only (no route yet)) ... |
| remaining work units | **97** = 73 masters not closed+native (49 in netlist + 24 absent) + 24 placeholders + 0 inputs; DEDUPE phase-1 rebinds to closed standards (GEN work, no route) cover 6 of the masters |

(6) Die-level runs (newest first):

| run | time | measured | last event |
|---|---|---|---|
| none | | | |
| `results/arch/hbm_die_v15/views_v5/pcrow_c_die_clock/run_summary.txt` | e30a0484c 2026-10-15T18:02:47-07:00 | {"kind": "region_run", "grt_s": ["17"], "tns_max": ["0.00"]} | committed receipt |
| `results/arch/hbm_die_v15/grt27_collected/receipt.json` | 2e47f6a43 2026-10-15T00:07:58-07:00 | {"kind": "full_grt", "status": "FAIL_CONGESTION_DIAGNOSTIC_HISTORICAL_MODEL", "overflow": 51123} | committed receipt |

<details><summary>Masters not closed + native PASS</summary>

| master | inst | state | registry | owner | detail | open inputs | DEDUPE |
|---|---:|---|---|---|---|---|---|
| hbfd_rly_624_EW | 165 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 229.66092 > 220 (37 pins) |  |  |
| hbfd_rly_624_WE | 165 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 226.84503 > 220 (21 pins) |  |  |
| ot_hbm_svc_sm_xcal | 32 | closed, native FAIL | closed (TT era) | Codex:H-XC-physical-1016 | capture 253.96084 > 190 (1 pins) |  |  |
| ot_hgi_sm_xload_cl2_bfq | 16 | closed, native FAIL | closed (TT era) | Claude H-SM | capture 416.8191 > 190 (3 pins) |  |  |
| hbfd_rly_624_NS | 11 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 288.09088 > 220 (305 pins) |  |  |
| hbfd_rly_624_SN | 11 | closed, native FAIL | closed (TT era) | Claude:hbmdie-lead | launch 288.23171 > 220 (310 pins) |  |  |
| hfd_ep_static | 9 | closed, native FAIL | closed (TT era) | Claude:H-LKEP | launch 223.22725 > 220 (3 pins); capture 212.70301 > 190 (1 pins) |  |  |
| hfd_lk_ep_face | 1 | closed, native FAIL | closed (TT era) | H-ELEM-A | capture 204.72551 > 190 (21 pins) |  |  |
| ot_hbm_svc_vmdel_lane | 32 | routed-failed | needs redesign (no live job) | Claude:H-NETLIST/kits | needs redesign (no live job); 7 failed job(s) |  |  |
| ot_hgi_sm_xload_cl2_ctl | 4 | routed-failed | needs redesign (no live job) | Claude H-SM | needs redesign (no live job); 4 failed job(s) |  |  |
| ot_hgi_sfu_scheduled_engine | 4 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed |  |  |
| hfd_ckgen | 1 | parent: leaves closed, not hardened | not started (open) | HBM-V15-HARDEN | 2 of 2 contract leaves closed |  |  |
| ot_hbm_svc_pc_ctrl_leaf | 128 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_static_cmd_target | 76 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_accel_smh_attn | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_sm_group | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_vm_kshare | 32 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_static_program_target | 18 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_pgslice | 16 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_vm_lg_static_split | 8 | RTL only (no route yet) | not started (open) | H-ELEM-A | no closure-loop job yet |  |  |
| ot_hbm_xp_aq_tree13_fmt | 8 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_static_cfg_collar | 6 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_hc_q_static | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_sm_vm_wr_q | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_bridge_release | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_cxport | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_qcore | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_static_sfustore | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_stack_fault | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_svc_wb_kport | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_vm_lg_static_split_term | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hgi_dma_back_static_vp4_banks | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_vms_calendar_static | 4 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hfd_coll_q2_static_host_v4 | 3 | RTL only (no route yet) | - | - | no registry row |  |  |
| hfd_hgi_vms_static_NE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: STANDARD (route once, replicate) |
| hfd_hgi_vms_static_NW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SE | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| hfd_hgi_vms_static_SW | 1 | RTL only (no route yet) | not started (open) | H-ELEM-A | 3 of 4 contract leaves closed |  | ph1: MERGE into the family master (no route of its own); NOT |
| ot_hbm_argmax_static_sw_vm | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_hc_eng_static | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_host_landing256 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_host_packet_static | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_idx_client_static_sw | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_lk_ep | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_status_join | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hbm_su_programme | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hfd_coll_q3_static_host_v4 | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
| ot_hgi_coll_inj_idx_join | 1 | RTL only (no route yet) | - | - | no registry row |  |  |
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

Unknowns: no die-level TT/FF STA exists for the current netlist

## Largest unknowns

- HBM: there is no full-die netlist. The v15 source contract has 83 instances / 39 masters; the 32 SM tiles (~362 mm2), attention halves, LK EP and host/SerDes are carried from v14 and are not instances. Only the PHY + 128 PC region (53.3 mm2) is on real views; the largest die case (diecase_b, SYNTH ETMs) is TT -237,369 ps. Integration of the SM has not started, so its failures are not yet visible.
- S81: the die physical run binds closed views for only 18 masters / 31,916 of 84,387 instances (OT_VIEW_BINDING); the other closed masters enter as generated abstracts, so their die-context timing is unmeasured. No S81 die STA has ever run (c19b GRT in extra iteration 3/12), and the adopted wide hub C5 (rm5_p1973) needs a new GEN, so the netlist will change again.
- Qwen compute: qfd_tile_nk (768 of 1,638 instances) has no closed view and is being re-packed (64 lanes); 71 open inputs come from 7 producers that are not built; no compute-die STA has ever produced numbers (C16s STA flow error, C23s in PDN); contract v1.3 predates the fpq_s6 homes, so the 10 contract masters absent from the netlist may be stale names rather than missing blocks.
- Qwen KV/system: the strict die_port_bind.py v2 check now runs on the BINDINGS-bound netlist (kv_port_bind_v2.sh, 2026-10-16): after the embgw / host_fdi / stack-strap fixes 0 undriven and 0 multi-driven bits, 23 unconnected inputs that are owed RTL (results/arch/qwen_split_1014/kvsys_v1_4_3_design/port_bind_v2/remaining_items.json); the record is a local regeneration, not yet a die trial. The only die STA is PDN-skipped (TT -1,762.84 ps, 299,285 real-to-real violators). The v1.4.3 PV-wide pair (new masters, 1,024 SRAM macros) is not yet in the netlist.
- Native audit: closed views that fail the native launch/capture budget (compute 1, KV 4, S81 19 in the netlist, HBM 4) need re-kits; each one found at die level so far has cost a re-route.

