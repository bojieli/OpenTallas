# S81-J6-ASSEMBLY-R4 handoff (started 2026-11-21 07:2x PST; successor of S81-J6-ASSEMBLY-R3)
Work: epyc10 /srv/opentallas-scratch2/claude/s81-j6 (gate.sh, mk_cand.sh, j7/), hub intel2 /srv/opentallas-scratch2/claude/s81-j6-r2-hub. Lane clone epyc10 /srv/opentallas-scratch2/claude/s81-j6-r4/repo.

## J6 r1 (PORTFIX one-file repair)
- Pack DONE (CHAIN_PACKED): manifest 03230568, plan 44be6051, event a9ed808a98d, bind kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_work_bind_11210658, candidate lanes/handoff/S81_D8J6R1_source_candidate_1121.json.
- Apply REFUSED 07:5x (nothing switched): epyc10 SRC_MANIFEST SHARED-INODE. Cause: FAM-S81-SLICE-R3 trees made by delta-apply --link FROM d8j6r1 in its lane dir (epyc10 fam-s81-slice-r3/trees/src_s81_j6r1_t37fstart, src_s81_j6r1_l6). verify only accounts link children BESIDE the base (kw45). Needs those trees moved into kw45 (rename) or ot-deleted by their owner (FAM-S81-SLICE-R4), then: cd s81-j6-r2-hub && OT_LANE=S81-J6-ASSEMBLY-R4 bash j6r1_apply.sh $PWD/j6r1_pack_candC1n_pf.out > j6r1_apply.out ; then confirm post-apply strict bind + post unblock.
## Done
- HCP registry: cfg7 RDX entry PUSHED main c6a2270ccb0 (+test). svc 10 were already on main.
- S81 wave tools_sha -> a9ed808a98d5 (kit_wave 231c776891). retry_fix serdes__t4@2 fix=a0fc9811a19 (0eed5290bc). Struct stop s81|serdes__t4|bf6905ce91d07 kept until SERDES-R4 private kit s81_serdes__t4_1121074458 ends, then kit_wave.py struct-release.
- gate.sh / elab.sh / j7_post.sh / mk_cand.sh: python3 -I -B (no __pycache__ in trees).
## J7 (apply 11-22 04:15 PST)
- candJ7b (v2 plan 07c4124c): strict bind failed only leaf t23/t70/t72 duplicate fstart_N (FSTART + leaf local-reset rows both kept).
- v5 steps (= candJ7c): v2 + GEN rlybr_h9 (COL-R4 rows_rb_r1all/r2all, after mkdepth405, before mkxalign) + GEN leaf_lr_set (leaf local resets replace-by-key, replaces DELTA step) + x2 t2_payload (COL-H10-R2, J5 base) + u_cf MX re-solve b7d7dfef (COL-H10-R3, base j7/bases/j7_v2_plan_07c4124c.json; their gate oth-ubuntu-925383-1795276372). Gen scripts j7/gen/merge_rb_rows.py, set_key_from_delta.py.
- Gate: ot-run --mem 108 --threads 8 --hosts epyc10 --priority plan --plan-job bind --dir s81-j6 -- bash j7/chain_j7.sh candJ7c j7/J7c.list a9ed808a98d5 ; G0 must report tap-net sink inventory (8bc23a5a90, in a9ed) + street capacity.
- HELD OUT (FABLE-PD-S81-0830 §8 + COORD): leaf re-grid (LEAF-R6 SUPERSEDE on d245f293 only with green gate), t5 v1f without kv_leaf define op, lepe_mu_C split / xg move, serdes enc/dec split + PG rows until bound, bk_sel until place read, xo D2, kv_leaf t2 cut, colrom a10c16b8 until ROM handshake bench PASS.
- At J7 apply: kit_wave_edit event-pending s81 J7 when the apply gate starts; tools_sha stays >= a9ed808a98d5.
