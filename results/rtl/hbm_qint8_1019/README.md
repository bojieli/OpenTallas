# HBM-QINT8 (10-19/20): packed INT8 Qwen weight stream on the d4g die composition

## Defect (bound GEN2e3/GEN2e4 source, same file hashes)
`ot_hbm_svc_sm_feed_programmed_rel_id` (svg_* x16 in die.v, SYNTH view) keeps an S1 consumer copy (`ot_smh_static_feed`) that
checks command [29] / [39:30] / [25] against the RAW svg packet. `ot_hbm_accel_smh_attn #(ENABLE_INT8 1)` converts a packed
128-code line (xc mark command[116]) into two BF16 lines 2 and 3 edges later, and the compiler's command fields describe that
converted stream, so every INT8 calendar faulted ("s1 1") at its first consume edge, at any pace. Witness before the fix:
`results/rtl/toksim_hbm_smhbm_1019/runs/q8_o_witness.json`, `q_qkv_p200.json` (source 9550595f3 / a064861d9).

## Fix (RTL: rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_id.sv)
PREL programme word bit [118] (unused under PREL: retire bank/epoch come from the go context) carries the same packed-line
mark. The copy checks the SM-front view `{conv ? {1, held tag} : mark ? 0 : raw}` (conv = the marked packet 2 or 3 edges
ago) plus the converter calendar rules of smh_attn g_int8 (mark without a packet, mark on the busy edge, raw packet on a
converted edge -> i8_f). Without a mark the view is the raw packet exactly. Compiler: svg word bit 118 = 1 on every
packed-line read word (tools/hbm_layer_vehicle/toksim_smhbm.py qwen_block_programme; a production Qwen INT8 compiler must
do the same). Bench check: tb_toksim_smhbm asserts svg view == sm.f_packet (valid, tag) every edge.

SAFE-DESIGN checklist (svg feed change; no new ports, no tile kit: svg is a SYNTH view in GEN2e4):
1 pins: no new ports, PASS. 2 reach: local, PASS. 3 fanout: i8_c <= 4 loads, i8_conv 11 loads, PASS.
4 depth: one AND/2:1 mux in front of the existing S1 compare (sticky fault flop), PASS. 5 storage: 6 control + 20 tag flops,
held tag 2 deep (no delay line), PASS. 6 floorplan: n/a (no outline change; ~30 flops). 7 clock: stream_clk, same domain, PASS.
8 schedule: static, faults never stall; no cycles added (INT8 converter latency 2 already in the compiler calendar), PASS.

## Evidence (Verilator 5.050, unpinned ot-run, ot-epyc5:/srv/opentallas-scratch/claude/hbm-qint8-1019/out)
Die-composed bench tb_toksim_smhbm.sv, successor PC (TOKSIM_PC=safe; mc3 identical), rotated layout, SMB_BSCALE 1, TP-8 rows.
| run | shape | verdict | blocks | span (first cmd -> last result) | edges/block |
|---|---|---|---:|---:|---:|
| fi8_qkv48_p80/p96 (+ fi8m3) | 4096 x 48 rows | PASS bit-exact | 24 | 3,390 | 141 |
| fi8_o128_p80/p96 | 1024 x 128 | PASS | 16 | 2,288 | 143 |
| fi8_gu192_p80/p96 | 4096 x 192 | PASS | 96 | 13,182 | 137 |
| fi8_down128_p80/p96 | 3072 x 128 | PASS | 48 | 6,654 | 139 |
p80 == p96: INT8 is SM-bound (130-word block programme + 6), not HBM-bound (64 B/edge/SM needed vs ~104 supplied).
Regression (non-INT8 bit-identical): fr_dsB_p96 per-op spans == s_dsB_p96; fr_o128_bf16w_p80 span 2910 == t_o128_p80.
Mutants (witness/): fm8_nomark (svg mark dropped) and fm8_late (svg mark one word late) -> FAULT svg s1 at cycle 844;
fm8_sign (define OT_INT8_MUT_SIGN, converter sign bug) -> golden FAIL 128/128 rows.
