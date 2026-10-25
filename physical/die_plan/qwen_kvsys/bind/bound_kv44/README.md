# kv44: KV/system die bound top, rebound from scratch on plan v3.8x (KV-BIND, 2026-10-24)

- **Top:** `rtl/qwen_kvsys_bound_top.sv` (sha256 98743bb4…). The rtl tree has 88 files; `rtl_sha256.txt` lists them.
  `bind.f` is the file list. Its paths point at the epyc2 tree
  `/srv/opentallas-scratch2/claude/kv/kvbind/t38`, which is e33504a6f with these overlays:
  - main d13ff7c78: tools/die_plan, physical/die_plan, kv_plan_leaves_1023, ot_dp_*.
  - The TOK-QK request sources from main: obsx_bo1, boot_event_bridge, d2d sfm/safe_fo/status_observers_v1, and
    results/rtl/qwen_rom_pair_candidate_1024.
  - `../kv44/rtl/qkd_d2d_cal_seq_bc4_pair1024.sv`.
- **Recipe:** `../kv44/asbuilt_kv44.json`. Driver: `../kv44/mk_kv44.sh`. The as-built netlist is rebuilt in
  `../inputs/kv_bound_rtl6/`. `../kv44/README.md` has the proof and every input.
- **Plan:** `physical/die_plan/qwen_kvsys/die_plan.json`, v3.8x (sha256 b3e713fd…, md5 4d53a273).

## Gates (epyc2; 2,472 s, peak 11.1 GB)

| gate | kv44 | kv41 (bound_pv) |
|---|---|---|
| bind | 0 errors, 0 warnings; 160 partitions, 86 types, 2,545 crossings / 430,558 bits | 0 errors, 85 types |
| connectivity proof | unbound 0, tied 0, undriven 0, multiply_bound 0, straps 5,190, plan_driven 1,935 | identical |
| verify | PASS: 3,359,267 / 3,359,268 matched, 0 mismatched, glue_unmatched 1 | identical counts |
| lint | Verilator 5.050, 86 split runs, 0 errors | 0 errors |
| strict port-bind | DIE_PORT_BIND PASS: 86 masters, 160 instances; every stub/tie/open/strap count 0 (variant_children 17) | PASS, 85 masters |
| bind_post regen | PASS: OK 16, WARN 3 (TRUNK_D / FLAG_D / CFG_FIA, the known KV-P5-law vs boot-image WARNs) | kv42: OK 17, WARN 3 |
| smoke | **PENDING**. bind_smoke has no runnable KV token-stage vehicle for a bound top (static audit only). | kv42: SKIPPED |
| BIND_GATE | **INCOMPLETE** (regen PASS, smoke PENDING) | kv42: INCOMPLETE |
| R8 check (landed) | FAIL with the same profile as kv41: 4 unequal groups, 12 inversions, 5 type conflicts. All come from the KV-P5 kg-row rule (ectl cfg vs epoch/kgo) and are accepted in kv41. | same |

## TOK-QK requests (KV-R1..R5)

- R1 IN: all 128 kvpc rst_n come from `i_host_hbm_rst_n_q`. This is a bind rewire, not a post-edit.
- R2 IN: host = `qkd_host_root_admission_obsx_bo1 #(.D2D_BOOT_ORDER(1))`, and `d2d_boot_begin -> d2d_kv.host_boot_begin`
  rides lane L643.
- R3 IN: `OBS1_COMPAT(1)` on d2d_kv.
- R4 IN: the dcal tile uses the pair1024 image. Note: that is the MU+RoPE emb1627 profile, not ew595.
- kv42 W request pads IN, native through land_r8_extra (see below).
- R5:
  - **B: compatible, not baked in.** It is leaf RTL only (qkd_ctrl_pc_nc, ot_qkd_static_ctrl_pc_emb,
    ot_qkd_static_kv_timing, qkd_ctrl_pc_host_static_core from claude/kv-tok-b-1024 @d08459bf0) and does not change
    any bound file. With those 4 files swapped in, all 29 dependent lint runs give 0 errors
    (`lint_with_boot_fix_B.txt`). TOK-QK selects them when it stages sources.
  - **C1/C2: NOT IN.** C1 needs bind.py glue_transport / split_bus_join, which is only on claude/kv-tok-c-1024
    @db2126db9 and not on main; kv44 binds with main's tools. C2 is a post-bind edit (`apply_C.py`) of hub_Wi /
    sys_SD + ot_fdi_*. Once C1's bind.py is on main, the hook is to re-run `mk_kv44.sh` with
    `split_bus_join: [ot_qfd_serdes_112g_x12_phy_s2]`; C2 stays a TOK-QK vehicle edit unless ot_fdi_* become leaves.

## Latency vs kv41 / kv42 (`lat_delta_kv44.json`, landing members)

- 11,901 members are common to kv44 and kv41. 186 changed (19,026 bits); 129 were replaced:
  - 128 kvpc rst_n now ride the hbm_rst_n lane (synchronous, 14-26 cycles; the die_rst_n spine was 2);
  - 1 boot edge (`d2d_boot_begin`, L643, 28 cycles).
- Plan v3.8x lane changes (bound depth): slg.rsp -> vport in0_* +1 (16 vports); vport vq -> slg vreq +1 (10 vports);
  ahub <-> astk am/ap +1 / +3; kvs_attn acal -> astk cal / cal_exp +1..+4; seq fan / xs +1; 4 fault bits +1..+3.
- W request pads are re-derived (RT 32 on 12 ports): 810 flops (kv42: 900). Landed W is kv42 - 1 on 6 members
  (WS_1, WS_3, WN_1, WN_3 pr_t / pr_valid) and equal on the rest.
- **Boot impact (TOK-QK):**
  - vport RT is now 31/32 (kv41: 30/31) and RL is 63 -> 64. kv44 raises the qkd_pv16_vport_b RT hardware bound to
    32 (param_regen; one type; slot line 48).
  - AP_OFS is regenerated: 64'hffd5ffd2ffd5ffd3.
  - The KV boot image must be recompiled on kv44 (boot_v36 run.sh with `BG=bus_groups.json.gz`); image_kv41 does not
    match this top.

## Reset (item 3, record only; lane RESET owns the tool)

What bind.py emits on kv44:
1. The die input rst_n goes to every partition's `arst_n`, where one `ot_reset_sync #(.ASYNC_STAGES(2))` per partition
   (160 instances, 86 types) asserts asynchronously and releases synchronously.
2. `host.die_rst_n` / `host.host_rst_n` are an async reset spine (`asbuilt.reset_spines`). The 141 spine nets are
   landed by `ot_dp_rsync #(.S(2))` in the sink partition (74 sites in the types). Some sinks get them as synchronous
   data lanes instead (L656-L662, 2-28 cycles).
3. `host.hbm_rst_n` (R1: kvpc + PHY) is a forwarded synchronous relay chain of ot_dp_st through the pc partitions,
   at **unequal** depth (6-26 cycles by position).

Under owner decision 2 (one root 2-flop sync per die region, synchronous relays <= 405 um, equal depth):
- (1) becomes one root sync per region plus a synchronous pipelined tree to the partitions.
- (2) the async spine and the per-sink rsync become the same equal-depth synchronous tree.
- (3) the hbm_rst_n chain is padded to one depth, or becomes a branch of that tree. Release order host -> hbm stays
  in the host leaf.

The hook points are in bind.py: `reset_spines` (pass 1b lane packing), the `ot_reset_sync` / `ot_dp_rsync` emission
in `emit`, and the verify rules for `ot_reset_sync` sources. The reset tool came in with `claude/reset-1024`, merged
to main at daa1b3e76 after this bind. kv44 does not use it.
