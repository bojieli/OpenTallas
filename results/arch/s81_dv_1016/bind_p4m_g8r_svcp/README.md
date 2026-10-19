# bind_p4m_g8r + SVCP (TW3-S81/LAYERS/SVCP4M, 10-19)

= bind_p4m_g8r (G8R2, plan p4m, land plan p4m) + the abutted on-die svc softmax P-path lane **pr_09_07** (514 b, 110 um:
rsv_09 ro W face -> rsv_07 ri E face; dsdv_svc_rs P PATH, gap G9).  die.v differs from bind_p4m_g8r/die.v ONLY in that net
(u_rsv_09 .ro W face, u_rsv_07 .ri E face).  die.v sha256 d6a8a8bbab7c8932725ca3a91a3631ac8ab0a0b8f1d3cf533f69de861e72c9b2.

Plan `p4m_svcp/plan.json` = `dv_plan_eqn.py --plan p4l/plan.json --land-in landing/p4l2` on the SVCP p4l plan: identical to
p4m/plan.json except the added link pr_09_07 and facts (svc_chain links pr 14 -> 15, bit_mm 364117 -> 364174); the land-in
plan is byte-identical to landing/p4m_in apart from its source path, so land plan p4m is unchanged (the lane is abutted).
Bind table `bind/bind_table_p4m_svcp.json` (`bind/mk_table_p4m_svcp.py`) = bind_table_p4m + the SVCP svc_rs `unlinked_out_bits`
spare-output rules.

`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4m_svcp/plan.json --out <scratch>/bind --bind real
 --bind-table results/arch/s81_dv_1016/bind/bind_table_p4m_svcp.json --land-plan results/arch/s81_dv_1016/landing/p4m/land_plan.json`
(3 min 51 s, 0.4 GB, local).  reset_reach_gate PASS.

Strict die_port_bind (unread / open-output check): **FAIL** only on unread_net_bits 3,202 / output_open_ports 43
(spare_out_bits 191,426 declared; every structural counter 0; 40 masters / 9,343 inst).  The unread nets, classes and
per-master open outputs are IDENTICAL to bind_p4l3_g8_svcp, so its classification carries over (unread_audit.json): svc
w_* = G9b (SO o rows), the rest other owners' classes; no pr_09_07 / P-path net is unread or open.

L0 on this die (compiler fcc8bf542, PPATH on, fixtures layerbench-s81/fixtures/L0): results/rtl/s81_layer_tput_1018/compiler/
prog_L0_g8r_svcp -- GAP 10 / PARTIAL 32 / LOWERED 23 (INT g8r: 16/28/21); attn.max, attn.exp GAP -> LOWERED, attn.den, attn.sink,
attn.wo_a, ffn.router GAP -> PARTIAL.  cut_svc recut (1,311 inst, pr_09_07 internal) + L0 replay: slice_bench/l0_cut_svc_p4m_svcp.
