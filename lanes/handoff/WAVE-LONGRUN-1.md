# WAVE-LONGRUN-1 handoff (11-15 08:1x PST, lane WAVE-LONGRUN-1)

Task: lanes/FABLE-FLOW-0815.md item 1 (76 openroad > 6 h hold 83 cores; superseded S81 rows; two GRTs of ot_s81sl_leaf__t47 at once).

## Measurement
7 hosts (intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10), probes 07:53 / 07:56 / 08:02 (CPU rate = growth between the last two, 5.4 min).
- 161 oth-* scopes older than 6 h; per-scope table WAVE-LONGRUN-1-scopes.tsv (host, scope, age, cores now, die, event, item, attempt, row status, action, kit dir).
- 96 RUNNING wave rows, 22 older than 6 h (WAVE-LONGRUN-1-running.tsv). Current plan of record = live kit_wave.current_keys of rt/current 3fa87b84b186
  over kit_wave.json 07:46 (s81 b6gsl_rel2, qwen_compute s29q103S4P, qwen_kvsys kvgeom6, s81_head head_rp21z4_1113, hbm pEv11c).
- Row superseded = its block key is not in the die's current plan (the test cancel_superseded uses). 17 of the 22 old RUNNING rows are
  S81 superseded rows; the 4 QC rows of s29q103S3R and the head row are NOT (block unchanged, current plan).
- Scopes: 58 private lane jobs kept; 26 current-plan wave jobs kept; 9 QC/KV scopes with no row on their event dir kept;
  4 QC old-block scopes kept (qwen_compute cancel_superseded=false, COORD); 64 S81 scopes on superseded blocks = 19 stopped + 45 held.

## Stopped 08:06-08:14 (WAVE-LONGRUN-1-stopped.tsv: 19 scopes, ~25 busy cores)
Only `ssh HOST ot-heavy-stop` (dry run first; dry-run unit list == expected list). Rule: superseded block AND no live tracked row of that attempt
(row terminal, or a newer attempt exists), plus the OLDER instance of a kit dir that ran twice (newest kept; --unit because both were on one host).
Not touched: any non-wave path, any current-plan scope.

## Held, COORD ruling asked (WAVE-LONGRUN-1-held.tsv: 45 scopes, ~122 busy cores)
S81 attempts on superseded blocks with a live tracked row and the OWNER hold "PENDING-PLAN 11-15 (r50) ... Running attempts finish".
Recommendation posted: stop them (adoption done, result cannot count).  After COORD YES, per row of the file:
`ssh HOST ot-heavy-stop --dry-run --match KITDIR`, then without --dry-run.  Or deploy the branch and set supersede_pending_plan_holds true.

## Root cause
wave_jobs.FLEET (OT_FLEET_HOSTS default intel2,epyc2,intel1,epyc4): the wave's stop/probe calls never reached epyc7/8/9/10, and epyc4 (terminated)
timed out every call so live_on_fleet() returned None ("fleet probe unreadable (reported only)", 398 REAP-DEAD SILENT lines).

## Structural fix (branch claude/wave-longrun-1-1115, tests tools/autopilot/test_wave_longrun.py)
(a) rekey_adopted + hold_protects_running: at adoption, unchanged live rows are marked event_adopted (KIT-WAVE REKEY), changed rows are cancelled by
    cancel_superseded; option supersede_pending_plan_holds (default OFF, enable on COORD YES) ends the PENDING-PLAN "running attempts finish" clause for rows of an old event.
(b) live_attempt_elsewhere: launch() refuses (LAUNCH-KEEP) while another block key of the same die+item is RUNNING/LAUNCHING/queue-RUNNING.
(c) FLEET from kit_wave.json minus retired_hosts; live_on_fleet / progress_on_fleet tolerate one unreadable host (retry, FleetMap.unreadable);
    hung_judge dead_min (hung_dead_cpu_min, default 30): CPU grew < 5 % of a core in 30 min and no stage log for 30 min = DEAD, cancelled HUNG; a busy unit is never touched.
    reap_stale_attempts retries a stop that could not reach a host (reaped only on a clean stop; window 24 h).
    orphan_sweep (host scan, ot-heavy-stop --unit): scopes of an attempt older than a newer attempt that started after it. Default = log "would stop"; orphan_sweep_live true enables.
Not covered: two instances of the SAME attempt (ap job a1 and a2 both running, the t47 case) - the autopilot resubmit must stop a1 first; listed here for KIT-OPS.
