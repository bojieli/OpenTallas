# Qwen COMPUTE-die element reuse under DV (dv2r8f), 2026-10-17

The owner asked which old-design work can stop. This file classifies every Qwen compute-die element family into three classes:
- **A**: reused as-is in dv2r8f. Only its position changes.
- **B**: reused with changes.
- **C**: obsolete under DV.

KV/system-die elements (`qkd_*`) are out of scope and stay.

**Sources:**
- The closure-loop status snapshot of 2026-10-17 ~00:50, including the live RUNNING/ECO/STALL rows.
- Local gates in progress, and `ot-run` jobs.
- The element census `results/arch/elem_census_1016/census.json` (18:20).
- The ref_tile families on main.
- The dv2r8f model (`dv2r8f.json`, `build_dv2*.py`).

**Caveat.** C means obsolete once DV is the compute-die main line. HANDOFF 0cj says that happens if the q3h4/q3h5 hub/seam cut stays above ~1, and q3h measures 1.435. The q3h4/q3h5 comparator trials still bind the C blocks until the owner retires the comparator. The owner should decide whether to stop that comparator too.

## Live work found (snapshot)

| live item | where | class | action |
|---|---|---|---|
| `qfd_sys_face-rr1-7473dff29` RUNNING route | EPYC4 | A | keep |
| `qfd_d2d_static_r8` ref gate (`ot-run` agidock) + local pre-route gate | agidock / local | A | keep (D2D successor) |
| `qfd_tile_nk_romleaf_c1`, `qfd_tile_nl_romleaf_c1` pre-route gates | local | A | keep |
| `qfd_tt_head_static_h11` pre-route gate | local | B | keep (part of tt_ctlm; its command fan-out changes, see below) |
| `qfd_sp_su64_sfu_pr` pre-route gate (central SU parent) | local | **C** | stop |
| `qfd_xhead_e_w130_mw` pre-route gate (column head) | local | **C** | stop as a die tile. Its x-slice function is folded into the DV slice. |
| `q-b2-integ-1016/run_trial.sh` (b2 port-remap integration) | EPYC4 | **C** | stop (the port tiles are gone) |
| `qfd_sp_vector_memory-fpa/fpb` EARLY_FAIL_STALL (central VM) | EPYC2/3 | **C** | cancel and delete |
| `qfd_hub_emb_g700pf` EARLY_FAIL_STALL (old hub) | PVE1 | **C** | cancel and delete |
| `qfd_slab_pair_add-pa7b` NEEDS_RTL (port-tile level-7 adder) | EPYC4 | **C** | stop. The adder logic is reused inside the DV slice station. |
| q3h4 / q3h5 die trials (Q-DIEPLAN3) | E4 | comparator | owner decision |

`vm_native_q*` (RUNNING/ECO) are HBM (`hfd_vms_bank_native_*`), not Qwen. They are out of scope.

## Classification by family

### A: reused as-is (position only)
- **ROM field:**
  - `qfd_tile_nk` / `qfd_tile_nl`;
  - `*_romleaf*` (incl. `_c1`);
  - node `nb1`;
  - `qfd_tile_rp2_45_slots` die names.

  Each is 768 tiles inside the 48 clusters, unchanged.
- **IO:**
  - `qfd_collective_static_io_production` and its children: `qfd_io_collective*`, `qfd_io_collective_static`, `qfd_static_ch546`, `qfd_ucie_gearbox*`, `qfd_xf_*`, `qfd_coll_xfifo*`, the static CDC twelve-leaf (`qfd_io_xfifo_static`, `qfd_cdc1024_*`);
  - PHY models: `ot_qfd_serdes_112g_x12_phy_s597` x3, `ot_qfd_ucie_x64_phy`.

  They move to the W-edge column, rotated 90 degrees.
  - The collective's word ports keep their formats: `seq_cd_*` 546, `io_out_*` 518.
  - Their source and sink are now the slice chain end (`dvs_W5`) instead of `seq_su`.
- **D2D boundary:**
  - `qfd_d2d_static` (r7f/r8b successor);
  - `ot_qkvd_ucie_x64_phy`;
  - `qfd_ckbump`, `qfd_rstsync`.

  They sit at the N end of the W column. The FDI contract is unchanged.
- **System:**
  - `qfd_sys_face`;
  - `qfd_embedding_word_provider`;
  - `qfd_clkrx`;
  - `qfd_rstseq`;
  - the `qfd_sigbump` straps.

### B: reused with changes
- **`qfd_c_b16` cluster (now owned by Q-CLUSTER).** It needs:
  - a `rs_i -> rs_o` 514-b registered feedthrough for the far bands (0 and 3), the same mechanism as `bc_o`;
  - its `rs` and `bc` faces facing the slice row.

  The xcst corridor stations (`qfd_xcst_n/s`, `_my`) stay inside the cluster.
- **`qfd_native59_compute_service`.**
  - Same function: the q/K/V export formatter, attention return and KV ownership/commit toward d2d.
  - Its inputs come from the slice chain (`dv_kv_*`, 548 / 520 b) instead of `sp_su64_sfu` (kv_w*, 2,048 b) and the VM (q 524, ar 520, write_commit).
  - It needs a port re-partition.
- **`qfd_tt_ctlm_static_s` / `qfd_tt_ctlm_b2` / `qfd_tt_head_static*` / `qfd_tt_core_leaf` / `qfd_tt_scale_leaf`.**
  - The matvec issue controller stays.
  - Its ib/go now enters the slice backbone at W5 (380 b), not `xs_tap`.
  - Its VM-facing ports (mx 553, ld, mo, mee) and the forks go.
  - The tree-top / up4 leaves go (levels 10-11 are unused in TP8, and levels 7-9 sit in the slices).
- **DV slice contents (`qfd_dv_slice2`, new master).** It REUSES the RTL of the following blocks, specialised to 1/12 of the rows and 8 lanes:
  - SU / SFU arithmetic (`qfd_sp_su64_sfu` children: lanes, align, reducers, exp/rsqrt/div);
  - VM bank primitives (`qvm_*` native banks);
  - constant memories (`qfd_crom_g` / `qfd_su_cbuf_g` contents become per-slice gamma / RoPE / scale ROM);
  - the x-slice head logic (`ot_qfd_xslice`, `qfd_xs_leaf` storage + corridor word former);
  - the level-7 adder (`qfd_slab_pair_add`) and the band-lane adders and result-port row scale.

  The RTL is reused; the old physical tiles are not (see C).

### C: obsolete under DV (stop jobs, gates and helper work; keep failure evidence per policy)
- **Central VM:**
  - `qfd_sp_vector_memory*` (par, b2_partitioned_ro6_pin_e3);
  - all `qvm_*` physical views (bank_entries_my_native, su_bank_native, read_control_ro6, return_plane, data256, wctl26/27, bank/su ctrl);
  - `qfd_vm_*` (bank_t, bctl, sctl, su_t, rr2/rr4, xcol_t, xplane, xqface, xrelay, xpad2, xfifo8/32, fan_pc/me/lc, bay_pad15*, qcommit);
  - the VM raw-commit observers (`vm_rawcommit`, 39 homes).
- **Central SU:**
  - `qfd_sp_su64_sfu` (and `_pr`);
  - the SU kit parent / frame of hardened children;
  - `qfd_su_cbuf_g`, `qfd_su_cbuf_native_*`, `qfd_crom_g*`, `qfd_crom48*` (central constant groups);
  - `qfd_seq_su_static`, `qfd_seq_su_gateway`, `qfd_seq_su_bi*` (central SU sequencer).
- **Port / band reduction star:**
  - `qfd_port_tiles_{0,1,2}{,_f1}`, `qfd_port_half_b2` (the b2 port remap / Q-PORTMAP);
  - `qfd_sp_band_lanes`, `qfd_sp_halfband_lanes_b2_l2`, `ot_qfd_band_lanes` tiles;
  - `qfd_bl_lane_cs*`;
  - `qfd_slab_pair_add` (as a tile);
  - `qfd_sp_res_train_par_*`, `qfd_res_train_half_b2_*`, `qfd_res_train_issue*` (result trains);
  - `qfd_b2_word_status`;
  - `qfd_band_upper_tp8`, `qfd_upper_b2_l2*`, `qfd_tt_up4*` (tree top);
  - `qfd_static_command_fork42`, `qfd_static_selector_fork4`.
- **Comb broadcast:**
  - `qfd_xs_tap`;
  - `qfd_xcol_e/w` (incl. `_band`, `_rq`, `_rq0`);
  - `qfd_xhead_e/w` (incl. `_m6`, `_w130_mw`);
  - `qfd_xs_leaf*` (`_m6`, `_banked`, `_extcap`, w130 / w3p): as die tiles, the column-head function is now inside each slice;
  - the q3h die-top H-tree stations.
- **Q / KVN mux:** `qfd_x3_mux_native*`, `qfd_x3_mux_static`. The q export now goes slices -> native59.
- **Old hub / centre:** `qfd_hub*`, `qfd_hub_emb*`, `qfd_hub_ps`. These were already superseded.

## Stop list (for the coordinator)

| item | stop |
|---|---|
| gate `qfd_sp_su64_sfu_pr` | stop the gate |
| gate `qfd_xhead_e_w130_mw` | stop the gate |
| `q-b2-integ-1016` trial | stop the trial |
| `qfd_sp_vector_memory-fpa/fpb` (STALL) | cancel |
| `qfd_hub_emb_g700pf` (STALL) | cancel |
| `qfd_slab_pair_add-pa7b` | drop the follow-up |
| Q-PORTMAP / Q-B2 | stop the helper streams |
| Q-VMWB (VM) | stop the helper stream |
| Q-ELEM SU / Q-ELEM-SUC (SU kit) | stop the helper streams |
| Q-DVM xcol / xhead / xs_leaf | stop the helper streams |
| Q-COMPUTE-ELEM seq / port / forks / tree-top items | stop the helper streams |

Pending the owner's call on the q3h4/q3h5 comparator:
- the q3h4 / q3h5 die trials themselves;
- the C blocks those trials bind.

## Keep list

| item | owner / note |
|---|---|
| ROM leaf / tile / node closure | Q-ROMLEAF |
| `qfd_c_b16` + DV feedthrough | Q-CLUSTER |
| D2D r7f/r8b | Q-LINK-D2D |
| collective static IO and its CDC/xfifo leaves | Q-COLL |
| `qfd_sys_face` route | |
| embedding provider, clkrx, rstseq | |
| tt_ctlm | re-ported |
| native59 | re-ported |
| DV slice RTL / benches | Q-DV-RTL |
