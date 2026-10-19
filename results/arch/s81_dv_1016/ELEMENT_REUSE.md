# S81 element reuse under DV (p1b) — what continues, what changes, what stops

Written 2026-10-17 by S81-DV for the coordinator / owner question "which old-design work can stop".

Sources:
- the closure daemon queue (`/tmp/claude-review-20261003/closure_jobs`, entries not yet in `verdict-watch/seen.json`): 14 S81 jobs;
- running fleet units (ot-heavy on E4 / PVE1 / AGI, 10-17 ~00:10);
- `seen.json` (980 S81-family entries in non-closed states, NEEDS_RTL / REFUSED / EARLY_FAIL_* and similar);
- HANDOFF stream sections.

Classes:
- **A**: reused as-is in p1b, so the work continues.
- **B**: reused with changes. The function stays in DV, re-shaped or re-parented; the old-form work stops and the new form is owned by S81-SLICE / S81-DV.
- **C**: obsolete under DV. It is a hub-only element, so its work stops.

## 1. The asked-about families

| Element family | Class | Why |
|---|---|---|
| **retcol** `ot_s81_hc_ret_column_c*` (`s81hc_retcol_c2f` queued; `retcol c0/c1` native-PASS rows) | **C** | The HC return column carries field / collective results into the central HC banks. In DV, h is slice-resident (4 cth per slice), so finished rows land in the slice's local capture and the column return path does not exist. |
| **CFIFO** `dsfd_cfifo` (frame cfifo, 128×) incl. `cfifo_crs` r5f (native PASS, c2e5317db), colck / negcap variants | **A** | The frame's own x-entry / return FIFO. Frames are reused unchanged; the slice drives the frame cfifo from the adjacent column instead of the serpentine. Keep closing it. |
| **bf_col** `dsfd_bf_col` / BF column leaves (`s81_bf_cl_fp`, `s81_bf_cl_red` queued; `bfh*`), `dsfd_bf_front_*` roots | **A** | In-frame BF16 element columns. Keep. |
| **Relay classes inside frames** `dsfd_rly_63/66/2/15/54/1/283/266`, the `sstn` split base/payload, in-frame `stn` | **A** | Frame-internal operand / return relays (the x_lane / A-B corridor). Unchanged. H-REACH reach runs continue: DV hop planning uses them. |
| **Die-level hub stations** `dsfd_hstnv_2049` / `hstnh_4096`, `hstn*` | **C** | Hub-parent stations. |
| `stnv/stnh 512/514/566` (cx/x2 serpentine), `rly_536 SN/SW/WS/EN` | **B** | Become the slice-ring / x-chain relay stations (1,104 b = 566 + 538 lanes) at measured reach. Keep the closed / native-PASS views. New `s81-dsfd-stnh/stnv` serpentine-specific jobs stop. |
| **Hub net ends / lanes** `s81-hend-m221pq-*` (hx/hr/hq/hsel/hcol/hl/hco/hix), `dsfd_m2l/l2r/r2l_vr_512*`, `s81net_l2r_vr_1100x1__hx_w` (queued) | **C** | Ends of the hub star (x source, return lanes, selector / collector hops). DV has no hub ends. |
| `dsfd_m2l_vr_68x*` (frame return 68-b lanes) | **B** | The 68-b return format is kept; the lanes become ≤ 1.9 mm frame → slice returns. The long hub-bound `hr_*` relay chains stop. |

## 2. Everything else with live or recent work

| Element / job family | Class | DV form / reason |
|---|---|---|
| Q element `ot_v41_rom_elem_q_qxpq_w10`, ROM macros, `ot_s81_cfg7_seq(_bfp)`, `qbank_N/S`, `dsfd_node_*` return tree, `dsfd_rstg`, `ot_s81ph_root_tile`, `dsrom-qelem-*` jobs | A | Frame contents. |
| HBM norm group `ot_hbm_norm_grp` (G64) | A | The slice norm datapath (exact; bench PASS). |
| Engram lookup `s81engm_lkp_static14` (queued), `engram-lkp-*`, Markov `s81_markov_chunk*`, `dsrom-markov256*` | A | Not hub transport. |
| HC `ot_s81_hc_cth` tiles | B | 4 per slice; the parent interface changes (slice-local NORM / POST). |
| SU lane leaves (`sml_u65 / smd_u65 / swe / qne / kve / kvq / qbt*`), `s81-swiglu-esum`, `dsrom_softmax_safe_*` | B | 1/16-width slice lanes, every pin registered (FLOW-HOLD: `dsfd_su_t_swe`). Softmax goes to the PHY-side SM tiles. |
| VM bank group `dsfd_vm_bgq28h` / `dsfd_vm_static_bank128` | B | One bank group per slice (64 KiB). |
| `ot_s81_su_sm` (SM softmax tiles) | B | 8 tiles abutted to the PHY-side service halves. |
| HBM service `dsfd_svc_c`, `dsfd_svch_rly`, `dsfd_svcio_*`, `s81_svc_*` | B | Split into two halves flanking the PHY. |
| Collective lane / engine `dsfd_coll_lane_w`, `s81b-coll_lane_*`, `s81b-coll_core*`, `dsfd_colt_lane` | B | Four edge engines beside the end slices (fold engine kept). |
| Seq / host / wfc / ctrl `dsfd_stage_seq_static_*`, `dsfd_host_c*`, `s81ph-dsfd_ctrl_ctr` (queued), `dsfd_wfc_*`, `fe-wfccrp-*`, `s81-host-protected` | B | The `seqhost` unit. |
| Index select / collect `dsfd_bk_selector / collector` | B | bk units in the void. |
| Engram mix `dsfd_engram_mix4*`, `engram_c*`, `el1011-engc-*` / `el1013-engc-compose` | B | Engram mix halves in the void. |
| SU meso FIFO `s81-meso-d4*` | B | Only if the slice keeps a 0.9 GHz serial domain. |
| **HC hub** `s81hc_ccf / cpin / crootre / crootrw / crootye / crootyw / ctile / ctileh` (8 queued), `ot_s81_hc_crootr*`, `ccr`, `cseq`, `ctrn*`, `hc_comb*`, `ha2_tccr*`, ref gate `s81hc_crrww` (running PVE1) | **C** | Central HC slab (comb / roots / control). DV: per-slice cth plus G-unit coefficients. |
| **SU hub** `dsfd_su_t_*` (ctl / pin / qbe / …), `dsfd_sp_su*`, SU RX hierarchical split `rxh_eq_gate` (running PVE1), `pi-s81hdisp` | **C** | Hub slab; replaced by slice-local lanes. |
| **VM hub** `dsfd_vm_be_sl / bgl28 / bgr28 / fcc / fcn / fld / flt / fsr / fxs / direct_scatter / static_landing / static_return / static_wfc / rsched / seq_tile / clt / mtp_ep / p2_ep / wfc_ep`, `ot_s81_vm_x34/x43*`, `s81_a2f_*` pilots | **C** | The central VM and its FE / BE / landing / reader / scatter fabric. |
| **Collective hub slab** `dsfd_coll_cb* / ce* / ct / ces0 / cesn / cbq / cbh / cele / celp`, `dsfd_coll_mtp_lane`, `dsfd_coll_p2_*` | **C** | Centre collective slab. |
| **Capture / gather / PQ** `dsfd_capt_*`, `dsfd_gth_*`, `dsfd_sp_pq*`, `s81_pq_ctl_state*`, `s81_pq_reader*`, `dsfd_cap_mtp_ep` | **C** | Central capture / gather / x source. Capture is slice-local (8 × 68 b). |
| **MTP / P2 hub transport** `dsfd_mtp_hrow*`, `dsfd_hrow_r*`, `dsfd_mtp_seq*`, `dsfd_p2_lnk`, `ot_p2h_head / xport`, `mtp-p2h-*`, `p2h_head_ref` | **C** | MTP hidden rows go on the ring to the edge links; head items go on the ctl tree. The arithmetic leaves `ot_p2h_fadd16 / arith` are **B** only if the MTP p2 prefix step is kept on the layer die (decided with the MTP ledger row). |
| `ot_s81_head_delay8x32`, `hing_dsfd_C_div2` | C | Hub head / delay glue. |

## 3. Live work: recommendation

| Live item | Class | Action |
|---|---|---|
| c27 GEN runs `g27n / g27f / gx2` (E4, H-C27 / S-DIE) | comparator | Keep until the DV die trial has a GRT/STA row (coordinator rule 0cj); then stop. |
| H-REACH reach / repeater runs (`sdie-reach-1016`, 20+ units) | A | Keep: DV hop planning depends on them. |
| S81 link census probe (`census-s81link`) | A | Keep: off-die link PHY side. |
| `rxh_eq_gate` (PVE1, SU RX hierarchical split) | C | Stop. |
| ref gate `s81hc_crrww` (PVE1) | C | Stop. |
| Queued `s81hc_ccf / cpin / crootre / crootrw / crootye / crootyw / ctile / ctileh`, `s81hc_retcol_c2f`, `s81net_l2r_vr_1100x1__hx_w` | C | Withdraw. |
| Queued `s81ph-dsfd_ctrl_ctr` | B | Hold; the seqhost form comes from S81-SLICE. |
| Queued `s81_bf_cl_fp / red`, `s81engm_lkp_static14` | A | Keep. |
| Streams: S-VM, the SU / HC parts of S-ELEM, S-ENGRAM+NORM (norm part), S-NET hub-net work | C | Stop hub work. Frame-side, BF, Engram lookup, link and relay-reach work continue. |

No job was stopped by S81-DV. Stopping is the coordinator's call, per HANDOFF and the owner.
