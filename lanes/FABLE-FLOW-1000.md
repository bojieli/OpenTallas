# FABLE-FLOW-1000: procedural / flow review, window 11-20 07:40 to 09:48 PST

Lane FABLE-FLOW-1000 (Fable 5.2). Read-only review, flow only. Replaces the 11-19 file of the same name (in git history).
Sources: autopilot/log.txt, lanes/FLOW-HEALTH.tsv (last written 09:09), tools/failure_breakdown.py 09:43, ot-run --status
09:46, kit_wave_state.json 09:48, kit_wave.json, docker ps / df / timers on the 7 hosts 09:46, lane posts.

## Headline

1. The reset identity class is falling, and the evidence is good but short. Gen refusals per hour: 27 (03), 83, 154, 166,
   149, 117 (08), 66 (09:00 to 09:37), 0 after 09:37. Of 319 attempts launched after 09:20 (when die_gen_env got
   OT_RESET_HOP_CAP_UM / OT_CBC_REACH_UM = 405 on S81 and KV, and QC's old tree kept 405 as its own bound env), about 140
   are past gen (S81 83, KV 33, QC 25) and none carries the class in wave state. 4 post-09:20 launches still failed with
   it (kv3_hg_v1, kv3_hg_v1p6, kv3_pv_v7, QC sle_st_a_v2 on v0e), all launched 09:20:54 to 09:21:26, inside the tick that
   changed the env. Not yet proven: only one result tick has run since the big 09:2x and 09:43 launch waves (364 launches
   in hour 09), and 183 rows are still ENQUEUED. The 10:00 and 10:10 ticks decide it.
2. The fix in force is an env override per die, not a structural fix. FLOW-NOADV-0915 has posted nothing (no
   lanes/posts file at 09:48), so nobody has stated what was changed or what it covers.
3. A hole remains: the older fallback trees carry no reset keys in their own gen_env (S81 d8h, d8g; KV hg11, hg10, hg9;
   QC n46_s2, n46_s2_p2026..., n46_s1). kit_wave.py 9846 sets every die key that the tree's env lacks to None, so a
   fallback launch on those trees runs the tool default 300 against a 405 bind and reproduces the class. Read from code,
   not seen firing.
4. Retries were not stopped by the cause: 118 types failed the same refusal 246 times in 2 h; 290 of 543 launches were
   attempt 5 or higher, 161 attempt 10 or higher, 22 attempt 20 or higher, maximum 42.

## Classes

Fleet at 09:46: 6 of 7 hosts admit 0 GB (only epyc7 admits 124 GB), 167 waiters, 513 running jobs, 369 wave rows RUNNING.

| # | class | count, trend | process root cause | structural fix | owner | fleet time |
|---|---|---|---|---|---|---|
| 1 | Bound reset identity refused at gen | 246 FAIL lines in the window over 118 types (S81 130, QC 90, KV 26); 149/h, 117/h, 66/h, 0 since 09:37 | main aced0fb210 changed a generator DEFAULT (reset hop cap 405 to 300). The bind records the reset tree it was built with, but gen takes the cap from the tool default or env, so every live 405 bind stopped matching | bind writes the cap and reach it was built with into the bound plan; gen reads them from there and ignores default and env for a bound tree. Then a default change can only affect new binds. Plus a merge test: gen one bound type per die against the live bound trees, fail on any identity difference | FLOW-NOADV-0915 | about 3 percent of compute (246 gens of about 7 min), but FAIL lines were 73 to 91 percent of LAUNCH lines per hour from 05:00 to 09:00 and 118 types made no progress for about 6 h |
| 2 | Fallback trees without the reset keys | 8 trees on 3 dies; 0 failures seen yet | per-tree gen_env was captured before the keys existed; missing keys are forced to None | same fix as 1 (value lives in the bind). Until then, write 405 into those 8 tree entries | FLOW-NOADV-0915 | 0 now; re-opens class 1 on any fallback |
| 3 | Retry on an unfixed cause | REPEAT lines 85 to 135 per hour (89 in hour 09); 33 types failed 2x, 32 types 3x to 5x in 2 h; 628 ledger entries | the repeat stop keys on a fingerprint and a full input hash. The class text changed at 06:00 (UNCLASSIFIED to PLAN), which reset the count, and the hash still contains the rt sha (30 trees a night), so "same input" never repeats. Open since FABLE-FLOW-0245 class 2 | key = digest of the files the failing stage read plus the bound plan identity, without rt sha and without the class label. One die-level record per refusal text: after the first 3 types fail with it, siblings with the same bind are not launched until that digest changes (this is the existing r705 skip working, not a new hold) | FLOW-NOADV-0915 | the same 3 percent as class 1; not additional |
| 4 | Cancel does not reach the container | the 5 named containers (coll_core-992477 epyc10, kv3_hg_v1p6-1282096 and kv3_pv_v8-2521551 epyc7, k13i / k13ci intel2) are gone at 09:48; I did not find which action removed them. 3 of today's 31 qualified cancels had no ot-run client at all | the container is a child of dockerd, not of the cancelled unit; the container stop of 184180e55f4 lives in the kit's pinned run_kit, so older kits lack it; lane-started ot-heavy jobs have no hub client to cancel | ot-heavy labels the container with its unit at docker run; ot-run --cancel stops by label on the host and re-checks it is gone; ot-run --status lists containers with no client | FLEET-OPS-R2 | under 1 percent today; each miss holds 48 to 128 GB of admission |
| 5 | Unsignable long jobs found by hand | 28 cancelled at 09:26 after 12 to 28 h each; 87 containers older than 12 h remain (intel1 22, intel2 17, epyc9 16, epyc10 15, epyc2 10, epyc7 4, epyc8 3); only the 40 in GRT were read | the owner rule (over 3 h and post-CTS TT under -300 ps) is applied by a one-off lane, not by the watchdog | noprog watchdog applies the rule itself each pass from 4_1_cts.json and writes the evidence row; no lane needed | FLEET-OPS-R2 | about 6 percent of running slots for 12 h or more before the cancel |
| 6 | Admission 0 GB with waiters | 6 of 7 hosts, 167 waiters; avail memory 118 to 345 GB per host; load per core epyc9 4.3, epyc7 3.9, epyc10 3.1, epyc8 2.3 | reservations far above use: 3 private coll_core GRT proofs on epyc9 (10 to 15 h) reserve 128 GB each and use 6, 21 and 21 GB, while epyc9 admits 0 with 23 waiters asking 208 GB. Host pick still ignores load (0245 class 10, open) | stage-peak admission (owner OK 11-19) for private kits too: reserve the measured stage peak, not the requested 128 GB. Host pick weights load. Rails unchanged | FLEET-OPS-R2 | epyc9 alone: 384 GB reserved for 48 GB used, about 20 waiter slots |
| 7 | New plan tree incomplete on hosts at launch | 09:38 SRC-INCOMPLETE: QC A4 postbind tree lacks bind_cells.sv and type RTL on epyc9 and intel1; 100 A4 launches at 09:43. Cross-host tree compare was clean at 09:07, before A4 | apply marks the plan live before every gen host holds the whole tree | apply completes only on a per-host receipt; a host without it is not a gen host for that event | new lane SNAP-RO successor (or QC-PLAN-R4 until one exists) | not measured; watch the 10:00 tick for src_manifest fails |
| 8 | Stale or superseded-plan launches | 0 found. After A4: 7 SKIP-OLDPLAN, 6 unstarted queue jobs cancelled, 95 SUPERSEDED-KEEP (old plan past synthesis, kept per owner). 3 "plan contract metadata missing" fails on the old v0e tree at 09:37. STALE 104, all HBM (parked), unchanged, 11 unowned | working as intended | none | none | 0 |
| 9 | Disk | intel1 scratch2 341 GB free (91 percent), epyc8 546 GB (93 percent), epyc2 297 GB; no floor refusals in the window | fixed by 69dcd28198, which is in rt/current 1caf584c6546 on all 7 hosts. The store GC last ran 09:21 to 09:26, before it landed, so the hourly snap-gc has not run once yet | confirm the 10:2x run deletes snaps; epyc10 auto-clean ALERT (no completed pass for 111 min) is unanswered | FLEET-OPS-R2 | 0 now |
| 10 | Review inputs stale | FLOW-HEALTH.tsv last written 09:09 (hour 09 shows 9 launches, real 364); wave tick 482 s at 09:43 (bind_preflight 249 s, plan_dies 200 s) against 172 to 239 s before | health file is written by a lane, not by the wave; a plan apply doubles the tick | wave writes the hour row itself at each tick | FLOW-NOADV-0915 | fix latency only |

## Do now (ordered)

1. FLOW-NOADV-0915: post what was changed at 09:20 and its coverage; add 405 to the 8 fallback tree envs; then move the
   cap into the bind.
2. FLOW-NOADV-0915: repeat key without rt sha and class label (open since 02:45).
3. FLEET-OPS-R2: cancel by container label; watchdog applies the unsignable rule; stage-peak reserve for private kits.
4. OPUS-FIX-QC-COLLCORE owner: decide the 3 epyc9 coll_core GRT proofs (pkw2b, pkw3, pkw4). Triage measured the same
   type at TT -576 and -702 ps on other kits; I did not measure these three.
5. Whoever owns QC A4: complete the tree on epyc9 and intel1.

Not checked: the result tick after 09:43; whether --crit reaches ot-run; why the 4 post-09:20 failures still ran at 300;
the containers older than 12 h that are not in GRT.
