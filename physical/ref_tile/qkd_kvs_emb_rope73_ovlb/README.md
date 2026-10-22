# qkd_kvs_emb_rope73_ovl -- RoPE73 OVL kvs_emb (K.STA.EMB), FALLBACK of qkd_kvs_emb_rope73_ovl (MAIN)

SQ-KATTN2 10-21. Top = generated qkd_kvs_emb_rope_ovl (OT_KV_ROPE=1 OT_KV_ROPE_OVL=1 OT_KV_EMB_N32=1 OT_KV_EMB_PJ=1,
qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_rope_ovl.sv), source draft codex/k-rope-1021 edb990e98 / 19e0e1d63.

Fixes vs the draft kit:
- join__rope_sweep: an OPEN 1-b tile input (cls open, no die driver, no body reader: the RoPE body drives
  u_join.rope_sweep internally) -> deleted at the generator (kv_static_die.rope_context_tiles) and the tile file
  regenerated; the 20 remaining ports are exactly the pin plan (gate pins PASS).
- SRAM column moved to the E side x172.8 (z3a u_rowtx column; join logic in the W/centre band by its W/S faces), pd 0.45.
- kind tile (flat; no hard children), job branch claude/sq-kattn-emb-1021, views/records under this kit name.
- Bench tools/qwen_kv_die/kvs_emb_rope_ovl_bench.sh (Verilator 5.050): m0 PASS (5 starts, 5 RoPE starts exactly 1024
  edges later with token 151936+pos[12:3], o_ctx_svc composition every edge, no start without adm_done, head-user /
  TX-user / KVN faults); mutants 1..5 (delay-1, token base, head-user check, KVN fault, adm gating) all FAIL.

Pending (not claimed): GEN callback ages, sole image, die bind (needs an OT_KV_ROPE_OVL K chain), physical closure.
