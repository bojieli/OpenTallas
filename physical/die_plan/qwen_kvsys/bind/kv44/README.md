# kv44: Qwen KV/system die re-bound from scratch on plan v3.8x (KV-BIND 10-24, owner decision 9)

The KV `bound_netlist.json` / `die_bound.v` that every KV bind since BINDER2 used were lost with the 10-23 hosts. kv44
rebuilds them and re-binds the die with main's `tools/die_plan/bind.py` on the current plan
`physical/die_plan/qwen_kvsys/die_plan.json` (v3.8x, sha256 b3e713fd…, md5 4d53a273). The bound top is in
`../bound_kv44/` (see its README for the gate results).

## 1. Rebuilding the as-built netlist (`../inputs/kv_bound_rtl6/`)

- Input: `../inputs/die_rtl6.v.gz` (rtl6 GEN die.v, sha256 e1fc838f…, 46,711 instances, 71 masters; source e33504a6f).
- Tool: `tools/qwen_kv_die/kv_bound_netlist.py` at e33504a6f (unchanged). It needs the rtl6 `kv_flags.env` and the
  `die.v.params.json` sidecar. Both were lost, so both are reconstructed:
  - `kv_flags_rtl6.env`: the kvs14r flags plus the rtl6 additions. The test is that all 25 bound masters match kv41's
    `bound_pv/rtl` (HOST_OBSX, DCAL_BC/BC4, EMB_WIN 595, ATTN_R16, FACE_LAND kvs_attn and D2DS kit
    qkd_d2d_static_r7w_sfm2 were found by mismatch).
  - `die_rtl6.v.params.json.gz`: 7,663 instances / 10,896 parameters, read from the leaf `#(...)` literals of kv41's
    `bound_pv/rtl` through `bind_names.json`. Where kv41's param_regen hook had changed a value, the as-built value
    is restored (`sidecar_from_bound.py`).
- Output: 46,710 instances, 15 rewritten, 9,812 constant bits folded, 35 strap ports, off-chip die_id/por_n/refclk,
  problems []. These counts equal the binder2-1023 record. `kv_hard_models.sv` is byte-identical to kv41's.
- **Proof:** re-binding plan v3.6 with binder4 bind.py (588d93853) and `asbuilt_v36e.json` on the rebuilt netlist gives
  87/87 rtl files byte-identical to the committed `bound_pv/rtl`. The one exception is a source-path comment in
  `kv3_hub_Wi_part.sv`.
- Scripts: `probe_bind.py`, `sidecar_from_bound.py`, `remap_asbuilt.py`, `mk_tree.sh`. The ASAP7 cell models come from
  the ORFS image `openroad/orfs:asap7lock` and are substituted for `@ASAP7_CELLS@`.

## 2. Recipe `asbuilt_kv44.json` = kv41's `asbuilt_v36e.json` + the TOK-QK requests as bind inputs

| request | how it is in the bind |
|---|---|
| KV-R1 kvpc rst_n = delivered HBM reset lane | rewire class `kvpc_hbm_reset` (`plan_rewires_kv44.json`, `mk_rewires_kv44.py`). 128 edges `host.die_rst_n -> kvpc_*.rst_n` are replaced by `host.hbm_rst_n` (identity, beside the hrst_n edge). In the RTL the kvpc rst_n are fed by `i_host_hbm_rst_n_q[0]`. |
| KV-R2 BO1 boot-event variant ON | `substitute_inst host -> qkd_host_root_admission_obsx_bo1` (main a2757edd53), rewire class `d2d_boot_order` (`host.d2d_boot_begin -> d2d_kv.host_boot_begin`, lane L643), and `D2D_BOOT_ORDER=1` (kv_regen44). `port_map_kv44.json` adds the variant's port-name alias. |
| KV-R3 d2d OBS1_COMPAT=1 | kv_regen44 sets `OBS1_COMPAT=1` on d2d_kv. Main's `ot_qwen_d2d_sfm.sv` / `ot_qwen_d2d_safe_fo.sv` / `ot_qwen_status_observers_v1.sv` are in the tree. |
| KV-R4 dcal image from results/rtl/qwen_rom_pair_candidate_1024 | `rtl/qkd_d2d_cal_seq_bc4_pair1024.sv` (`gen_dcal_pair1024.py`; same module `qkd_d2d_cal_seq_pin_bc4` with the pair image inlined, period 293,376, C 0a010308 / K 03030443). It is listed in `files` + `prefer`. Note: the pair profile is MU+RoPE emb1627 R16, while kv41's dcal ran the ew595_r16 image; TOK-QK owns that choice. |
| KV-R5 B / C1 / C2 | **NOT IN.** claude/kv-tok-b-1024 and kv-tok-c-1024 had no commits beyond b1131f6fa8 at bind time. Hook points: B = controller boot window (`qkd_ctrl_pc_nc` / `ot_qkd_static_kv_timing` leaf RTL, swap via `prefer`/`substitute_inst`); C1 = hub_Wi valid/data delay alignment (an R8 `land_r8_extra` member or a bind rewire); C2 = async FIFOs at the HOST adapter (a `substitute_inst` of the host leaf). |
| kv42 W request-lane pads | Native: `land_r8_extra tables/kv_wreq_r8_kv44.json`. It replaces the kv42 post-bind edit. The pads are re-derived for v3.8x (see 4): 810 flops (kv42: 900). |

`kv_regen44.py` (param_regen) runs `../kv_regen36e.py`, which applies the v3.6 rule values guarded by the measured ECTL
K round trip. It then adds:
- the R2/R3 opt-ins;
- `qkd_pv16_vport_b RT` bound 31 -> 32 (see 4);
- `AP_OFS` = 64'hffd5ffd2ffd5ffd3. The v3.6 rule value 64'hffd2ffd1ffd1ffd1 is stale on v3.8x. The new value is from
  `regen_constants.py kv_ahub` on this bind and is pinned like `D2D_TXDP_K`: bind_post re-derives it and FAILS on any
  change.

## 3. Landing tables re-derived on v3.8x (`tables/`)

1. pass 0 (land_align off) -> `bus_groups` -> `r8/r8_fault_exempt.py` -> `r8/r8_invariant_split.py` ->
   `tools/die_plan/r8.py pads --bus leaf --replica type` gives `qwen_kvsys_r8_landing_kv44.json` (5,537 members,
   205 padded, 18,584 pad flops; v3.6: 203 / 18,520). `r8.py check` on the table: PASS.
2. PV entry table: `kv_pv_pads_plan.py --option bound --entry --tie-types PLAN --tie-only cross` +
   `kv_pv_entry_table.py` (claude/kv-p6-v37-1023 @0ec5c902d; scipy in a venv) -> `kv_pv_entry_to_r8.py`. The result is
   identical to v36: 3,100 covered ids, the same pads, and the same params (TRUNK_D 43, FLAG_D 0, cfg_fia 68).
3. kg row pads: `../kv_kg_row_pads.py` on pass A gives 96 members and 8,257 flops, identical to v36.
4. W request-lane pads (`kv_wreq_dq44.py` -> `kv_wreq_r8_extra.py` on pass B).
   - Plan v3.8x lengthens slg <-> vport lanes: rsp is +1 on all 16 ports and vq is +1 on 10.
   - The RT rule (`9 + max_g(D(vq_g) + D(rs_g))`) reproduces kv41's 30/31 exactly and gives kv44 RT 31/32. **32
     exceeds the qkd_pv16_vport_b RT bound of 31 on 12 ports**, so kv44 raises the bound to 32 (one type; slot line
     47 -> 48 deep; any word <= 31 behaves as before).
   - The kv41 boot DQ (KV-P7 image_kv41/vport_dq_pads.json) moved by dRT gives RL 63 -> 64 and these pads:
     WS_1 1, WS_3 9, WN_1 2, WN_3 13, ES_1 3, ES_3 9, EN_1 4, EN_3 13 = 810 flops.
   - `regen_constants.py` VPORT_RT now checks against the bound the bind applied, not a literal 31 (tools change on
     this branch).

## 4. Reproduce

`mk_kv44.sh SCRATCH OUT` (tree = e33504a6f + d13ff7c78 overlay + request sources; see the header). It runs
`bind.py all`, then `bind.py portbind`, then `bind_post.py --die qwen_kvsys --bound OUT --smoke submit`.
