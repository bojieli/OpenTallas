# FAM-S81-COL-H9R0-R2 handoff (successor of FAM-S81-COL-H9R0; started 11-21 05:0x PST)
Family: S81 col_h9_r0_p1..p6 (~60 unsigned). Predecessor history: lanes/handoff/FAM-S81-COL-H9R0.md (scripts, rows, J7 order).
## Live (05:1x)
- J5 wave route jobs (hub autopilot/state.json): rep pva4376595 0d6487d7a8c6 (work dir intel1 key-cardinal ot-jobs, DRT iter0 50%); pvd2159f4a 4e4323c4d5b1 (work epyc10, DRT iter0 60%); pva2793873 3283f16cae2b (epyc10, DRT iter0 70%); pv11b73b67 64e24c10ad78 (epyc10, DRT 90% 17k). NB state.json host field differs from the work-dir host; trust ot-jobs dir.
- bind1 (gate A, seg405+xalign, no xo) running intel1 oth-ubuntu-2073865-1795265819 (bind_otrun.log); bind2 (+xo D3) running intel1 oth-ubuntu-2230553-1795266161 (bind2_otrun.log).
- hub intel2 chain2.sh pid 1585663 waits bind2 RAN -> kit_wave run-item fam-s81-col-h9r0/wave/spec.json (event famh9r0s2) -> place/geom.
- Waiter: rtx-pro background poll (scratchpad h9wait.sh) on all of the above.
- TOKEN-1121 asked 05:03 about +3 cycles on the col_h9_r0 xo lane; no answer yet.
## Next
- On bind RAN: read BIND/LATCHECK/G0_BASE vs G0_NEW (g0_base*/g0_new* dirs); fix red.
- After chain2 place PASS: route the private kit: intel2 `ot-run --mem 64 --threads 16 --disk 40 --hosts intel1,epyc10,epyc7,epyc8 --dir $G -- bash $G/run_kit.sh $G/<type> route 64 16` (G = gen dir; not epyc9).
## COORD correction 05:2x (FABLE-CLOSURE-0600)
- Rep GRT -15.6 was the FF line; TT is -74.3. Residual = ROM-input stage (lever 1, per-type RDX from as-built names). Do NOT expect the J5 wave jobs to sign; they keep running (any-plan, may still inform), no TT repair retries on ROM-pin endpoints (stop list).
- Plan: private kit 1 = bind2 (seg405+xalign+xo) via chain2 (place/geom evidence). Variant = src3 = src2 + R3 gen_rdx_rows.py (intel1 fam-s81-col-r3, --type-re ^col_h9_r0_) + die define OT_S81_CFG7_RDX at bind (rows alone are a functional error) + cfg7 seq repointed to signed ot_s81_cfg7_seq_rdx_1121 view -> bind3 -> kit -> route. This is the signable candidate. J7 order then: R3 relay rows -> R3 xalign -> mkdepth405 -> mkxalign ^col_h9_r0_ -> mkxo -> gen_rdx_rows (R3 owns the RDX rows on J7).
- 05:26 VARIANT LAUNCHED: plan_d405xo_l1_j5.json = plan_d405xo_j5 + R3 mkplan2.py (copy mkplan2_r3copy.py) on rep pva4376595: +104 ROM input rows, +12 qbank output rows, +35 RD_EXTRA q rows (sha 3302aa29 in src3). bind3 ot-run intel1 client pid 2802815 (bind3_otrun.log). Hub chain3.sh pid 2215689 (fam-s81-col-h9r0/chain3.log) -> run-item wave3/spec.json (event famh9r0s3) -> place/geom. Private: RD_EXTRA rows need the die define OT_S81_CFG7_RDX + signed cfg7 rdx view to be signable (R3 gen_rdx_rows.py handles the view repoint).
- Cleanup: l1tmp/ (hardlink copy of src2 plan dir used for mkplan2 pins lookup) -> ot-delete once bind3 is done.
- 05:3x COORD: lever 1 (RDX + ROM pval generator) owned by FABLE-FIX-S81-COLROM. Posted bind3/chain3 as a test-case offer; await its answer (use as test case / drop). Keep seg405/xalign/xo rows (ours).
- 05:4x COORD ruling on xo +3: accepted if bind2 LATCHECK passes (strict, depth-aligned, no LAT diff on the xo lane); no wait on TOKEN-1121. If LATCHECK flags the xo lane, post the exact row to COORD. Keep bind3 until COLROM answers.
## 05:4x COORD WAVE-ENV ruling (d442c09bb6e) applied
- Old chain2 (1585663) and chain3 (2215689) stopped by exact PID (both were in their bind wait loop; no kit made). Binds untouched.
- wave/spec.json + wave3/spec.json: gen_env += OT_NATIVE_RESET_SCOPE=selected, OT_GEN_M8_GRANT=1 (item_env cl9f71e63d / cl9f71e63d__pv* of the J5 wave; rest already = die_gen_env J5 + item_env), dry_gen=true.
- New hub chainb.sh N WAVEDIR: wait bindN -> run-item (dry_gen: kit_rtl/gen/lint/preflight) -> diff config.mk (normalized, path basenames) + kit_effective_env.json + flow_tag vs J5 wave kit (epyc10 kw43-wave-1109n .../attempt_3/gen; ref copy wave_ref_config.mk) -> on match: ot-run run_kit.sh K route 64 16 on intel1 (G/route_otrun.log); on diff: post ENVDIFF, stop.
- Running: chainb2 pid 2665583 (chainb2.log, bind2/wave), chainb3 pid 2665584 (chainb3.log, bind3/wave3).
- COLROM 05:36: own generator gen_colrom_rows.py (epyc10 fable-fix-s81-colrom), own rep col_h10_r1; says R3 gen_rdx_rows emits wrong u_rN_ names on 6 sub-families. My bind3 used mkplan2 (per-type, plan inst names); strict bind will show. Bind3 kept until COLROM answers on it.
## 06:0x bind3 DROPPED
- Not a valid proof: R3 mkplan2 put 7 RD_EXTRA q rows on u_r0_u_s4 (ot_s81_cfg7_seq_bfp, which has no RD_EXTRA; COLROM generator skips bfp) and the J5 tree has no OT_S81_CFG7_RDX define / RDX view. Names themselves were right for col_h9_r0 (bound leaves keep u_u_r0_ prefix).
- bind3 cancelled (ot-run --cancel oth-ubuntu-3059420-1795268158, exit 143), chainb3 2770522 stopped by exact PID; bind3/ src3/ l1tmp/ deleted with ot-delete. chainb2 (bind2, seg405+xalign+xo) remains the only rep kit chain.
- Lever-1 path: COLROM tree1 (epyc10 fable-fix-s81-colrom, candJ7RDX + gen_colrom_rows, define/view/registry/reprove) whole-die gate1 running. Asked COLROM: after GATE PASS I stack mkdepth405 -> mkxalign ^col_h9_r0_ -> mkxo onto its plan for the h9_r0 rep (signable form), or COLROM includes the rep.
## 06:1x-06:3x
- bind1 + bind2 GREEN (BIND_RC 0, LATCHECK_RC 0; bind2 LATCHECK 873/873 PASS, delta {}) -> xo D3 accepted (COORD 05:4x ruling). G0 in bind*.sh was an arg error (check.py has no --json-only); corrected G0 base/new1/new2 = intel1 g0.sh via ot-run (g0_otrun.log). NB COLROM/assembly run G0 with --street-rule warn and compare via s81-j6/g0cmp.py.
- chainb2 (pid 2770520) in kit_rtl/gen (dry_gen) since 06:12 -> config.mk diff -> rsync gen dir to epyc8+epyc10 -> ot-run route from epyc8 --hosts epyc8,epyc10.
- COORD option 1 (stack on COLROM plan) -> I posted a change: J7 v2 (S81-J6-ASSEMBLY-R3 candJ7a/b) already carries RDX + mkdepth405 + mkxalign + mkxo; tree1 is not a manifest tree. Plan: build rep from the J7 published src_manifest tree when J7b gates green. Scripts staged on epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0 (mkdepth405.py, mkxalign_r3.py, mkxo.py) in case COORD insists.
- Waiters: route jobs (h9wait 1 1), G0, chainb2, COLROM gate1, answers (h9ans).
