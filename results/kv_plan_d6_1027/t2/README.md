KV-PLAN-DELTA-6 task 2 (10-27, Tue Oct 27 18:12:27 PDT 2026). Base hm_r26q5c39 (pd sha256 4190246956824a7a); applied plan intel2:/srv/opentallas-scratch2/claude/kv-plan-d6-1027/t2/pd/hm_r26q5c39_t2.json (sha256 18adbc3d9009b824).
Apply: python3 t2_apply.py <codex-kv-q6-1351>/tools/die_plan <plan_dir> hm_r26q5c39.json hm_r26q5c39_t2.json <out>   (writes cores/*_r26d6.json into plan_dir too)
(a) D-KV-ECTLK-NARROW-D6: qkd_ectlk_q0/q2 216x172.8 -> 155.52x172.8 SW anchor, 16 hard_core records (kv3_hg, _v3, _v1, _v1p2..p6), 16 clock taps x -30.24.
(b) D-KV-PVPAIR-SPLIT-D6: pv_pair_slice_split.json (kv_core_slice form, not a plan field).
G0 (codex-kv-q6-1351 check.py): base PASS 0 err/1863 warn; t2 PASS 0 err/1863 warn, identical finding set.
