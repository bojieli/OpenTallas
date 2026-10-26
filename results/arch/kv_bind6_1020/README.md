# KV-BIND6 10-20 strict-bind replay (diagnostic, NOT a die result)
Case: Codex d5p diagnostic copy (54e9d9c39 + ledger producer, OT_KV_PARAM_DIAG=1), restored to its PRE-HEALTH netlist,
health plane re-installed with the GEN9 tools, then tools/qwen_kv_die/kv_port_bind_v2.sh (replay.sh / replay2.sh).
- abbb4391c (n_hpt_* health transport nets): kv_output_pads 'private spare output has a dynamic/nonzero input' GONE;
  pass 1 unread 3948 / opens 7; pass 2 refused 'SEQ_HS: ahub hs_start is not sourced by qkd_kvs_attn.ahs' (driver = qkd_kvs_attn_fl).
- e744dbe0f (misc roles accept the verified attn _fl wrapper): pass 2 unread 1 / opens 7 (replay_pass2_e744dbe0f.txt):
  unread n_rrs_n_hboot_t0_0__g4_s1 (dead reset station -> fixed 75171867d kv_child_rst prune);
  opens dcal adm_done/cal_ready/layer/running + d2d recovery_cycles (OBSX readers, OT_KV_HOST_OBSX=1, not in this case's flags);
  qkd_kvs_pc / qkd_kvs_pc_h pc__hfx (sr6 PC RTL bound, PC view LEF has no pc__hfx pin -> health plane skips it; KV-PC5 view).
