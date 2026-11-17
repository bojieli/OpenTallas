# KV-R3 handoff (2026-11-17 ~05:55 PST) — KV die owner, successor of KV-R / KV-R CODEX

## Root causes of D14 TERMINAL FAIL 98e4c42f519c (GEN_LINT)
1. **bind_cells.sv prefix**: the wave stages bind_out into kit-store snaps (/kit-store/snaps/780b.../root/.../kv-r/d14_bind); the
   D14/D15 tree tools (gen_phys.py 64c62fd1, kit_gen_lint.py 2485da0c) predate the kit RTL input-closure and compare the snap path
   with the raw bind_out root -> "outside the kit source tree". Fix = approved current-main closure export/validator
   (Codex transplant E7 kv-r/d14_prefix_closure_1117/overlay: gen_phys e29e6df5, kit_gen_lint 4ead4e22; replay PASS + hash mutant caught).
2. **ECTL params**: views of record kvhg1_views_1116/qkd_ectlk_q0..q3 were built at QK 37 / RL 26 (E10 fable-fix-kv-pv-ectlk/q*_m10_p2
   mem.json 100101/11010, KVRL_NOTE 11-15); plan + part_bound request 37/26. WRONG SIDE = frozen source guard
   columns_fixed_at_13_0_34_18 (D14/D15 kiss_st_cols 25d9efac, columns e3970fd0). Codex cd1d167a1d1 restored 37/26 but forwarded
   #(QK,RL) into u_q0..u_q3 = liberty macro cells (no params) -> "qkd_ectlk_q3 has no parameter RESPONSE_LAT".
   My fix **claude/kv-ectlk-hardcore-noparam-1117 @ca21e3176e49c290034802c0cc4d3bde8588d76e**: no overrides on the macro instances,
   guard in qkd_ectlk_columns at 37/26. Yosys (kit_gen_lint frontend, E10 kv-r3/ytest): 37/26 PASS; 34/18 caught; cd1d reproduces u_q3 error.
   ot-gate-remote: intel2 ~/tmp/kv-r3/ectl_gate.log (queued on epyc2 at 05:40, E7 root fs < floor).

## HG5 (D15) strict bind: PASS (E7 kv-r/hg5gate/gate.out, done 05:32)
PRE 0, G0 0 errors, bind 0 errors / 2545 crossings / 429530 bits, LATCHECK 2404/2404 delta {}. But bind.f points at D15 tree's
34/18 ECTL source, so D15 itself would repeat the GEN_LINT FAIL -> not published. No D15 GEN waiter left (PID 972345 gone).

## D16 = D15 + 4 files (GEN_LINT repair only), built + gated ON THE FINAL TREE on epyc10
- tree epyc10 /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg5_340b90be_d16 (plan 340b90be33dd unchanged), protected
  (lanes/PROTECTED-DBS.txt, coord e9a6298d43e). Script epyc10 kv-r3/build_d16.py + gate_d16.sh; out epyc10 kv-r3/d16gate (gate.out).
- unit oth-ubuntu-1263885-1794923279, log intel2 ~/tmp/kv-r3/d16_gate.log (plan priority, --plan-job bind).
- Publish waiter intel2 PID 1472353 tools-converge/kv-r3/run_d16_publish.py (log ~/tmp/kv-r3/d16_publish.log): waits ALL_DONE,
  asserts PRE/G0/bind/LAT, tree_check, cheap static, then r471 publish dry GEN kv3_hg_v1 on gen_host epyc10 (commit=True).
- NEXT: on PUBLISH PASS -> apply with pilot kv3_hg_v1 (find apply cmd: KW00 apply_reviewed_tree_marker.py; HG3b switch notes in KV-R.md),
  READY post for ca21e3176e4 after GREEN.

## Not mine / preserved
E7 D14 restore + intel1 copy 3777547 (stopped, preserved); E7 kv-r/d14_prefix_closure_1117 (Codex evidence); epyc7 disk 47 GB (floor 50).
