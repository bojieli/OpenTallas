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
