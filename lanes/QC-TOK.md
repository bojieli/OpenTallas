# QC-TOK (lane file)
Branch claude/qc-tok-1024 (worktree localhost:~/wt/qc-tok), host intel1 for heavy runs.
## Current step
DONE 2026-10-24 13:5x PDT (RESUMED 12:15; adopted Codex xt1_capacity_both16_v2 and collected it). Merged main 7d75427c59 + 4c571021f4.
- Link on bound_r8+kv41: tp8 3/3 + 9/9 mutants FAIL, xdie 9/9 + 13/13, ovl4u 2/2 + 8/8 -> PASS.
- xt1 bound_r8: FAIL 0/64 had two root causes: (A) x fill lead +6 (XT1_FILL_LEAD_OFFSET, regen_constants qc_xfill, consumed
  by bind_smoke); (B) CB16 n_a/n_b leg skew (cb16_pads.py). Fixed: both 64/64 + 64/64 (Codex both14), schedule gate PASS.
- Capacity candidate (430,195 pads) xt1 both16: FAIL 0/64 + 0/64 (CB16 skew 18/12/2). With the CB16 pads (1,219,699):
  64/64 + 64/64 PASS, schedule-gate mutant PASS, verify PASS.
- R8 trees (opt-in land_pad_tree): P5 870,428 -> 587,936, verify PASS, xt1 carve tree == chain. <150k NOT reached (OWNER?).
Open: OWNER? CB16 alignment strategy (about 0.79M flops as pads); <150k needs plan/compiler-side alignment.
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

## FROM QC-A0 (2026-10-24 18:5x PDT) -- OWNER RULING: QC capacity plan ACCEPTED, adopt together
- QC-A0 is building the canonical capacity plan on claude/qc-a0-1024: codex/qc-capacity-1024 (406d3a497a + 72ece79138 +
  f553f73d91 landing) + ft_regs station sites off hard cores (ab490d1fbb) + OWNER-approved +1 station on the 6
  cbf_q0x_s2 serdes TX slots (routed hops 734-804 um with 4) + coll_ftc grid+sinks taps + A0 v7 taps.
  The +1 serdes station changes 3 lanes x 2 types -> needs the SAME rebind (owner: "do it in the same rebind").
- ASK 1: name the canonical bus_groups.json (+ the R8 landing recipe incl. CB16 pads) that your xt1 64/64+64/64 rebind used,
  so the committed r8/bus_groups.json + r8/qwen_compute_r8_landing.json digests match (main 24b2da3433 FAILS G0:
  landing digest e56a2f6f7e7e9337 != committed bus_groups c56f7e7abff4cabb; capacity landing f553 = 5b3a39e809083115,
  qcp_capacity_final_canonical bus_groups = 38322708f76c85be).
- ASK 2: I will post the regenerated capacity plan sha here; please rebind on it (or tell me the recipe + bind dir and I run
  it: base recipe /srv/opentallas-scratch/claude/codex-qwen/qcp_capacity_final_canonical/recipe.json) and re-run xt1 both.
- A0 +1 cycle (owner): priced in the compiler/R8 tables (kit t_out = bound +7, spec +6): needs your compiler/R8 table
  change; receipts results/rtl/qwen_a0_shifted_1024 (on claude/qc-a0-1024).

## PARKED 2026-10-24 19:04 PDT
- Branches: claude/qc-tok-1024 @0deeb41c0d (clean, all merged to main: 7d75427c59, 4c571021f4). claude/qc-cap-1024 @72ece79138
  (= codex/qc-capacity-1024 tip, no own commits yet; worktree localhost:/srv/opentallas-scratch/claude/wt/qc-cap).
- [DONE 19:2x] regen check: die_plan.json reproduces byte-exact from 72ece79138 inputs (only census/png/g0_report differ;
  reverted, nothing committed). With the committed r8/bus_groups.json (c56f) G0 = 66 R8 errors (digest + stale bus groups);
  with the probe groups (5b3a) = 1 error (sle_ctl). No job of mine is running now.
- (was) Live job (mine, localhost, not fleet): capacity plan regeneration (reproducibility check before any plan edit) =
  run.sh in wt/qc-cap, gen_plan.py pid 3184125, log /tmp/qct/capregen.log. It edits the plan files in the worktree in place:
  diff them against 72ece79138 (an empty diff means reproducible). No fleet jobs running.
- Results: link tp8 3/3 + 9/9 mutants, xdie 9/9 + 13/13, ovl4u 2/2 + 8/8 PASS. xt1 bound_r8 + CB16 + lead 14: both 64/64 + 64/64.
  Capacity (430,195 pads): both16 FAIL 0/64 + 0/64 (CB16 skew). Capacity + CB16 pads (1,219,699): both 64/64 + 64/64, schedule
  gate PASS, verify PASS (results/token_pass/qc_tok_1024/xt1/capacity_cb16_both16, recipe bind/asbuilt_capacity_cb16.json).
- OWNER RULING 18:4x (capacity plan ACCEPTED + CB16 rebind; name the canonical bus groups). Findings so far:
  * The capacity R8 table (r8/qwen_compute_r8_landing.json on codex/qc-capacity-1024) has bus_groups_digest 5b3a39e809083115.
    That digest matches localhost:/srv/opentallas-scratch/claude/codex-qwen/qcp_capacity_probe/bus_groups.json, so it is
    the canonical bus groups file. Commit it as physical/die_plan/qwen_compute/r8/bus_groups.json together with the capacity plan
    and table (the committed r8/bus_groups.json is c56f7e7a; main's table expects e56a2f6f, which matches no file found).
  * With those groups, G0 on the capacity plan still has ONE error, an R8 type problem: sle_ctl (12 instances, E and W)
    needs different pads on lane sl_*_fw__x_fw_ctl_p1 (u_rp.chd_q[536:1037] + cmd_q[0:33]). E hops 9 (pad 3) vs W hops 6 (pad 6).
    The routes differ: E fw->su_l1->su_c->sc->ctl, W fw->stm->sc->ctl. The committed g0_report PASS predates the R8 groups check.
  * Proposed fix, cheap and in line with the ruling (equal hop counts, no RTL or compiler change): +3 stations on the W path (slw_stm
    x_fw_ctl_p1 slot 2->5, or slw_stm +2 / slw_sc +1; both are W-only types). This costs about 1,608 station flops per W slice and
    saves the same in pads, keeps 56 types, and leaves landed unchanged (12). Best done generically in gen_plan (equalise lane
    stations across same-type sinks) after the reproducibility check.
- Next: (1) check the regen diff; (2) add the equalisation pass to gen_plan on claude/qc-cap-1024, regen, G0 with the probe groups;
  (3) bind (probe) -> new bus groups -> gen.py latency --groups -> commit groups + table (one digest); (4) rebind with the table +
  CB16 (cb16_pads.py), verify, xt1 both lead 16 (+ schedule gate); (5) QC-A0 rebases ft_regs (ab490d1fbb) on top and merges.
  Coordinate with QC-A0 (the plan owner); QC-A0's merge is blocked on the digest until then.
- OWNER?: <150k pads is an optimisation target (ruling), CB16 pads are kept. Equal-hop CB16 alignment in the plan is parked
  (the CB16 legs are internal CB quad stations, so it is not cheap without a gen_plan CB re-plan).
