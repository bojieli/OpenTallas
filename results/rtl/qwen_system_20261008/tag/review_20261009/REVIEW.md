# C03 full-shape collective tag: review (sys-takeover, 2026-10-09)

Change under review: `rtl/rom/ot_qwen_tp_seq_w12_fs.sv` (qwen-system 923aa715d, already on main and instantiated by
`ot_qfd_sp_constants_sequencer_sys`). Tag = `{gen[1:0], stage[5:0], pos[12:0], token[7:0], seg[2:0]}` (32 b).

Verdict: APPROVE.
- Stage (6 b) covers the 38 stages E, L0..L35, H; pos 13 b covers P <= 8,191 (Qwen 8K); gen (2 b) separates package
  steps; seg 3 b covers <= 8 descriptors a stage (the stage programs have <= 7).  token[7:0] is enough once stage, pos
  and gen are present (a slipped die differs in at least one of them).
- Base behaviour is unchanged: the wrapper instantiates the base sequencer and only replaces c_tag.
- The native-collective face (`ot_qwen_tp_seq_w12_fs_nc`, claude/sys-takeover-coll2-seq-b-20261009) keeps the same tag.

Bench (`physical/sys_takeover/seq_tag_bench.sh`, the committed tb with the Qwen layer's two all-reduce segments a stage,
38 stages x positions 5 / 261 / 517 / 8,191):
| run | full-shape collisions | base collisions | verdict |
|---|---|---|---|
| pos | 0 | 28,576 | PASS (608 records, 608 VM writes, no fault) |
| stage field dropped | 11,248 | | mutant FAILS |
| position cut to 8 bits | 456 | | mutant FAILS |
| segment field dropped | 304 | | mutant FAILS |
