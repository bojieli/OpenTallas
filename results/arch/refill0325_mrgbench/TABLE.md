# REFILL-0325/MRGBENCH 10-20: READY_TO_MERGE on-main merge bench + mutant regression (Verilator 5.050, ot-epyc7)

Scope: READY_TO_MERGE branches not on origin/main with kit benches added/changed since REFILL-1830/MRGBENCH
(claude/refill1830-mrgbench @7a921deb3). Each kit's job.json stages.bench re-run on
`git merge-tree --write-tree origin/main(360c64320) + branch` (what the daemon sees after merge), closure-daemon verdict
semantics (pass = rc 0 + pass_regex, no readmem input error; mutant = fail_regex seen). Snapshot = git archive of
Makefile rtl tools physical/common_flow + kit dir + cmd/source-named paths (collect.py; pc sr7 also qkd_kvs_pc{,_h}_rl1,
read by kvpc_sram_bench.py). Unpinned ot-run, staged on ot-epyc7 /srv/opentallas-scratch/claude/refill-0325/MRGBENCH.

| branch | kit | merge tree | conflicts | stages | unexpected | verdict | owner |
|---|---|---|---|---|---|---|---|
| claude/kv-clkfix-hroot-1019 @048ef6067 | qkd_kvs_hroot_k1 | 3c2a31b56 | - | 3 pass / 5 mutants | 0 | PASS | KV-CLKFIX (LEAD2-KV), K.STA.HROOT |
| claude/kv-pc3-1019 @2cbb1e030 | qkd_kvs_pc_sr7 | eacafded6 | - | 9 pass / 16 mutants | 0 | PASS | KV-PC4/PC5 (LEAD2-KV), K.STA.PC |
| claude/kv-pc3-1019 @2cbb1e030 | qkd_kvs_pc_sr7b | eacafded6 | - | 9 pass / 16 mutants | 0 | PASS | KV-PC4/PC5 (LEAD2-KV), K.STA.PC |
| claude/s81-frame5-rffwd-1020 @f9d44ffae | s81frame_col_h9_rf | 196f7d8d8 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME5, S81.STA.OWN.1 |
| claude/s81-frame5-rffwd-1020 @f9d44ffae | s81frame_col_h10_rf | 196f7d8d8 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME5, S81.STA.OWN.1 |
| claude/s81-frame5-rffwd-1020 @f9d44ffae | s81frame_col_h9_sr | 196f7d8d8 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME5, S81.STA.OWN.1 |
| claude/s81-frame5-rffwd-1020 @f9d44ffae | s81frame_col_h10_sr | 196f7d8d8 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME5, S81.STA.OWN.1 |
| claude/s81-frame4-1019 @6e02bff31 | s81frame_col_h9_sr | 87f5c33a1 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME4/5 |
| claude/s81-frame4-1019 @6e02bff31 | s81frame_col_h10_sr | 87f5c33a1 | - | 1 pass (lint) / 0 | 0 | PASS | S81-FRAME4/5 |

Note: the s81frame kits carry only a lint bench stage (no behavioural/mutant stage in job.json) -> submit_exact will
refuse them until a lockstep bench + mutant witnesses are added (S81-FRAME5).

Not run:
- claude/kv-sram-d2d-1019 @1c6c02ed7 (13 kits d2d_static_ovl/r7w_* + qfd_native59_dv_service): merge-tree has 17 text
  conflicts incl. bench-read RTL rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv, physical/common_flow/ot_rst_copies.*
  and tools/closure_loop + tools/ref_tile (pre_route_gate, source_binding, ...) -> owner must rebase first; sfm2 kits are
  superseded by KV-D2D3 sfm3 (claude/kv-d2d3-1020).
- claude/kv-gen9-1019 (epoch branch, merge only after constituents; its new kits sr7/sr7b/r7w_sfm2 = rows above / kv-sram-d2d).
- tools/test-only or no-kit branches (kv-clkfix2, s81-frame4-fwdclk, s81-frame5-fwdview, qw-gen3, s81-frame3-qxpqmerge),
  HBM next-release branches (hbm-*, l2h-bw-safe, toksim-hbm-*), kv-ahub3 (unchanged since REFILL-1830).
