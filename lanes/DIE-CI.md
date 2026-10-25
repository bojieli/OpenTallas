# DIE-CI lane (claude/die-ci-1024, wt localhost:~/wt/die-ci)

Owner-approved toolchain item 2026-10-24: whole-die prototype CI on every change.

## Current step (12:20 PDT) RESUMED 12:1x, adopted: commit-timer run on main 9f6cbf0662 (intel2
/srv/opentallas-scratch2/claude/die-ci, ot-run 48 G, started 10:03; old tool: no die STA, no OOM ladder). Its G2:
25/30 probes EXIT 0 so far; HBM q_sfuc EXIT 137 at 32 G (as in the nightly); KV hgi_v7 OT_DONE 11:57 (pin access 17.5 min);
KV hub_Eo + HBM q_su1 still running. Left to finish (no duplicate); it commits to claude/die-ci-results itself.
Nightly pinned 9d2065c7a2 collected by Codex (FAIL; see CODEX notes).
- MERGED cd2708b887 (@799f32402): CI now runs on current main WITH die STA and per-job memory:
  * one ot-run job per die, --mem = die_ci.py job-mem <die> (largest G2 docker + 8 G): s81/s81_head/QC/KV 72 G, HBM 136 G
    (was one 340 G job that queued 390 s);
  * G2 part probe EXIT 137 -> re-run alone at 2x up to the die ceiling (default 32->64; HBM 64->128);
  * die STA uses main's die_sta.py, else DIE-STA's branch tip (claude/die-sta-1024) passed as --sta-tool, ref@sha
    recorded in die_ci.json; gate = TT setup / FF hold (owner 08:10), SS info only;
  * per-die parts merged by `die_ci.py collect`; run host keeps only the latest run dir (scratch2 space).
  Verified locally: KV pair e5e6 via DIE-STA tip: policy TT +93.3 / FF +231.0, margined TT -20.1 / FF +170.2 (FAIL),
  KV latency FAIL (plan v3.8v digest has no table). test_die_ci 22/22.
- Next: the hourly commit timer picks main cd2708b887 once the adopted run releases the lock (tools/die_plan changed ->
  full G2 for dies whose plan changed, else CARRIED).

## What it is
- tools/die_plan/die_ci.py run: per die (s81, s81_head, qwen_compute, qwen_kvsys, hbm; hbm_arch B2 auto when on main):
  G0+G0C (one check.py --completeness), xdie (PLAN-TOOL5 in-die + xdie_io.py on rack tables s81 / hbm-ds; qwen-rom and
  hbm-qwen N/A: rack macros not lk_ windows), G2 (g2.py die + 5 worst; CARRIED in commit mode when plan+tools unchanged),
  census, latency (digest-matching <die>_latency.json == Plan.lane_latency), die STA via DIE-STA's die_sta.py (ILM)
  on a sub-top of partitions in tools/die_plan/die_ci_views.json + stand-in budgets for every other seam.
  -> results/die_ci/<date>_<sha12>/{die_ci.json,<die>.json,<die>.md,SUMMARY.md}
- Margins on top of policy (tools/die_plan/die_ci_margins.json, check_margins refuses relaxation):
  crosstalk 49.4 ps setup / 20.8 ps hold per seam (|MCF-1| x R_eff(DFFHQNx1 SS 6.6 / FF 2.8 ps/fF) x 0.7 x 0.178 fF/um x 60 um);
  IR stated 5 % VDD -> late cell x1.058 (alpha-power, a=1.3, Vt=0.25); PDNSim NOT RUN (no die PDN database);
  OCV cell 1.05/0.95, net 1.03/0.97 -> late cell 1.111 total.
- die_ci_cron.sh: picks scratch2 host via ot-run --pick, CI worktree at sha, stage-views, ot-run, rsync back to
  localhost:/srv/opentallas-scratch/claude/die-ci/results, commits JSON/MD to branch claude/die-ci-results, keeps a
  "DIE-CI LATEST:" line in HANDOFF.md.

## Results (dry run on main 4b7b2b3e64, no G2, localhost)
| die | G0 | G0C | xdie | census | latency |
|---|---|---|---|---|---|
| s81 | PASS | FAIL 91 hard_cores | FAIL (xdie_io s81 130: copyb_in lk_EN2 missing, S/B host flag) | PASS | PASS |
| s81_head | PASS | PASS | FAIL (same s81 system) | N/A (census none) | FAIL: no s81_head_latency.json |
| qwen_compute | PASS | FAIL 4 ft_budget | FAIL 4 ft_budget | PASS | PASS |
| qwen_kvsys | PASS | FAIL 22 hard_cores | PASS | PASS | PASS (lat_v38s) |
| hbm | PASS | FAIL 121 (core_faces 110, die_io_plan 10, ft_budget 1) | FAIL: xdie_io hbm-ds 961 missing (rack lk_SE0.. vs die_io NW_io..) | PASS | FAIL: no hbm_d4g_latency.json |
- die STA (with die_sta.py from claude/die-sta-1024, KV views kv3_io_cor_v1|kv3_io_ft_v1): policy worst seam setup@SS
  -101.2 ps (= DIE-STA -100.8 at 833.333; die_ci uses min(plan 833, 833.333)), hold@FF +231.0; margined+xtalk
  setup -271.6 / hold +169.0. Stand-in worst (all unmeasured seams): ft setup -106.5 / hold -24.4 ps = IO slack the
  kits must leave to absorb the margins.

## Coordination
- DIE-STA: die_ci imports tools/die_plan/die_sta.py from the sha under test; until it merges the sta gate is
  NOT RUN (stand-ins still reported). No ILM / STA code duplicated (die_ci only filters the top, injects
  set_timing_derate, post-subtracts crosstalk).
- Views registry tools/die_plan/die_ci_views.json: lanes add {host, path} of routed 6_final.v/.spef per plan type.

## Found
- 07:5x central checkout ~/OpenTallas was on DETACHED HEAD (checkout main -> origin/main after 4b7b2b3e64); 7 merges
  sat unpushed. Fixed (ff) under merge.lock -> origin/main f138403b01. (HANDOFF line)
- intel2: ~/OpenTallas missing (moved to /srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas, no symlink);
  die_ci_cron skips hosts without a repo clone.

## OWNER?
- Margin values (xtalk MCF=2 bound, OCV 5 %, IR 5 % VDD) are documented assumptions; they make every current seam
  negative under margins. Confirm they are the intended pessimism, or name a source for tighter numbers.

## CODEX notes
- CODEX root: old nightly remains active on epyc2 pinned9d2065c7 (older corner tooling), result is diagnostic only. Current commit timer enabled on main TT/FF implementation; no duplicate nightly.

CODEX 10:50 PDT COLLECTED nightly pinned9d2065c7a2, service inactive/exit0 but gate FAIL. 6332s. S81/head/QC G2all6PASS; KV G2 v7/hubEo incomplete(no exit; pinaccess/DPL), HBM q_sfuc/q_su1 EXIT137 memory. No actual newplanfailure inferred. Every failure mapped to current owner: S81 corefaces/rackIO/headlat; Qwen fourFTcapacity + oldKVlatdigest(actualvalues0mismatch) + physicalrecoveries; HBM B2l geometry/cells/actualmemorycaps. OldCI lacked die_sta so allSTA NOTRUN. Fullresult epyc2:/srv/opentallas-scratch2/claude/die-ci/results/die_ci/2026-10-24_9d2065c7a2b9. ExtraOCV/IR/xtalk assumptions remain OWNER? as original lane note. Currentmain TT/FF timer retained; no duplicate stale nightly launched.

## 12:35 PDT
- Adopted run 9f6cbf0662 DONE 12:31: FAIL. G2 s81/s81_head/QC/KV all PASS (KV hgi_v7 + hub_Eo now complete, 0 overflow
  / 0 no-access); HBM G2 FAIL = q_sfuc + q_su1 EXIT 137 at 32 G (old tool, no ladder). G0C: s81 91 hard_cores, QC 4
  ft_budget, KV 0, HBM 121; xdie: s81 rack 130, HBM 972; latency: KV + HBM FAIL; STA NOT RUN (old sha).
- die_sta.py is now ON MAIN (DIE-STA merge e70305aec7): CI uses it directly; --sta-tool only as fallback.
- New-code run started 12:31 on main da5213b0b3 (intel2, 6 per-die jobs incl. hbm_arch_B2 now on main; HBM 136 G,
  others 72 G). Jobs queued by ot-heavy (intel2 admits 34 G now); results -> claude/die-ci-results + HANDOFF LATEST line.

## 12:50 PDT (coordinator 12:4x)
- MERGED bf41c38e32: die STA GATE = agreed policy (TT setup / FF hold, 60/25 ps); margined slack and margined stand-ins
  are INFO columns (SUMMARY: "die STA gate" + "INFO margined"; per die: seam table gate vs INFO). KV pair e5e6 under
  the gate: TT +93.3 / FF +231.0 -> PASS for that pair (margined INFO -20.1 / +170.2). Margin values stay OWNER?.
- intel2: ~/OpenTallas is a symlink (scratch2 clone at 3e05af806b); the runner already fetches hub main every run and
  now fails closed unless the CI worktree HEAD == sha. The 12:31 run on intel2 checked out da5213b0b3 correctly.
- In-flight run da5213b0b3 (started 12:31) uses the pre-bf41c38 gate (margined); the next hourly commit run on bf41c38
  re-gates (G2 CARRIED where the plan is unchanged).

## CODEX notes 2026-10-24 21:10 PDT
- CODEX took over: collect pending CI and fix missing current-plan latency tables on codex/die-ci-refresh-1024. Old pinned da5213b0b3 run still progressing: intel2 HBM q_sfuc GRT iter8/30 (20:50), B2 q_b010 iter16/30 (21:05). Left intact; no duplicate. Four completed dies each G2 PASS 6/6, overflow/access0. Old KV policy seam TT +93.348 / FF +230.957 PASS; recorded FAIL came from obsolete margin gate. Current main already gates policy and excludes retired d4g/B2r2.
- Fixed real current-main latency failures: new base-plan KV lat_v38v tables (2416 lanes,max36 cycles) and HBM B2l lat tables (298,max35). gate_latency PASS both, prior files retained. KV prior lat_v38s differs 43 lane depths, so this is a regenerated table, not a digest relabel. R8/token rebind remains separate. Branch committed/pushed for root integration.
- Remaining CI failures: S81 old run 91 hardcores/rack128 -> S81 lane; QC old R8+4ft -> capacity adoption lane; missing actual seam views except recovered KV IO -> waiting physical signed views to register.

## CODEX PARKED 2026-10-24 21:10 PDT
Claude return order: branch codex/die-ci-refresh-1024 @03032ef99 pushed/merge-ready; no jobs started, adopted old CI remains running; details CODEX-LOG handoff.

## CODEX notes 2026-10-25 02:43 PDT
Operational job collection and 14h stale CI lock handed to INFRA owner /root/infra_fleet. Latest SUMMARY found on intel2 was 9f6cbf066233; no runs touched. Current-plan latency/schema fixes remain with CODEX geom/proto if new failures collected.

## CODEX notes 2026-10-25 02:46 PDT
CODEX took over finished-job harvest and CI lock diagnosis on codex/die-ci-ops1025. Inherited service3819714 lock is LIVE work, not deadlock: intel2 g2part-162124(q_sfuc retired d4g)100% CPU33GB, GRT extra11/30 after12h; g2part-4028004(q_b010 retiredB2r2)100% CPU9GB extra21/30 after13h. No cancellation/relaunch. Four completed die records copied to rtx-pro:coord-scratch/codex-infra/die-ci-da5213b0b3. All four G2 PASS6/6 overflow0/no-access0. Historical SHA da5213b0b3 failures: S81 G0C91 missingcores +xdie128; head xdie128; QC r8=1 +ft_budget4 (52/56); KV latency stale-table + obsolete margined STA gate (actual policy TT+93.348/FF+230.957ps PASS). Those are historical plan/tool failures already owned by current replan/capacity/latency lanes; no current-release regression inferred.
Fix: future die_ci_cron.sh background child immediately copies its own completed JSON/MD records and logs exit, independent of slower peers; final full verdict still waits all jobs. bash-n PASS; branch sent root. Existing live shell unchanged, no duplicate probes.
2026-10-25 03:16 PDT INFRA -> DIE-CI: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: /srv/opentallas-scratch/claude/die-ci (open fds). When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.
