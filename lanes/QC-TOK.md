# QC-TOK (lane file)
Branch claude/qc-tok-1024 (worktree localhost:~/wt/qc-tok), host intel1 for heavy runs.
## Current step
2026-10-24 13:40 PDT: started. Finding: all xt1/link-stage inputs lived on dead hosts (ot-gold1/2, ot-epyc7/9 scratch):
xt1 gold/masks (TOKe-QWM tokqwm-1023/xt1), link fixtures. bind_smoke.py fetches from ot-gold2 -> must regenerate from
the HF checkpoint (Qwen/Qwen3-8B @b968826d, reachable from localhost) + committed tools. STEWARD-TOKh/TOKi G5 runs
(tp8/xdie/ovl4u PASS, xt1 0/64) were never committed.
## Runs
- xt1 sub-lane (fork) -> branch claude/qc-tok-xt1-1024, intel1:~/scratch/qc-tok/xt1 (see section xt1)
- link sub-lane (fork) tp8/xdie/ovl4u -> claude/qc-tok-link-1024, intel1:~/scratch/qc-tok/link (see section link)
- R8 padding analysis: localhost (model + layout search), main-lane
## Results
## R8 padding (task 4)
- bound_r8 (P5 plan, qc12) = 870,428 pad flops; main plan P6 (qc-p6-r8 1f5b9bee3, probe bind) = 248,360.
- P6 breakdown: ~95% are REPLICA classes (one as-built same-cycle source broadcast to slice partitions at
  different hop counts): hw ctl->hc0..3 75.5k, su_l0/l1 vm_w* -> ctl/stm/sc/su_c 83k, fw cmd/hr/chd -> ctl/fe 38.6k,
  stm tw -> ctl/st_a 25.2k, fw/hc1 -> st_a/st_b 12.7k. Chains are gone in P6; what is left is tree depth spread.
- partition-lag retiming (LP) infeasible: every slice partition pair has plan round trips (positive cycles).

## OWNER?
## xt1 (sub-lane, branch claude/qc-tok-xt1-1024, worktree localhost:~/wt/qc-tok-xt1)
- 13:55 inputs regen on intel1:~/scratch/qc-tok/xt1 (venv ~/scratch/qc-tok/venv, HF Qwen3-8B@b968826d in ~/scratch/qc-tok/hf);
  TP8 L0 die0 image build pid 69012 (log build_img.log), pin = results/arch/qwen_tp8_native_dispatch_1014/actual_checkpoint_layer0/die0 matrix_int8 8f48f3f4
- 13:58 inputs regenerated: image matrix_int8 = pin 8f48f3f4 (REAL weights), x = stand-in (RMS-norm embedding tok 785), layout mismatches 0 (intel1:~/scratch/qc-tok/xt1/inputs).
  runs on intel1: bound_r8 near smoke (smoke.sh near, log smoke_near.log, work smoke_near); source control stage_xt1 landed pid 77679 (ctl/, ctl.log)

## link (sub-lane: tp8 / xdie / ovl4u on bound_r8)
- 2026-10-24 13:53 PDT launched intel1:~/scratch/qc-tok/link/run_all.sh (pid 85413): source assembly = git archive main 3e05af806b;
  fixtures rebuilt from git by commit (stage_link_fixtures.sh sources); bound constants: tp8 COLL_BENCH_ARGS
  "--relays 0 7 8 8 --lanes 2 2 10 2 2 10 --lx 12 4 12" (LS 389); xdie bound pair image D2D_DIE_STAGES
  2,2,2,3,2,2/34,34,32,32,32,31,31 (TXDP C 0a010308 / K 03030443 = constants); ovl4u --release-masters compiled for the same seam.
  Logs intel1:~/scratch/qc-tok/link/logs/{tp8,xdie,ovl4u}.log. Branch claude/qc-tok-link-1024 (~/wt/qc-tok-link).
