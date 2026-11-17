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

## UPDATE 07:3x PST — D16 APPLIED
- D16 fresh gates (E10 kv-r3/d16gate): PRE 0, G0 0 err, strict bind 0 err / 2545 crossings, LATCHECK 2404/2404 delta {}.
- Publish r471 PASS (record commit bf398cf88bd): dry GEN kv3_hg_v1 on E10 DRY-PASS, **GEN_LINT PASS all 6** (kit_rtl_paths PASS, rtl_check PASS, memory_bits PASS).
- Applied 07:17 (KW00 apply_reviewed_tree_marker, expect D10/KV-HG1): die src = kw45/src_kv_pin_eb1e73448bd0_hg5_340b90be_d16,
  event KV-HG5, gen_hosts [epyc10], pilot kv3_hg_v1, hold release gen_pilot:qwen_kvsys:d9187b9c24f1. Receipt
  lanes/handoff/qwen_kvsys_atomic_apply_1794928647528162651.json; kit_wave commit 39a8a324aad, switch record 794ae124a26.
- 9 "waits on child core" rows (kv3_hub_Eo/Wi/Wo, kv3_pc__cl254f2e73/__cl5a95b461, kv3_pc_v1 x3, kv3_pc_v3) are LINT-ADVISORY
  (launch on PROVISIONAL child views, KW-PROV-1) on the old D10 plan; they release with the pilot hold once the wave's kv3_hg_v1 GEN
  on D16 passes. Not hand-released (system gen_pilot check).
- ECTL branch READY posted: claude/kv-ectlk-hardcore-noparam-1117@ca21e3176e49 GREEN 1/1 (main 2382f7a6fba).
- FLEET: replicate D16 to more gen hosts if wanted (only on E10 now).

## HG6 (COORD dispatch 07:3x, FABLE-CLOSURE-STRATEGY lever 3) — NEXT, NOT STARTED
One event on D16 plan 340b90be33dd: (a) bays-only carve rows E9 kv-pc-delta/wt/results/kv_pc_delta_1117/HG6_PC_bay_rows.json
(branch claude/kv-pc-delta-1115@51a44abe9f2 / 60939a26af: 0 collisions, 36,718 of 36,984 um2 kept, clock rows byte-identical);
(b) 25 ring->bin stations on the 3 kv3_pc_v1 types as partition_types.<t>.internal_stations (schema form exists:
conn "bus:<bus>", from_um/to_um/regs_um, bit_sites_um; realize_internal_stations true). Inputs: ring_to_bin_model_lower_bound.json
(mechanism: move u_bin to first <=380 um segment + uniform payload/epoch stations, last at old bin), ring_to_bin_macro_clear_plan.json
(obstacle-aware, NO legal sites allocated yet), ring_to_bin_measured_geometry.json (607 paths, 20 buses, worst 1,436 um).
Steps: allocate legal sites off macros/rows-B reservations -> rows JSON -> compose plan -> PRE/G0/strict bind/LATCHECK (cycles
priced; bank re-site only if a latency group breaks) on the final tree -> publish dry GEN -> apply. Fable diff review in parallel.

## 11-17 HG6 v3 (after FABLE-PLAN-KV-HG6)
- reach_fix fix run stopped (exact PID 2761681 on epyc10); its output plan unused.
- composer v3 epyc10 kv-r3/compose_hg6.py (copy on epyc8 kv-r3/): blocks = cores+2.16 (nominal+track offset), ALL post-carve reserved_sites_um rects of the 3 PC types (S1), macro gaps <12 um (S2, 36 slots), footprint 1.404x0.27; u_bin pinned via face_bit_sites_um at L/(k+1), stations at L(j+1)/(k+1), last at old bin (S3); every site <=195 um from a grid tap (S5, no tap re-cut).
- plan_hg6_v3.json sha 3ec92f084ef8 (latency regenerated 2404 lanes); audit_hg6.py: on_reserved 0, in_slot 0, core_clear 0, overlaps 0, tap_max 195 (all 3 types); PRE RC0; reach c1 2/205.1 c2 1 c4 0 = D16 baseline. 40 banks/type, 1208 station flops + 607 u_bin sites, +960 lane-cycles, worst bit hop 402.9.
- D18 tree epyc8 /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg6_3ec92f08_d18 manifest 8ac400a6ffd9 (rsync of D16 + plan swap), protected.
- gate: epyc8 kv-r3/run_gate_d18.sh via ot-run --priority plan -> kv-r3/d18gate/gate.out.
- publish runner intel2 tools-converge/kv-r3/run_d18_publish.py ITEM commit|nocommit; run 1 = kv3_pc_v1__cl23f6a148 nocommit (Fable S6 dry GEN), log d18_drygen_pc.log; then kv3_hg_v1 commit, then apply.
- epyc10 scratch2 hit 5 GB free 11-17 (recovered to 153 GB); D17 tree unprotected but ot-delete SKIP (kit_wave ref) -> left.
