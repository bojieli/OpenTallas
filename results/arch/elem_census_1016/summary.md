# Open / not-started element census, revision 2 (ELEM-CENSUS, 2026-10-16 18:15 PT)

Owner question (10-16 ~11:00): what are the many "open" and "not started" fleet-viz element rows? Are they numbered-suffix
replicas that copying one closed element would cover? Start everything that does not wait on an architecture change.

Revision 1 (11:00 PT, main 74ea5d84d) classified 215 rows. This revision re-reads fleet-viz /api/elements at 18:15 PT
(main 672e7f4d0). It keeps every row that still has an open category, in both independent_rows and integration_rows,
which gives 168 rows. It also classifies the 26 rows that appeared since 11:00. Of the 215 revision-1 rows, 72 left the
open set: 52 superseded, 15 closed, and 5 rows gone.
census.json holds every row with its evidence, the 18:15 live-job state (live_jobs_1815, latest_job_1815) and
resolved_since_1100.

Identity is proven by the fleet-viz method (master_identity.normalized): comments and whitespace are stripped, the
module name is substituted, and the sha256 of the body is compared. Rows are never matched by name.

Classes:
- A: exact replica (same body hash, outline and pins). Bind it; no route.
- B: width, pin or mirror variant built from closed masters (k-copy, padding or mirror).
- C: composition or parent. It closes with its children plus parent integration.
- D: blocked on a named architecture item.
- E: superseded.
- F: independent, never started. Started by the census.
- G: in flight, or covered inside an in-flight parent kit.
- M: hard macro.
- R (new): a failed attempt with no live job, where the owner holds a named structural successor.

| design (fleet-viz target) | A | B | C | D | F | G | M | R | open rows |
|---|---|---|---|---|---|---|---|---|---|
| Qwen compute die (qfd_*) | 0 | 0 | 7 | 16 | 2 | 2 | 0 | 0 | 27 |
| Qwen KV/system die (qkd_*) | 0 | 27 | 5 | 6 | 1 | 0 | 0 | 0 | 39 |
| DeepSeek ROM (S81) | 0 | 0 | 21 | 11 | 3 | 3 | 2 | 3 | 43 |
| HBM accelerator | 0 | 3 | 13 | 10 | 0 | 23 | 1 | 9 | 59 |
| total | 0 | 30 | 46 | 43 | 6 | 28 | 3 | 12 | 168 |

No A rows remain: the three exact replicas from revision 1 are folded into their masters. ot_hgi_coll_pring_static_add_lane
is a new exact reuse of the CLOSED ot_hgi_coll_pring_add_lane (master_identity replica_groups with view_reuse). fleet-viz
already shows it as closed, so it is not counted.

## Numbered and side suffixes

- **qkd_rly_<W> (22 rows) and the new qkd_rly_<W>__dir (5 rows): class B, not replicas.**
  - __dir is the same one-flop-per-bit relay with a / b split into per-direction ports.
    It comes from tools/qwen_kv_die/kv_bound_netlist.py relay_dir_module.
  - Each maps onto the four CLOSED standards qkd_rlys_1/36/296/528. Examples:
    - 2089__dir: 1044 forward + 1044 reverse + 1 reverse = 528 x2, 528 x2 mirrored, and rlys_1.
    - 284__dir: 283 forward + 1 reverse = 296 (13 pad bits) + rlys_1.
  - The rows go away when OT_KV_RLY_STD=1 becomes the generator default (Q-KVSYS-DIE).
- **qfd_port_tiles_{0,1,2} vs qfd_port_tiles_{0,1,2}_f1:**
  - The plain rows are BAND logic variants waiting on the b2 remap (D).
  - The _f1 rows are wires-only parents of the word/result halves (C, integration rows).
- **qfd_sp_res_train_par_0/1/2:** D. b2 replaces them with six parameter-free half-trains.
- **Mirror pairs** (same RTL file, mirrored faces, so not replicas):
  - ot_s81_hc_ctrn_col_e/_w: R. Both a4 routes failed congestion; S-NORM owns the successor.
  - qfd_xcol_e/_w: D. Column envelope grant.
  - dsfd_capt_x8_data_e/_w: now C, see below.
- **dsfd_capt_x8_data_e/_w and dsfd_capt_status_dual: G -> C.**
  - Each is a wires-only pair wrapper over two S-VM capture-split leaves.
  - All of those leaves are CLOSED and native PASS (S-VM 14:00 / 15:26).
  - Added to master_identity compositions; S-DIE binds the pairs.
- **qkd_hslice / qkd_hslice_dn:** same body. hslice is F (being submitted); _dn is B (mirrored placement of the hslice view).

## Revision-2 changes to fleet-viz (tools/fleet_viz/master_identity.json)

- Three new wires-only compositions: dsfd_capt_x8_data_e, dsfd_capt_x8_data_w and dsfd_capt_status_dual.
- Re-hashed dsfd_bk_selector_c1 and dsfd_sp_vm. fleet-viz had reported "source body changed"; both bodies are still
  wires-only, so the compositions apply again.

## Blocked (D), changes since 11:00

- **ot_hbm_vm_lg_static_bank: the d4b slot and the routed view disagree.**
  - d4b now gives it 96 slots of 33.696 x 34.56 um.
  - Its only routed view (main d066faae2, vm_lg_bank_hc_static_1015, routed outside the loop) is 150.336 x 151.2 um.
  - H-DIE was told to size the d4c slot from the view.
- **VMS glue (ot_vms_hub/rcl/rstop/status_static):** still has no d4b slot.
- The other D items are unchanged from revision 1: Qwen b2 remap, the KV bind17 missing producers, the S81 HCX / embed
  homes, HC RETCOL, WFC epoch, the credit-free bk_collector, and HBM IDX glue.

## Failed with no live job, successor named (R): 12 rows

- **S81:**
  - dsfd_host_c: the o3 kit gated at 11:30 but was never submitted.
  - ot_s81_hc_ctrn_col_e/_w.
- **HBM:**
  - VM q2 faces: q2E failed congestion.
  - COLL: ctl_v5_q3 (NEEDS_RTL), vmasm (congestion), uop_slice96 (refused at intake on a source-path lint; flow-only fix).
  - SFU: core_split (successor k7 split2), programme_store (r5 -> r6).
  - SM x-load: cl2_ctlw (successor cl2g), cl2_bfqf, xq_pegress.

Each owner was told in its stream log.

## Independent, started by the census (F)

- **qkd_rst_region:** CLOSED. qkd_rst_region-ec1-5fe4533d3, TT +277.01 / FF +30.02, DRC 0.
- **qkd_hslice, qfd_sys_face, qfd_embedding_word_provider:**
  - Kits are on claude/census-qkit-1016. Helper Q-KIT runs benches and mutants, re-gates, and submits.
  - Job ids are below and in the stream logs under [ELEM-CENSUS kit].
- **ot_s81_kp4_enc, ot_s81_kp4_dec, ot_s81_rate_match:**
  - The S81 link digital sublayer under the pdie macros; the contract rows are on main 20130f663.
  - Helper S81-LINK kits and submits them on claude/census-s81link-1016.

## Gated but never submitted (fleet fill)

- dsfd_stage_seq_static_c10: the v2 kit 7cbfb3921 has been gating since 06:26.
- dsfd_host_c: the o3 kit.
- Both were sent to S-ELEM(PQ).
