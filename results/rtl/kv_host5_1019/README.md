# KV-HOST5 10-19: H = HOST RESULT(n) -> kind-12 CONTEXT(n+1) edges (D2D_CTX_HOST_REQ), GEN9 725008993 RTL

Benches (Verilator 5.050, fleet ot-epyc5; `rtl/test/kv_host5_1019/run_hlat.sh ROOT OUT [TB]`, every file in `<TB>.f`).
Both are the committed MU benches with timestamp monitors only (no behaviour change, both still PASS):
- `tb_kv_host5_hlat` = tb_mu_peer_e2e (die-0 MU1 coordinator chain, 8 rank codecs + endpoint_mu, ideal 0-latency
  peer link): `runs/tb_kv_host5_hlat.log` PASS.
- `tb_kv_host5_hplane` = tb_qkd_host_mu_out (host plane qkd_host_fullcontrol_observed MU1: pkgctl MU1 + host_if MU_OUT,
  real SQ/CQ DMA): `runs/tb_kv_host5_hplane.log` PASS.

## Chain for a GENERATED token (the next input token = RESULT(n)'s token), all core-family clocks (kv_die HOST_CLK_FAMILY)

| leg | edges | source |
|---|---|---|
| engine_result at root face -> die-0 endpoint retire report (local_tk TK93) | 5 | hlat er->ret0 (all 12 steps) |
| local_tk -> token service tk8 (lt, tk8 regs) | 2 | RTL qkd_host_ctrl_token_service_packet_collected l.157/160 |
| tk8 (all 8 ranks) -> host-plane hc start (pkgctl done -> host_if step_done -> sl_tok -> I_RD/I_WAIT/I_GO -> pkgctl hc) | 15 | hplane HPLANE_GEN (8/8 = 15; prompt token 17-23) |
| hc -> token service cmd_v (qkd_host_hc_station hq, cmd_v) | 2 | RTL qkd_host_hc_station.sv |
| cmd -> die-0 endpoint native request (= qkd_host_native_context_tx source) | 9 | hlat cmd->rq0 uncontended (54 when 4 users' cmds queue) |
| request -> held in context_tx (send_kind 3 slot may capture) | 1 | RTL qkd_host_native_context_tx |
| **H (die-0 KV host, all 7 peer TK reports already in tk8)** | **34** | |

Ranks 1..7: their own request (their kind-12 source) is cmd->rq8 = 25 (ideal peer frames, vs 9 at die 0) -> H >= 50.

## Not a static die constant on TP8
- The pkgctl retires a step only after ALL 8 ranks' TK reports (tb_qkd_host_ctl_mu). Remote reports need the class9 result
  out to each peer and the TK frame back over the host SerDes peer link (elastic boundary), and ranks 1..7 get their start
  as a token frame over the same link: H_die0 = 34 + 2 L_peer, H_rank = 50 + 3 L_peer (L_peer = one-way peer frame latency).
- Static use is still safe: qkd_host_native_context_tx faults (source_ok) if the request is not held at the send slot,
  so the compiler may assume H = 34 + 2 L_bound (die 0) / 50 + 3 L_bound and fail closed when a peer is late.
- Under MU (4 users) the CONTEXT of run n+1 normally belongs to another user whose RESULT came >= 1 run earlier; the
  34-edge figure binds only back-to-back runs of the same user (single user / latency user).
- With H = 34 (single-package/ideal-peer floor): CONTEXT slot 21+34 = 55, fill budget 170-34 = 136 >= fork+3+join4_cal last+1.
