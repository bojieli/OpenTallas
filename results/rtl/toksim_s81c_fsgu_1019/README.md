# TOKSIM-S81C/FSGU (10-19): ffn.experts_gu + attn.a_proj in every old shape class, release frame RTL (19bf4121e)

Why the old DAG values differ per layer (experts_gu 1239.8 / 1857.9 / 1856.9 / 3705.6 / 1852.8 / 2470.7 / 1238.9): the old
node is `dsrom_1m_allmeasured_adapters.field_rows` = "the slowest die's one-region RTL time" on the OLD m221pq S81 die for
the representative layer's golden-routed experts + r8 die wire over 2..6 phases (L2 2, L1/L21 3, L0/L20 4, L24 5, L3 6):
an artefact of where the old die put the routed experts. On the p4l DV die every layer die holds the 6 routed experts x
rank-local 1152 rows = 6,912 rows dealt evenly (SPEC s.2 / s.330): frame u_f_0L00 = 12 matrices x 5 rows = 24 phases (4+1
rows), K 5120 FP4, nseg 5, in EVERY layer. Measured: one representative layer per class, all = 3680 (P145 PASS, P144 FAULT).

| class (old) | layer | kind | fixture | field phases | experts_gu P145 | a_proj 7 frames go->last RET |
|---|---|---|---|---|---|---|
| 1857.9 | L1 | engram+sliding | reduced | 25 | PASS 3680 | 361 |
| 1856.9 | L2 | ratio2+compressor+indexer | full | 89 | PASS 3680 | 361 |
| 1856.9 | L14 | engram+ratio2+compressor+indexer | full | 114 | PASS 3680 | 361 |
| 3705.6 | L3 | ratio2 | reduced | 25 | PASS 3680 | 361 |
| 1852.8 | L20 | ratio1+compressor+indexer+candidates | full | 89 | PASS 3680 | 361 |
| 1238.9 | L21 | ratio1 | reduced | 25 | PASS 3680 | 361 |
| 2470.7 | L24 | ratio1+indexer | reduced | 25 | PASS 3680 | 361 |
| control | L0r | sliding | reduced | 25 | PASS 3680 (= FGU full-field L0 3680) | 361 (= FSMALL L0) |

Every leg: 24/24 single phases XS_PLACE_CHECK PASS (golden segment tree bit-exact, coverage, cycle-exact calendar, fixture
BF16 tie), swap/shift mutants FAIL, seq +RETIRE=1 P145 PASS 60/60 rows, P144 FAULT (edge 467 status 11). a_proj: 7/7 frames
lower_xs XS_CHECK PASS, go 63 -> last RET 424 max.

Reduced fixtures (tools/s81_dv/layer_prog/qf_producer/toksim_fsgu_ffnfix.py): a_proj + experts_gu inputs only, from the
pinned w17 golden shard (attn_norm / ffn_norm) + released checkpoint, same writer / golden / split as dv_layer_fixtures.py
(sources pins identical); routed experts re-derived and equal the shard's; the L0 run reproduces the full L0 fixture 37/37
files byte-identical. Used where dv_layer_fixtures refuses (L3/L21/L24 read earlier-layer KV / index sources; L1 not in
its LAYERS). Their fields hold a_proj + experts_gu only; the L0r control (same reduced field) gives the full-field 3680.

a_proj caveat: the old sparse-class nodes (3090.3 L2/8/14: 736 rows, 1859.2 L20: 608, 1858.1 L24/28/32/36: 480) are a_proj
448 rows + compressor.wkv 128 + compressor.wgate 128 + indexer.weights_proj 32 (L2) / wkv + weights_proj (L20) /
weights_proj (L24). xs_place (the DV field compiler) does not place compressor.wkv / wgate / indexer.weights_proj at all,
so 531 measures only the 448-row a_proj part: NOT a replacement for those nodes until those rows are placed and measured.

Run: toksim_fsgu_leg.sh L [PERS [ffn.experts_gu]] on ot-epyc9:/srv/opentallas-scratch/claude/toksim-s81c-fsgu (exe: FGU job 4
Vtb_toksim_fgu_seq, same inode; a_proj exes: FSMALL s_h9nx_e5/s_h10_e2/s_h9MX_e1/s_h9nx_e2; Verilator 5.050).
