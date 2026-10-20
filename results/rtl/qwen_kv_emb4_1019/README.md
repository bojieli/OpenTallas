# KV-EMB4 (tree K.STA.EMB) 10-19: hardened row_tx_ctx child + OT_KV_EMB_CTX kvs_emb faces

## 1. qkd_embedding_row_tx_ctx child kits (c1a PD 0.50, c1b PD 0.45)
Successor master of the CLOSED qkd_embedding_row_tx r2 (b97c79344): same row body / SRAM / outline 216 x 151.2 / faces,
ONE new S-face output `row_open` (= armed, x 168) consumed by qkd_embedding_ctx_start's overlap veto inside kvs_emb.
Bench `tools/qwen_kv_die/kvjc_row_tx_ctx_gate.sh` (real qkd_embedding_static_join upstream, Verilator 5.050, ot-epyc9):
m0 PASS (24 tokens, 1560 items, row_open == independent armed model on every sample, 24 falls, 6/6 negatives fault);
mutants 1 (word index), 2 (no residency check), 3 (late read), 4 (row_open = row_ready) FAIL. Witnesses: row_tx_ctx/m*.log.

| # | SAFE item | Result |
|---|---|---|
| 1 | Pins | PASS: pin regs on every pin (row_open included, +1 edge); rst_n lands in the RTL rst_q flop + kit reset_landing 2 stages |
| 2 | Reach | PASS: 216 x 151.2 tile, all paths local |
| 3 | Fanout | PASS: unchanged r2 body (closed); row_open = 1 register, 1 load |
| 4 | Depth | PASS: unchanged r2 body (TT +162 closed) |
| 5 | Storage | PASS: row in ot_sram_1r1w_64x512 macro |
| 6 | Floorplan | PASS: same as closed r2 (macro on track grid, one S std-cell band); hard-child lattice applies to the parent placement |
| 7 | Clock | PASS: ck at S-face centre beside the register mass (r2 SS spread 83 ps, TT/FF judged at gate); io_hold_margin 0.03 |
| 8 | Schedule | static; row_open leaves one edge late: the parent's next admissible new owner is >= 2 edges after the 65th send slot |

## 2. OT_KV_EMB_CTX kvs_emb kits x1a (e2a OT_SPINE_SYM) / x1b (e2b OT_SPINE_TREE_PAD): specs in kits/spec_x1{a,b}.json
Master qkd_kvs_emb_ctx (KV-EMB2 body, main f87209b55). Same 388.8 x 302.4 outline, W (i_hroot_W*) / S (i_hroot_E*, i_ctl,
ck, rst_n) faces. E face from the die pin plan (kv_static_die face rule: everything else on E, toward the d2d end):
-d2d__svc[173:0], +i_ctx[98:0] (die fork of the HOST -> d2d port-1 record bus; arrives from the d2d side as svc did),
+px_st (fan root start, beside px_tok/px_tep), +emb_fault (KV-HEALTH sink); 713 E pins (was 786). Hard child
qkd_embedding_row_tx_ctx_c1{a,b} at the 43.2 lattice (129.6, 86.4). Kit gen waits for the child's CLOSED view (no stand-in).
Bench tools/qwen_kv_die/kvs_emb_ctx_bench.sh (tb test/tb_qkd_kvs_emb_ctx_lockstep.sv, Verilator 5.050): lockstep vs the
die-bound qkd_kvs_emb (svc start/token/epoch driven from px_*) + a reference ctx_start; every child input port, row_open,
outputs and emb_fault compared each edge; m0 PASS (14,000 checks, 47 starts, 2 overlap refusals, 1 malformed); mutants
1 (row_open unwired) 2 (join start from raw record) 3 (emb_fault drops row_tx) 4 (fill_token from epoch) FAIL.

## 3. Calendar (GEN9 / dcal successor)
kind-12 CONTEXT slot = max(PREC_K0 3, RESULT(n)@KV HOST 21 + H) (d2d_link_calendar --ctx-host-req H, 4a9737677); H = HOST
RESULT->context edges, NULL until KV-HOST measures. Start at the kvs_emb core = ctx slot + fork ages + 1 (i_ctx pin reg)
+ 2 (ctx tap + out reg): +2 edges vs the svc start. Budget: 170 - H >= fork + 3 + join4_cal last + 1. Row overlap: next new
owner >= 65th send slot + 2 (row_open through the child's output pin reg) -- token period 249,600 edges, 0 cost.
