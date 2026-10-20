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
