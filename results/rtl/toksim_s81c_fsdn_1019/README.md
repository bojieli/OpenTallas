# TOKSIM-S81C/FSDN 10-19: ffn.down in every p4l layer type on the release frame RTL

Why the DAG's old down cycles differ per layer (1516.3 / 1517.7 / 1540.7 / 2028.2 / 2050.7 / 3071.5): the old DAG
(token_path_20261009 ds_rom.json) priced each layer on the OLD die placement (r8 die wire 424..867 cyc over 3..6 phases +
old field RTL). The model's down shape is the same in all 40 layers (6 routed FP4 + shared FP8 w2, K 2304, same TP4 rank and
16 slice x 8 frame row deal, xs_place.op_groups). On the p4l-MU die only the frame's FIELD differs per layer type
(xs_place XS_OPS / BF_OPS: L0 set; L2 / L20 add idx.q + cmp.wk; L14 adds eng.wkv). Representatives
(dv_layer_record.representatives): ratio 0 -> L0 (L0, L1), ratio 2 -> L2 (L14 for Engram L14), ratio 1 -> L20 (L20..L39).

Vehicle: FDOWN's (u_f_0L00 = col_h9_l4_nx LK5, GEN mu4c 19bf4121e, 78/78 RTL blob-identical, Verilator 5.050), each layer's own
field compiled by toksim_fsdn_frame_gen.py --layer with that layer's rank-0 layerbench fixture (released checkpoint + golden
shard, manifests verified), FGU +RETIRE bench exe (FGU job 4 build, same sources), +RETIRE=1 on every sequence.

Results (L0 = control, reproduces FDOWN exactly):
| layer | down field phases | singles | mutants | per-expert seq floor | span at P130 routed / shared |
|---|---|---|---|---|---|
| L0  | 44-64 (21) | 21/21 PASS | swap/shift FAIL | P125 FAULT 11, P130 PASS | 549 / 561 |
| L2  | 50-70 (21) | 21/21 PASS | swap/shift FAIL | P125 FAULT 11, P130 PASS | 549 / 561 |
| L14 | 75-95 (21) | 21/21 PASS | swap/shift FAIL | P125 FAULT 11, P130 PASS | 549 / 561 |
| L20 | 50-70 (21) | 21/21 PASS | swap/shift FAIL | P125 FAULT 11, P130 PASS | 549 / 561 |
Every expert 4/4/2 rows, 70 rows per layer checked (xs_place check: segment-tree values bit-exact vs golden, coverage, calendar
edge-exact, fixture BF16 tie). Instance (FDOWN definition): 20 x 130 + 289 = 2889 + priced tail 195 = 3084 in every layer type.
Files: <L>/{singles,sweep}.txt, res_seq_*_P125/P130.json, gen.log, index.json, sources.sha256, exe.sha256, fsdn_<L>.otrun.log.
