# QC-TOK (lane file)
Branch claude/qc-tok-1024 (worktree localhost:~/wt/qc-tok), host intel1 for heavy runs.
## Current step
RESUMED 12:15 PDT (Claude). Adopted: Codex job intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_capacity_both16_v2
(capacity candidate codex/qc-capacity-1024 @72ece79138, 433,915 pads, xt1 both, lead 16; building since ~11:30).
Branch claude/qc-tok-1024 fast-forwarded to the Codex tip 210a1be64f, plus 9f6778464f (r8_tree receipts).
State of xt1: bound_r8 + CB16 pads + fill lead +6 (14): near 64/64, far 64/64 (Codex both14), hr+1 mutant caught
only by the fixed-edge schedule gate (numeric 128/128). The P5 cb16 chain verify and the cb16_tree verify both PASS
(2,723,870 matched, 0 mismatched, lint 0). Tree vs chain on the xt1 carve: EQUIVALENT (r8_tree/equivalence.txt).
Baseline bound_r8 lead 8 both: FAIL 0/64 near + far (intel1 smoke_both, expected).
MERGED main 7d75427c59 (link + xt1 recovery + opt-in trees).
12:25 adopted capacity both16 (lead 16) FAILED: near 0/64, far 0/64 (FAULT near_cluster at 296, far_cluster at 325; no
heads fault). Root cause B again: the capacity bind (P6 plan, codex-qc-a0, 430,195 pads) has CB16 leg skews of 18/12/2
(cb16b.py). Fix under test: cap_cb16 rebind with qc_cb16_pads_capacity.json (+789,504 -> 1,219,699 pads, 0 errors, 0
residual skew; only the 7 CB files change), localhost:/srv/opentallas-scratch/claude/qc-tok/cap_cb16 (verify running);
xt1 both lead 16 on intel2:/srv/opentallas-scratch2/claude/qc-tok/xt1_cap_cb16_both16 (run.log, building).
## Runs
- xt1 sub-lane (fork) -> branch claude/qc-tok-xt1-1024, intel1:~/scratch/qc-tok/xt1 (see section xt1)
- link sub-lane (fork) tp8/xdie/ovl4u -> claude/qc-tok-link-1024, intel1:~/scratch/qc-tok/link (see section link)
- R8 padding analysis: localhost (model + layout search), main-lane
## Results
- LINK (bound_r8, kv41): tp8 PASS 3/3 + 9/9 mutants FAIL (after MU calendar recompiled at LS 389: ls-378 fixture
  collided on UCIe -> mu cases refused); xdie PASS 9/9 + 13/13 mutants; ovl4u PASS 2/2 + 8/8 mutants.
  results/token_pass/qc_tok_1024/link/ (README).
- XT1 near (bind_smoke --local, bound_r8): FAIL nominal near 0/64 (FAULT heads cyc 181, near_cluster 286), mutant FAIL.
## R8 padding (task 4)
- bound_r8 (P5 plan, qc12) = 870,428 pad flops; main plan P6 (qc-p6-r8 1f5b9bee3, probe bind) = 248,360.
- P6 breakdown: ~95% are REPLICA classes (one as-built same-cycle source broadcast to slice partitions at
  different hop counts): hw ctl->hc0..3 75.5k, su_l0/l1 vm_w* -> ctl/stm/sc/su_c 83k, fw cmd/hr/chd -> ctl/fe 38.6k,
  stm tw -> ctl/st_a 25.2k, fw/hc1 -> st_a/st_b 12.7k. Chains are gone in P6; what is left is tree depth spread.
- partition-lag retiming (LP) infeasible: every slice partition pair has plan round trips (positive cycles).

## OWNER?
- CB16 leg alignment costs about 0.79M pad flops on every plan so far (P5 814k, capacity P6 790k), which is more than the whole
  capacity budget. Cheaper options need a decision: the plan puts n_a/n_b legs on equal hop counts (gen_plan r3 internal stations
  already exist on cbf/cbn na/nb), the CB16 node RTL gets a skew-tolerant join (a valid-aligned FIFO of depth = skew,
  narrow), or the compiler issues the two column halves at offset start times.
- R8 <150k: trees give P5 870,428 -> 587,936 (and P5+CB16 1,684,604 -> 1,402,112); P6-XT1 1,034,324 -> 985,040.
  Not reachable by trees: residual = single-source chains (P5 tw x-lane) + P6 replica stars + CB16 leg alignment
  (~0.8M). Needs a plan/compiler decision: CB16 legs on equal hop counts in the plan, or compiler-side skew absorption.
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

## CODEX notes
- CODEX took over: collect cb16/+6 fill results and run discriminating near nominal/mutant on codex/qc-tok-1024. intel2 smoke_cb16_near lead8 FAIL 56/64 (GU 0/8); lead14 existing near JSON PASS 64/64. Lead-sweep wrapper fails on absent gold_far.json because this is a near-only vehicle. New own ot-run job intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_near14 (log localhost:/srv/opentallas-scratch/claude/codex-qwen/xt1_near14.log), reuses existing binary. Full far vehicle remains to retest. Trees/bound smoke 0/64 expected with old lead/skew.

- CODEX own near lead14 retest nominal64/64 PASS. hr+1 mutant also numerically64/64 but shifts actual CW/result edges+1; original numeric wrapper is insensitive and remains FAIL. New separate fixed-consumer-edge sensitivity gate PASS (artifacts preserve both numeric PASSs), codex/qc-tok-1024 c6ec9651aa. Full both+CB16+fill6 build live intel2 scratch2/codex-qwen/xt1_both14 (~76GB elaboration), no duplicate.

- CODEX fullboth lead14 complete: nominal near64/64 + far64/64 (QKV/O/GU/down all exact), build3603s/sim680s/peak75.9GB. HR+1 numeric mutant ALSO128/128; timing-aware schedule gate catches changed actual CW/RS edges and PASSes. Original smoke wrapper FAIL preserved, no generated-die token/physical credit. Receipts results/rtl/qwen_xt1_both14_1024 on codex/qc-tok-1024.
