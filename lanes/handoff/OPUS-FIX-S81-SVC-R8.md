# OPUS-FIX-S81-SVC-R8 handoff (started 11-21 10:3x PST; successor of OPUS-FIX-S81-SVC-R7). Nothing signed or exported yet.
Work dir epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r8 (scripts also in that dir).

## LIVE (re-arm waiters first)
- chainJ7 epyc10 PID 1506228 (chainJ7.sh, log chainJ7.log): bind_j7.sh (elab -> strict bind --all-gaps -> LATCHECK, treeJ7) -> STATE;
  green -> prep_j7.py att + rest kit preps in parallel (kit_att/, kit_rest/; KSTATE_att, KSTATE_rest; config.mk diff gate vs wave_ref).
- H8 proof chains (COORD: keep as type_split-fix proof only): chain10i epyc10 PID 224179 (R7 bind_hi4x), chain_rest8i epyc8 PID 2379962.
- J8 generator trial: epyc10 j8/job_g4.sh (gen16yc4.py = R7 gen16yc3 + keepouts for FT station blocks + landing band rects) on hi rs t1, t3; out j8/out_g4.

## Ruling 1 (hi4 on J7, deadline bind + both preps clean ~19:00 PST, else J8)
- j7pre/plan_pre.json = gen_hi4_j7pre.py on J7 v5 (03c17773): J7 hi4 + (H8 r5b -> preview) 3-way + x_epoch compose (replay reproduces H8 E exactly;
  on J7 only band monitor_0 moves with J7 collector child) + ATTCUT renames + ub tap fix (32/32).
- treeJ7 = candJ7c hardlink copy (mk_tree_j7.sh, native_bind/out excluded) + overlays: svc_rs att/mem_ar/rs.sv from 9bd318e90366 (R5 tree; J7 svc RTL == H8 HEAD),
  s81_svc_r5_hi4_sources/*.sv, SRAM bb.v, bind/inputs/map_census_r5.json. Manifest treeJ7/asbuilt_r8_hi4_split_j7.json (mk_manifest.py: candJ7c + 3-way hi4 rows).
- Split: spec_j7.json, split_j7.sh (band-test tools with R7 core-tap patch) -> treeJ7/physical/die_plan/s81/split_hi4x (SPLIT_RC 0).
- Trial: PLAN split plan_c BASE v5 onto J7 v6: BUILD_OK.
- Package for R4 after green: PLAN line + manifest ops (asbuilt_vN keys vs candJ7c) + FILE lines (split_hi4x dir, RTL overlays, map, SRAM bb).
## Ruling 2: type_split core-tap fix: FLOW-STRIPBODY-1121 commits (posted 10:5x); if not on main by 15:00 PST, R8 pushes R7 patch
  (epyc10 opus-fix-s81-svc-r7/repo diff, base 197076cf03) via ot-push-main.
## Ruling 3: svc_s1 GEN NOT in J7 v6 steps -> asked R4 to confirm for candJ7d.
## Ruling 4/5 (J8): lo = single types (no split); census of lo real failures still to do (all 8 were STRUCT-STOP cancelled at place 11-21 02:0x).
  hi: keep y cut; t1/t3 fix trial = keepouts (gen16yc4).

## UPDATE 11-21 12:4x PST (newest)
- H8 chains ended: bind/LATCHECK green; both preps pass kit_rtl (core-tap fix proven) and FAIL generate "plan invalid" 6 ports = type_split
  defects A (offset piece N/S bus windows in parent frame) + B (FT cut port windows != slot ends, overlap L* cut ports). Reported to STRIPBODY.
- Lever 8: same spec through STRIPBODY lc splitter == my split (only out-dir relative paths differ). Use their splitter going forward.
- J7: chainJ7 (PID 1506228, pre-fix plan_c, evidence only; its preps will fail generate). chainJ7b PID 263082 = plan_c_fx.json
  (fix_cut.py post-pass: 0 mismatches, 0 cut-line overlaps) -> bind_j7fx.sh (bind_out_fx) -> STATE_FX -> prep_j7fx.py kitfx_att/kitfx_rest
  -> KSTATE_FX_*. On both PREP_OK: python3 -I mk_pkg.py -> pkg/hi4_j7.list (PLAN plan_c_fx BASE v5, mo_svc_hi4_split_j7.json, FILE lines,
  HOOK hook_sidecar.sh 3-way sidecar merge) -> post to R4 before 19:00 PST, else hi4 -> J8.
- J8 hi: all 7 compose. t3: out_g5c (R8_KEEP [[0,1]] R8_BANDBOX attn_i2,attn_i1). t1: out_g6f (gen16yc6, R8_KEEP [[1,1]] R8_FTKEEP ft0,ft1
  R8_DY 260 BANDBOX attn_i2,attn_i1). Others per R7 (gen16yc3). Next: combined run, J8 splits, fix_cut, bind.
- lo: wave attempts only ever failed die-wide kit_rtl (leaf__t12 reset reach) then STRUCT-STOP; J8 single types + struct-release.
- svc_s1 GEN (REACH>405) not seen in J7 v6 steps; asked R4 (no reply yet).
