# FABLE-FLOW-0245: procedural / flow review, window 11-19 23:43 to 11-20 01:55 PST

Lane FABLE-FLOW-0245 (Fable 5.2). Read-only review. Sources: autopilot/log.txt, lanes/FLOW-HEALTH.tsv,
tools/failure_breakdown.py, ot-run --status, flow_refresh.jsonl of every wave kit refreshed in the last 100 to
150 min on the 6 build hosts (251 / 285 kits), rt trees, posts of FLOW-FIX-2045, SNAP-RO-1119, FLEET-OPS-R,
WAVE-PILOT-FIX.

## Headline

1. Tonight's five kit-side fixes are in rt/current but in almost no kit. Of 251 kits with a flow refresh in the
   last 100 min, 240 (all of qwen_compute) carry tools fd0e65ccdd36 (23:59, before every fix), 9 s81 kits carry
   older trees, and exactly 2 s81 kits carry a post-fix tree (10deaf355827, 4e2c7f271783); both are still at gen.
   No kit anywhere has repair_bound.tcl or kit_resume.py. Cause: tools are pinned in spec.json at launch, and
   the stage refresh itself runs from that pinned tree (kit_wave.py flow_refresh: `_kfr = {tsrc}/tools/autopilot/
   kit_flow_refresh.py`, `--rt {tsrc}`). A fix to a flow script or to kit_flow_refresh therefore cannot reach a
   kit that is already launched, and only 12 kits were launched after 00:20 because the fleet is full.
2. The repeat stop does not stop anything while rt changes every 6 minutes. A relaunch is skipped only on the
   full input hash, which contains the rt sha (kit_wave.py 11265-11272, owner r704 / r705). 30 rt trees were
   made between 22:55 and 01:47, so the hash never repeats and every failed row relaunches unchanged.
3. intel1 scratch2 is at 114 GB free (97 percent) and falling 43 to 206 GB/h; auto-retire deleted 0 (every
   candidate refused as live input). Floor 50 GB is about one hour away, with 90 jobs running there.

## rt/current per host

At 01:43 all 7 hosts (intel2, intel1, epyc2, epyc7, epyc8, epyc9, epyc10) had 3eefd4b49b72, which contains all
11 listed commits. At 01:53 they had moved to 5d31c0e0b451. Host rt is not the lagging part; the kit pin is.
epyc10 has no ~/.local/bin/ot-run link (the other build hosts link it to rt/current).

## Tonight's fixes, verified live

| fix (main sha) | in rt/current since | exercised | verdict |
|---|---|---|---|
| kit_reports stale-report quarantine (c1c4e14b232) | 00:12 | no | kit_reports.py is in 2 kits of 251 (both fresh gen, nothing to quarantine). 0 stale_reports dirs, 0 KIT_REPORTS lines. Not seen working. The in-place restarts it was written for (private H23 / H25 style kits) do not pass through gen, so they do not get the file. |
| cts_post subtree_balance patch into running kits (116c87ab028) | 00:21 | no | DOES NOT REACH RUNNING KITS. 0 of 251 kits patched; 36 place-stage refreshes in the window all ran pre-fix refresh code from their launch pin. The one kit that has the block (dsdv_slice_c1x_C__t5 attempt 10, epyc2) got it from gen, not from the patch. |
| RSZ-0074 per-chunk catch (49bfd40e422) | 00:32 | no | new tt_setup_repair.tcl is in 1 kit (same one, at gen). No RSZ-0074 in any kit log in the window either, so nothing to judge. |
| post-GRT repair bound + DRT_STALL (42fa5661630) | 01:02 | no | in 0 kits (no repair_bound.tcl, no hook in any config.mk). failfast_rules.py is a kit copy, so DRT_STALL is also pinned. A live case it would have caught: intel1 slw_fw_v2 at 5_2_route, drt_violations 85626 unchanged over the 6 h window (NOPROG 01:45), still running. |
| run_kit auto-resume + cancel stops the container (184180e55f4) | 01:08 | no | kit_resume.py in 0 kits. No cancel of a started job since 01:08 (the one CANCEL-STOP-RESULT, 01:11, had "none running"). Not seen. |
| noprog watchdog plan-sha removal (3a15d56132e) | 01:39 | yes, 1 pass | BEHAVED. Passes 00:00 to 01:30 each had 2 to 5 CANCEL-NOW "kit plan sha is not a live adopted plan"; the 01:30 pass cancelled a QC residual ECO on epyc7 (sle_su_l1), against the owner rule. The 01:45 pass: 0 CANCEL-NOW, 0 SUPERSEDED rows in NOPROG-TABLE. |
| rt materialize lock (7fd6b4331e6) | 00:12 | yes | BEHAVED. 15 sync refusals 01:12 to 01:26 (hub scratch2 under 100 GB) left no lock for the refused tree; its lock appears at 01:27 with the successful sync. Residue: 17 zero-byte .materialize.<sha>.lock files are never removed. |
| snapshot put (a4629bc6026) | 00:56 | yes | BEHAVED, with one loss. qwen_compute_n46_s2_p20261120004922 built, applied 01:25, two launches on it (01:37, 01:46). epyc7 was DROPPED from QC gen hosts ("target exists or not writable") and nobody owns putting it back. |
| incremental verify (ce037831311) | 01:27 | no | the 01:25 apply ran before it landed and took 1807 s of full hashing. Next put is the first test. |
| representatives-first (a64ef7fec3) | 01:27 | yes, 2 ticks | BEHAVED. FAMILIES lines at 01:38 and 01:47; s81 held 14 then 10 siblings behind a failed representative and launched 3 then 8 picks. ot-run --status shows no crit marker, so the high priority itself is not confirmed. |
| auto_retire PROTECTED-DBS (29f59e08773) | 01:39 | no | runner carries --protected-dbs on all 6 hosts, but the hourly timer last ran 01:11 and next runs 02:11. 0 "PROTECTED-DBS" refusals logged so far. |

Score: 4 behaved, 1 does not do what its title says, 6 not exercised.

## Classes

Fleet at 01:45: every host admits 0 GB, 266 waiters, about 525 running jobs.

| # | class | count, trend | root cause in process / tooling | structural fix | owner | fleet time |
|---|---|---|---|---|---|---|
| 1 | Kit tools pinned at launch, stage refresh from the pin | 249 of 251 recent kits pre-fix; new tonight as a measured number | spec.tools_rt is resolved once at launch and flow_refresh runs kit_flow_refresh from that same tree | stage refresh runs rt/current's kit_flow_refresh with --rt rt/current (design tools stay pinned; only flow scripts move); FLOW-HEALTH gets a column "kits per tools sha" so a fix post can state its coverage | FLOW-FIX-2045 | up to 45 percent of running jobs (240 QC kits) run without the five fixes; loss materialises only where RSZ-0074 / unbounded repair / DRT stall hit |
| 2 | Unchanged relaunch after repeated failure | 25 REPEAT lines in 2 h, 1142 in 29 h; qkd_pv_fin_s8_pin attempt 25 to 27 (same PLAN gen error), slice_station__t22 attempt 34, svc_lo_dsdv_svc_rs* MPL-0020 relaunched 3 min after failing, slice_station__t29 / t40 relaunched 8 s and 5 min after STALLED | skip key contains the rt sha, and rt changes every 6 min; REPEAT is log-only under stops_off | key = digest of the files the failing stage actually read (the persisted tools digests of 88537c5e13 already exist) instead of the rt sha. This is not a new stop: it makes the owner's r705 rule ("skip only on the full input hash") true again | WAVE-PILOT-FIX | 3 to 5 percent (each relaunch reruns gen to place before failing the same way) |
| 3 | Operator queue move counted as failure | 14 INFRA[stopped] at 00:05 (13 s81, 1 KV), was 27 OOM-guard kills last window | FLEET-OPS-R moved 27 unstarted waiters off epyc2 by signalling their hub clients with a /tmp script; the wave records FAIL and an attempt | an `ot-run --move JOB --hosts` verb that re-queues without ending the client; until then the wave treats "signal 15 before start" as REQUEUED, no attempt consumed | FLEET-OPS-R | under 1 percent (no compute lost, attempts and queue place lost) |
| 4 | No host qualifies after a hub disk-full window | 7 QC place fails at 01:43:53 after 93 min in queue; 6 earlier on 11-16 / 11-17 | INFERRED: the hub ot-run wrapper sends new run dirs to root scratch3 when hub scratch2 is under 50 GB (it was 41 to 45 GB 01:12 to 01:27); no build host accepts that dir | choose the run dir on the target host at admission, never on the submitting host; hub ot-store GC on a timer like the build hosts (it had never run: 1,685 GB) | FLEET-OPS-R | about 1 percent (7 kits x 1.5 h wait) |
| 5 | rt sync blocked by hub disk | 15 ALERTs in 19 min, recovered 01:31 | same hub store growth; every push was unlandable while it lasted | same GC timer; disk_rate already predicts the floor, let it trigger the store GC | FLEET-OPS-R | 0 compute; 19 min of fix latency |
| 6 | src_manifest false fails | 0 in this window (85 from 20:00 to 23:59); breaker closed 00:09 | fixed (verifier from rt/current, receipt re-check) | done; keep | SNAP-RO-1119 | 0 now |
| 7 | Plan-sha cancels of old-plan jobs | 2 to 5 flagged per pass until 01:30, 0 at 01:45 | fixed by 3a15d56132e | done; the two cancelled residual ECOs were relaunched by QC-HOLD-0030 | NOPROG-FIX-1115 | 0 now |
| 8 | Disk about to hit the floor | intel1 114 GB free; epyc8 and epyc10 93 percent | auto-retire refuses everything on intel1 as live input (rt_tools_launch trees, src trees named by queued jobs); 43 waiters pin them | host pick stops sending new kits to a host under 2 h of disk at its measured fall rate (placement, not a cap) | FLEET-OPS-R | at risk: 90 jobs on intel1 |
| 9 | Unowned / stale | STALE 104, all HBM (parked by owner), unchanged; 11 of them unowned. epyc7 dropped from QC gen hosts, unowned. hbm src_overlay unreadable on epyc10, 13 lines, unowned | no lane picks up a host dropped by an apply | apply posts a NEEDS-LANE per dropped host | COORD | small |
| 10 | CPU oversubscription | load / cores: epyc7 6.0, epyc9 4.2, intel1 2.1, epyc8 2.1, epyc10 1.9, epyc2 1.2 | admission is by memory only and host pick ignores load | host pick weights load (epyc7 at 579 while epyc2 is at 148); no launch limit added | WAVE-PILOT-FIX | not measured; likely the largest single slowdown on epyc7 and epyc9 |

KIT-WAVE FAIL lines 23:43 to 01:55: 26 (14 operator move, 7 no-host, 4 place tool errors, 1 KV gen), down from
107 in the prior window. Launches 115, of which 12 after 00:20.

FLOW-HEALTH.tsv: hourly rows are sound; the file also carries a host table and a SKEW section after row 58, so
it is no longer one table (readers that parse it as TSV get mixed rows). Its hour-01 row shows 0 launches at 01:09.

## Do now (ordered)

1. FLEET-OPS-R: intel1 scratch2, before about 02:50.
2. FLOW-FIX-2045: stage refresh from rt/current, then re-state which running kits each of the five fixes covers.
3. WAVE-PILOT-FIX: replace the rt sha in the skip key by the stage-input digest.
4. SNAP-RO-1119: epyc7 back into QC gen hosts; report the first incremental-verify time.
5. FLEET-OPS-R: hub store GC timer; confirm the 02:11 auto-retire run logs PROTECTED-DBS refusals.

Not checked: whether --crit reaches ot-run for representatives; the 02:00 watchdog pass; kits older than 150 min.
