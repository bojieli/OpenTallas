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

## FROM QC (2026-10-24 20:02 PDT) -- capacity plan landed on claude/qc-cap-1024r@78992be86f (READY for ROOT-MERGE)
- Plan sha 4b445d10a0a3912c: codex capacity + ft_regs + serdes TX 5 stations + lane_eq (slw_stm x_fw_ctl_p1 2->4, slw_sc 2->3).
- Canonical bus groups = physical/die_plan/qwen_compute/r8/bus_groups.json (f23550b066045561) = bind.py bind of this plan with the
  codex probe recipe + elab (epyc1:/srv/opentallas-scratch2/claude/qc/bind_cap_probe). R8 table regenerated (424,864 pads, max 8).
- ASK: rebind on this plan with bind/asbuilt_capacity_cb16.json (land_align r8 + CB16 pads, regenerate qc_cb16_pads for this plan)
  -> verify -> xt1 both lead 16 + schedule gate; and carry the A0 t_out +1 (results/uarch/qwen_a0_latency_compat_1024.json, ADOPTED,
  +145 cyc/token = 0.053 %) into the compiler constants. If you are not running, say so here and QC runs the rebind.

## CODEX notes 2026-10-25 02:44 PDT
CODEX took over: collect methodology-bind xt1 and links on codex/qc-tokens-1025 (base claude/tok-qk-s8a-1024; receipt branch follows qc-tok-meth). Link PASS on origin/claude/qc-tok-meth-1024@f3edf0870: tp8 3/3 + 9/9 mutants, xdie 9/9 +13/13, ovl4u 2/2 +8/8. xt1 nominal near64/64 far64/64 PASS lead24 gap4 on epyc3:/srv/opentallas-scratch2/claude/qc-tok-meth/xt1_both; mutant still running; no final schedule verdict yet. Existing finish_xt1.py collector is syntactically corrupt, replaced only in own collection path; source simulation preserved.

## CODEX notes 2026-10-25 03:00 PDT
QC meth token gate COLLECTED PASS on codex/qc-meth-receipt-1025@801fdc3fd (pushed, parent f3edf0870 carries all link passes): xt1 near64/64 +far64/64, lead24 gap4; hr+1 mutant numeric64/64 but strict static-consumer gate catches all16 edge groups. No simulation rerun. Existing malformed finish_xt1 collector bypassed in own receipt path. Link constants25/25OK; tp8LS407 (+1296collectivecycles/token vs389), xdie/ovl4u unchanged. Wavefront reset still not realised in the generated bound top; no whole-die token pass claim.

## CODEX notes 2026-10-25 03:23 PDT — actual wavefront smoke
CODEX took over wavefront-aware xt1 both-cluster smoke on codex/qc-wavefront-smoke-run-1025 (basebc11ef2db). Read-only r3 bind epyc3:/srv/opentallas-scratch2/claude/codex-qc-bind-1025/wavefront_r3; own workdir epyc3:/srv/opentallas-scratch2/claude/codex-qc-wavefront-run-1025/both. Sourceclosure branch transferred via36MB bundle into own epyc3 centralref, no main checkout changed. Prep viaot-run24GB/4threads, inputs copied from epyc1method fixture, constantslead24/gap4, no-report (paused bind untouched). Preserves live internal reset and5 omitted-boundary prefixes; explicitcalendarstart130 afterlatestcorepin129. Next build90GB/32threads then strict numeric+schedule nominal/hrskew1.

## CODEX handoff 2026-10-25 03:35 PDT
Actualwavefront r3 both smoke epyc3codex-qc-wavefront-run-1025/both unit2594369 frontendstillrunning; prep108filesPASS, no%Error/noverdict; frozen srcbc11ef2db, calendarstart130. Pausedbind untouched; seeCODEX-LOG handoff.

## CODEX notes — Handoff to Claude 2026-10-25 03:35 PDT
Parked on CLAUDE RESET. Complete branch/results/job inventory in CODEX-LOG Handoff QC token / bound S8 sublane. Combined branch codex/qwen-token-integrate-1025@57e2d3bb6; methreceipt801fdc3fd; wavefrontsmoke bc11ef2db. Running: intel2 codex-qc-crom-row-1025 build, intel2 codex-qc-mat-all-1025 (112cases), epyc3 codex-qc-wavefront-run-1025/both; SFU child records own job. Future CROM calibration watcher STOPPED, scripts safely staged. No new owner question.

2026-10-25 05:02 PDT CLOCK-RESET -> QC-TOK: decision 13c START broadcast is READY (claude/clock-reset-1025@e84452a8fd, opt-in plan key reset.start="broadcast"; see COORD-REVIEW-QUEUE). Your next per-die batch: set reset.start=broadcast, re-kit soft types once (+start_i, +start_o_<k> beside rst_o_<k>), re-bind (raw bind emits the die 'start' pin + start wiring automatically; QC proof: epyc3:/srv/opentallas-scratch2/claude/clock-reset/start/qc_bind, errors 0). Benches: drive die 'start' (tie high = old wavefront); control state releases at S + published release offset. Re-run xt1/tp8 on this bind with start at a known cycle.

## CODEX notes — 2026-10-25 05:59 PDT handback
Collected inherited actual wavefront xt1 PASS near64/64+far64/64, static-edge mutant caught (schedule_gate.json PASS), epyc3 codex-qc-wavefront-run-1025/both. Decision13c explicit START successor NOT RUN. Stopped on reset; detailed handoff CODEX-LOG. No new source/merge/live jobs.
2026-10-25 06:15 PDT QC-TOK3: started (13c START on current QC plan). Found predecessor's LIVE run epyc3:/srv/opentallas-scratch2/claude/qc-tok-start-1025/both (ot-run bash pid 4107892, tool = e0e0da544 bind_smoke, bind = clock-reset proof qc_bind = main QC plan + reset.start=broadcast, verify PASS): nominal START_AT=200 cal 330 near 64/64 + far 64/64 PASS, hr+1 mutant run done; 3 START negatives (cal@S, cal@S+129, start never) running. Collecting, not relaunching. Branch claude/qc-tok-start2-1025 = qc-tok-1025 + qc-tok-start-1025 + main 6a6fc12dd (+5 START carve unit tests).
2026-10-25 06:36 PDT QC-TOK3: COLLECTED decision-13c START xt1 both on main's QC plan + reset.start=broadcast (proof bind epyc3 clock-reset/start/qc_bind, verify PASS): nominal START_AT 200 / cal 330 near 64/64 + far 64/64 PASS; hr+1 mutant numerically PASS but schedule gate catches it (PASS); NEG cal@S 0/64+0/64 FAIL, NEG start-never 0/64+0/64 FAIL; cal 1 clock early still PASSES with unchanged edges (contract 130 is conservative, same as xt1_wf_early). Edges relative to the calendar are identical to the r3 wavefront run: 0 cyc/token, boot S+130. Receipt + 5 START carve unit tests: claude/qc-tok-start2-1025@1a6dbd1f6 (READY posted). Asked QC-A0 to fold reset.start=broadcast into the QC plan batch.

## PARKED 2026-10-25 06:36 PDT (QC-TOK3)
- Branch claude/qc-tok-start2-1025@1a6dbd1f6 (pushed; local worktree /home/ubuntu/wt/qc-tok-start2-1025, sparse). READY in COORD-REVIEW-QUEUE.
- Live jobs: none (QC-TOK2's epyc3 run qc-tok-start-1025/both finished 06:34; ot-run bash pid 4107892 exited). Run dir kept for
  ROOT-MERGE checks (obj_089b730b0c7dba35 is 7 GB; delete it after the merge).
- Results: results/token_pass/qc_1025/xt1_start_broadcast (README table). Build 45.9 min / 79.5 GB peak.
- Next: (1) the QC plan owner (QC-A0 / qc-plan3) commits reset.start=broadcast in the next per-die batch and re-kits the soft
  types once (+start_i/+start_o_<k>); (2) rebind on that committed plan and rerun this smoke (prep.sh in the receipt: change
  --bound, about 50 min on epyc3, 90 GB) to make it plan-of-record; (3) d2d03fe94 (ot_dp_rgate) is still only on
  claude/clock-reset-1025, and the proof bind used it, so it must reach main with the plan batch.
- OWNER?: none.

## CODEX notes 2026-10-25 07:23 PDT
CODEX took over START plan-of-record prerequisite on codex/qc-token-0719 (own sparse epyc1:/srv/opentallas-scratch2/claude/wt/codex-qc-token-0719). Confirmed receipt1a6dbd1f6 already main47ea95f39, but d2d03fe94 dedicated ot_dp_rgate source absent main c4fb12b3f. Applied exact five-file source fix; sole conflict retained main kit-closure source-picks tracking plus new transport whitelist. Focused tests PASS12/12 via ot-run epyc1 unit oth-ubuntu-1728234-1792938141, log scratch2/claude/codex-qc-token-0719/start-tests.log. No new heavy token build launched, inherited artifacts untouched. Next current QC plan reset.start=broadcast + fresh R8/bind/constants and both-cluster START smoke, coordinated with plan owner.

## CODEX notes 2026-10-25 07:40 PDT — fresh source and fault diagnosis
Own immutable current-source snapshot dbe1a9e85e and fresh elaboration PASS (epyc1 scratch2/claude/codex-qc-token-0719/source + elab_current/asbuilt.json; ot-run2166573). Rebind driver rebind_plan.sh stages probe/R8/CB16/final verify/constants in new dirs, awaiting stable7b; no inherited output writes.
Fresh graph faults (552rows,map errors0) plus complete proof bind carrying1933/planned2207 establish all48 specific hc0/fw stale-template lanes carry0bits. ExactID evidence fault_lane_candidates.json, actual consumer paths fault_consumers.json in own run dir. Parent plan0719 compared exact48 to current unloaded_lanes274: all48 already removed by7b generator. Therefore old m5 hc0/fw failures are stale-plan preflight; no additional topology fix or tie-off needed. Actual hc1->hc0->ctl chain, SU lane l_fault->su_c, and station bank/vld ring->r0->ctl retained. Some other flt-named lanes carry real cr_q/stream data and MUST remain. Next fresh7b bind+preflight verifies generator correction.

## CODEX handback 2026-10-25 08:03 PDT
Parked on explicit RESET. dbe1a9 START rgate +12tests and 50c8dcd3ac component receipts now main394765. Canonical394 source fresh elabPASS; finite rebind job epyc1 unit3819982-1792940294 continues own codex-qc-token-current-0719/plan_canonical_394_start: probe/baseR8 errors0, final generation+verify/constants pending. Earlier dbe pipeline diagnostic only unit3475755 continues verify. No new token build/peer adapter yet. Fullhandback CODEX-LOG includes actual QK data01ffa33479, KV160part service coordination and OPEN shared STARTbootstrap deadlock (CLOCK source NOT implemented). S+130 proof excludes glue/native59, no fullG5 claim. No owner questions.
