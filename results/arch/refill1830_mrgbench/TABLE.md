# REFILL-1830/MRGBENCH 10-19: READY_TO_MERGE on-main bench + mutant regression (Verilator 5.050, ot-epyc9)

Scan: 58 READY_TO_MERGE branches not on origin/main; every release-relevant one already carries its own committed
fleet 5.050 receipts (positive + mutant fail witnesses) on its branch base, so no branch lacked receipts. Value added
here: the same kit job.json stages.bench (closure-daemon verdict semantics: pass = rc 0 + pass_regex; mutant = fail_regex
seen) re-run on `git merge-tree origin/main(22137b39b) + branch` -- i.e. what the daemon would see after merge.
Snapshot = git archive of rtl tools physical/common_flow + kit extra_paths + cmd-named paths (paths.txt; pc3 also
physical/ref_tile/qkd_kvs_pc{,_h}_rl1, read by kvpc_sram_bench.py -- first try failed 24/25 on that missing input, rerun).
Conflicts listed are text conflicts of merge-tree in files NO bench reads (owner resolves at merge).
kv-host2 has no kit: host2_job.json = run_post_uid_slot.sh cases (4 positive/negative-detect PASS, 3 mutants FAIL).

| branch | kit | merge tree | merge conflicts (not bench-read) | stages | unexpected | verdict | owner |
|---|---|---|---|---|---|---|---|
| claude/kv-ahub3-1019 @500985c55 | qkd_ahub_g2l | cf7417614 | - | 3 pass / 6 mutants | 0 | PASS | KV-AHUB3 (LEAD2-KV) |
| claude/kv-attn2b-1019 @69bab6da2 | qkd_kvs_attn_rv3 | 46a4cd619 | tools/die_port_bind.py | 2 pass / 7 mutants | 0 | PASS | KV-ATTN2 (LEAD2-KV) |
| claude/kv-attn2b-1019 @69bab6da2 | qkd_kvs_attn_rv4 | 46a4cd619 | tools/die_port_bind.py | 2 pass / 7 mutants | 0 | PASS | KV-ATTN2 (LEAD2-KV) |
| claude/kv-dcal2-1019 @e2ce1fa6f | ot_qkh_ktree_lk | 837ad1517 | tools/qwen_split/d2d_link_calendar.py | 2 pass / 1 mutants | 0 | PASS | KV-DCAL2 (LEAD2-KV) |
| claude/kv-dcal2-1019 @e2ce1fa6f | ot_qkh_ktree_lkp | 837ad1517 | tools/qwen_split/d2d_link_calendar.py | 2 pass / 1 mutants | 0 | PASS | KV-DCAL2 (LEAD2-KV) |
| claude/kv-host2-1019 @f5cdb27df | post_uid_slot | 189081cc8 | - | 4 pass / 3 mutants | 0 | PASS | KV-HOST2 (LEAD2-KV) |
| claude/kv-pc3-1019 @2343b9072 | qkd_kvs_pc_h_sr6 | 5efe2e2cd | tools/qwen_kv_die/kv_static_die.py | 9 pass / 16 mutants | 0 | PASS | KV-PC3 (LEAD2-KV) |
| claude/kv-pc3-1019 @2343b9072 | qkd_kvs_pc_sr6 | 5efe2e2cd | tools/qwen_kv_die/kv_static_die.py | 9 pass / 16 mutants | 0 | PASS | KV-PC3 (LEAD2-KV) |
| claude/qw-cluster3-stream-1019 @76690aa6e | qfd_dv_stream_t_1019 | 954d7a483 | - | 2 pass / 7 mutants | 0 | PASS | QW-CLUSTER3 (LEAD2-QW) |

Not run: mu-kv-ctx (merge conflict in bench-read d2d_cal_image_mu.svh -> owner must resolve first), hbm-safe-k9r (RTL conflicts sfu_core_split2/3 + common_flow), Qwen dv2f* lineage branches (not main-mergeable; REFILL-1725/QWLAYER covered ctlm4/sysface3/gen3c), kv-pc2/grp2/emb2/health (REFILL-1725/KVREG 102/102), tools/results-only branches.
