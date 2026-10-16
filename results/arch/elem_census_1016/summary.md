# Open / not-started element census (ELEM-CENSUS, 2026-10-16)

Owner question (10-16 ~11:00): what are the many "open" and "not started" fleet-viz element rows? Are they replicas or
duplicates (numbered suffixes) that can be built by copying a closed element? Start anything that does not wait on an
architecture change.

Snapshot: fleet-viz elements.py compute() at ~11:00 PT, main a3e2ffe29. There were 215 open rows: Qwen 63, S81 65, HBM 87.
census.json has the full per-row table with evidence.

Identity is proven with the fleet-viz method (master_identity.normalized):
- comments and whitespace are stripped and the module name is substituted;
- the sha256 of the resulting body is compared.

Rows are never matched by name.

Classes:
- A: exact replica of a closed master (same body hash, same outline and pins). Bind it; no route.
- B: width, pin or mirror variant that can be built from closed masters (k-copy, padding or mirrored placement).
- C: composition, parent or cluster. It closes when its children close plus a parent kit.
- D: blocked on a named architecture item.
- E: superseded or stale (evidence given per row).
- F: independent, never started. Started by ELEM-CENSUS.
- G: in flight (live job or live gate).
- M: hard macro, bound by its view.

| design | A | B | C | D | E | F | G | M | total |
|---|---|---|---|---|---|---|---|---|---|
| Qwen ROM (compute + KV/system) | 3 | 22 | 5 | 22 | 1 | 4 | 6 | 0 | 63 |
| DeepSeek ROM (S81) | 0 | 0 | 18 | 11 | 14 | 0 | 18 | 4 | 65 |
| HBM accelerator | 0 | 3 | 14 | 10 | 34 | 0 | 26 | 0 | 87 |

## Numbered / side suffixes

Only 3 of the 215 rows are exact replicas. Most suffix families are real parameter or mirror variants.

- **qkd_rly_<W> (21 rows, KV die): class B, not A.**
  - These are generated per-width relay stations.
  - They map onto 4 closed hardened standards: qkd_rlys_1, qkd_rlys_36, qkd_rlys_296 and qkd_rlys_528
    (results/arch/qwen_kv_rly_std_1016/variants.json).
  - Examples: 2089 = 4 x 528 and 1025 = 2 x 528 (padded), 93 = 3 x 36, t1 and 1 = rlys_1.
  - The rows go away once OT_KV_RLY_STD=1 is the generator default. Q-KVSYS-DIE will switch it after the kvs12b GRT.
- **qfd_port_tiles_0/1/2 and qfd_sp_res_train_par_0/1/2: not replicas.**
  - The bodies differ only in .BAND(n), but BAND changes the ROM instance, the pt_id strap and the train logic.
  - Both families are D: the approved b2 remap replaces them (one port variant, six parameter-free half-trains).
- **Same or mirrored RTL, but kits differ in pin faces and outline, so mirror variants, not replicas:**
  qfd_xcol_e/w, smh_tile_eg/wg, dsfd_capt_x8_data_e/w, dsfd_l2r_vr_1100x1__hx_E/W.
- **hfd_hgi_vms_static_NE/NW/SE/SW: four distinct bodies, all wires-only wrappers, so C.**
  - NE equals SE except for one quadrant-id tie constant. Making sid a strap would let one master serve both.
  - NW and SW differ in port widths, so the 10-15 note "NW = SW up to constants" is false on current RTL.
- **qkd_hslice / qkd_hslice_dn:** same module and same body hash; only the chain-face pins differ.
  - _dn is B: the qkd_hslice view placed mirrored (approved by Q-KVSYS-DIE).
  - qkd_hslice itself is F (started).
- **A rows, folded into their masters:**
  - qkd_hgs = the closed qkh_head_gather_stage (body b60a6b40, LEF 324 x 21.6).
  - qkd_hss = the closed qkh_head_sstage (body 335a3954, LEF 21.6 x 21.6).
  - qkd_d2ds is a die-name alias of qkd_d2d_static, which is still open (D).

## Blocked on architecture (D)

- **Qwen b2 port remap:**
  - qfd_port_tiles_0/1/2, qfd_sp_res_train_par_0/1/2, qfd_slab_pair_add
  - qfd_tt_ctlm_static_s and qfd_tt_ctlm_tree_static (need the parameter-free calibrated controller)
  - qfd_native59_compute_service (needs the b2 pin grant)
- **Qwen compute die, other:**
  - qfd_xcol_e/w: column envelope grant.
  - qfd_io_collective_static: quarter-local ring redesign.
  - qfd_sp_su64_sfu: SU frame of hardened children.
  - qfd_seq_su_static vs qfd_seq_su_gateway: sequencer choice.
- **Qwen KV die, 17 inputs with no producer** (kvsys_v1_4_3_design/port_bind_v2/bind17_producers.json):
  - qkd_seq (the t_ar_cr on-die credit must go)
  - qkd_host_rt (needs the controller swap)
  - qkd_embedding_static_core_provider
  - qkd_d2d_static
- **Qwen KV die, other:**
  - qkd_astk_ep: v1.4.4 segment slot.
  - qkd_static_kv_landing_seg: hold fix plus the v1.5 static join.
- **S81:**
  - Hub re-floorplan c74342891: dsfd_engram_mix4_c lost MIX4 slot A.
  - S-DIE role-home decision: ot_s81_hcx_* (3 rows) and ot_s81_embed_expand.
  - HC RETCOL adoption: ot_s81_hc_ctra/ctrb.
  - HC parent choice: ot_s81_hc_ctfx_cap.
  - WFC epoch producer: dsfd_wfc_vmx_p.
  - Credit-free successor needed: dsfd_bk_collector_c1 relays colt credits on die.
  - Engram LKP hold redesign: dsfd_engram_lkp_static14.
- **HBM:**
  - VMS glue has no homes or pins in grants v8 / plan v5, and the nat2 bank flip is on hold: ot_vms_hub/rcl/rstop/status_static.
  - No outline or pin grant: ot_hbm_vm_lg_static_bank (64 instances).
  - IDX glue home: ot_hbm_idx_calendar_static.
  - IDX op clock-spread successor: ot_hbm_idx_vm_query_static and ot_hbm_idx_vm_static.
  - svcPC H7 gate: ot_hbm_svc_pc_ctrl_leaf_cfg.
  - HBM MTP deferred (owner 10-16 07:25): ot_gpu_rf_visibility_fence.

## Started (F)

All four were cleared with their die leads first.
- qkd_rst_region and qkd_hslice: Q-KVSYS-DIE.
- qfd_sys_face and qfd_embedding_word_provider: Q-COMPUTE-DIE.

Job ids are recorded in the stream logs under the prefix [ELEM-CENSUS kit].

S81 and HBM have no F rows: every never-started row there either has an active owner or lacks an outline/pin grant.

Kit-ready work found outside the registry:
- **S81 link digital sublayer** (ot_s81_kp4_enc, ot_s81_kp4_dec, ot_s81_rate_match). It sits inside the ot_pdie_serdes /
  ot_pdie_ucie blackbox macros. It is real on-die logic with no rows or jobs and should be added to the S81 contract (S-DIE).
- **S81 dsfd_wfc_vmx_r / dsfd_wfc_hep_t.** These need a no-backpressure check first.

## Fleet-viz fixes (evidence kept)

- **E rows:** 48 entries added to ~/claude-takeover-20261007/superseded_elements.json, each with source_evidence.
  - ot_hbm_su_static_vm_ports gained source_evidence, so its existing entry now applies.
  - Backup: superseded_elements.json.bak-census-1016.
- **A rows:** qkd_hgs, qkd_hss and qkd_d2ds are folded into their masters in element_overrides.json (kind alternative).
  - The reason field records the hash and LEF evidence.
  - Backup: element_overrides.json.bak-census-1016.
- **C rows, wires-only:** 15 rows added to the compositions in tools/fleet_viz/master_identity.json.
  - They now appear as integration rows instead of independent not-started masters.
  - Each entry is gated on its pinned body sha256 and on the no-state check.
  - qkd_ahub was re-hashed after the hd3 Z-bus split (2c5f3342 -> 3c05d51e).
- **C rows with their own state** (dsfd_sp_hc_c/t, dsfd_sp_su_c, ot_s81_hc_cth, IDX score/parent, TKM): left listed.
  They need a parent kit.
- **B and M rows:** left counted, with their mappings recorded here.
  - qkd_rly_* disappears once OT_KV_RLY_STD is the default.
  - Macros need a macro pattern in results/fleet_viz/die_contracts.json (die leads).
- **Stale contract sources:**
  - KV die: now reads v1.4.3 port_bind_v2 (Q-KVSYS-DIE, main 49fd7b44a).
  - Compute die: still reads netlist_0030; switches when the b2 die.v lands.
  - HBM: the registry reads the v15.1 contract while the die is at v16. Most of the 34 HBM E rows are v15/v14 masters
    absent from v16. H-DIE should repoint the source.
