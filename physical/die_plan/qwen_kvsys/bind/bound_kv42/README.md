# KV kv42 bound top (KV-TOK 10-24) = kv41 (bound_pv, BINDER4 @588d93853) + PV W request-lane pads

Closes the KV-P7 boot item "kv41 lacks the W request-lane pads" (image_kv41/pv_check.txt, vport_dq_pads.json).

- Pads: `../kv_pv_wreq_pads.py bound_pv/rtl ../boot_v36/image_kv41/vport_dq_pads.json OUT bound_pv/bus_groups.json.gz
  bound_kv42/bus_groups.json.gz` -> one `ot_dp_dly #(.W(15), .D(DQ-15))` on {pr_valid, pr_t} of each V port whose boot
  DQ exceeds the qkd_pv16_vport_b bound 15: WS_1 2, WN_1 3, ES_1 3, EN_1 4, WS_3 10, ES_3 10, WN_3 14, EN_3 14 stages
  = 60 stages x 15 b = **900 flops** (the boot's count). Changed types: kv3_pv_v5/v7/v11/v12_part (one instance each:
  pv_S_5, pv_S_7, pv_N_5, pv_N_7). `rtl/` holds only those 4 files; every other file = bound_pv/rtl (rtl_sha256.txt lists
  the assembled kv42 tree).
- Why a post-bind edit, not a bind.py re-run with a land_r8_extra table: the as-built netlist the KV recipe binds against
  (binder2-1023/kv_bound/die_bound.v + bound_netlist.json) was lost with the 10-23 hosts. The edit adds delay stages on one
  leaf-input connection per port with the bind's own INNER-delay cell; connectivity is unchanged. verify / strict
  port-bind: NOT RE-RUN (no netlist); lint: the kv_dieslice Verilator build of the kv42 tree.
- `bus_groups.json.gz` = bound_pv's landing record with the pad added to landed_stages of the 16 padded pr_t / pr_valid
  members (`wreq_pad` field) = what a re-bind with the pad in land_r8_extra records.
- bind_post (regen_constants, --smoke skip, peer QC bound_r8): regen PASS OK 17 / WARN 3 (kv41: OK 15 / WARN 4):
  **VPORT_DQ WARN -> OK** (max 16 -> 9 by the KV-P5 law); remaining WARNs TRUNK_D / FLAG_D / CFG_FIA are the known
  KV-P5-law vs PV-entry-table / boot-image differences (the compiled boot image is authoritative). Smoke: see
  tools/qwen_layerbench/kv_dieslice (KV-TOK).
- Boot image: `../../boot_v36/image_kv41` unchanged. The kv41 boot compile already programs DQ = 15 on the 8 padded ports
  and lists the pads as "bind must already carry it" (pv_check); RL = the longest port's 4 + W + RT (that port has DQ 0,
  no pad) is unchanged, so a compile on kv42 gives W' = W + pad, DQ' = DQ - pad = 15, pad_stages 0, identical targets.
  A literal re-run of kv_boot_v36.py prep on kv42 is NOT RUN: its rtl6 GEN as-built inputs (relay_stages.json,
  static_model.json, kv_flags.env, health_successor.json: ot-epyc5 codex-kvgen-2140/run_main_rtl6) were lost.
  RL 63 / cfg_fia 64 (boot) vs 67 / 68 (entry table): the boot values are the programmed ones (table lacks the as-built
  relay-table reference offset, KV-P7 note).
