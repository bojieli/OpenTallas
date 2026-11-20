# FABLE-FLOW-1400: procedural / flow review, window 11-20 12:00 to 13:55 PST

Lane FABLE-FLOW-1400 (Fable 5.2). Read-only review, flow only. Previous: lanes/FABLE-FLOW-1200.md.
Sources: autopilot/log.txt, ot-run --status (13:43, 13:53), earlyoom / kernel / user journals on the 6 build hosts,
~/.local/state/noprog/report.json on 7 hosts, kit_wave.json + kit_wave_state.json, lanes/NOPROG-ACTIONS.tsv,
lanes/VISUAL-QUEUE.tsv, lanes/GEOM-REVIEW.md, ~/.local/state/ot-postbind, rt/<sha> trees, lane posts.

## Headline

1. The unsignable watchdog is NOT ready to enable. Its list is clean on the hosts it sees, but it sees only 3 of 6
   build hosts: on epyc8, epyc9 and epyc10 every pass logs "0 containers" (48 to 62 run there), for the whole 30 h of
   journal kept. The no-progress watchdog is blind on the same hosts. 167 of 369 running jobs are unwatched.
2. OOM kills did not stop. They fell about 60 percent and moved: epyc10 has none since 11:28, epyc8 (none before
   12:09) now loses one 31 to 39 GB openroad every 10 to 30 min, epyc9 still kills. Admissions did not collapse.
3. All 145 S81 J5 launches (13:19 to 13:28) are pinned to tools without e7ebced0c4e (rt 887cb2d06ac1 and
   eae58257326f). 4 J5 kits are generated, none carries OT_PLACE_MAX_TRANSITION. The rest still wait for memory, so
   a re-pin now loses no work.
4. The J5 post-apply bind has no result: elaboration exited rc 2 with an empty log, so bind and LATCHECK never ran.
   It was posted as FAIL at 13:18 and nobody has acted on it.
5. HUNG-WATCH cancels rows that wait for memory: 16 cancels since 11:45, all with no container and 106 to 206 CPU
   seconds. It acts after 31 to 48 min although hung_watch_min is 120.
6. epyc7 is the only host that admits (281 to 348 GB free to admit) and S81 cannot use it: it holds no S81 tree and
   is not in the S81 gen_hosts.

## (a) OOM kills and admissions after STAGE_PEAK_FRAC 0.5 (12:10)

Kills, counted as earlyoom SIGTERM victims that are build processes (host journals):

| host | 11:00 to 12:10 | 12:10 to 13:45 | note |
|---|---|---|---|
| epyc10 | 16 | 0 | last 11:28. Two kernel kills at 13:31 are a 4 GB container cap (CORE-LIB-LIMITS trial), not the host |
| epyc9 | 15 | 12 | 12:47 (2), 13:06 to 13:27 (10): four 22 to 23 GB ORFS jobs, eight sub-step tools (tt_setup_repair, postcts_gate, pregrt_ff_hold, grt_policy_tt) |
| epyc8 | 1 (12:09) | 5 | 12:53, 12:57, 13:00, 13:28, 13:35: each one openroad of 31 to 39 GB with oom_score_adj 0 |
| epyc2, intel1, epyc7 | 0 | 0 | no earlyoom kill all day |

Rate: about 27 per hour before, about 11 per hour after. The hub recorded only 4 of the 17 as infra-oom.

- epyc8 is not an admission problem: it admitted 1, 2 and 4 heavy jobs in hours 11, 12 and 13. Its 49 running jobs were
  admitted before the change (53 heavy admits in hour 10) and are growing; available memory is 44 to 65 GB. FRAC cannot
  fix that. ot-run shows "peak 0" for epyc8, so no stage-peak growth is charged there at all.
- Victim order is wrong on epyc8 and epyc9: earlyoom first kills 3 to 8 small wrappers at oom_score 800 (ot-heavy
  waiters, sleep, tee, an ssh running post.sh, a git fetch), which frees nothing and drops queue clients and posts. Then
  on epyc8 it kills the largest job with oom_score_adj 0, so age scoring (ot-oom-age) is not marking builds there.
- The FLEET-WATCH-1015 12:08 statement "no kernel/earlyoom kills at 11:00-11:55" is wrong for epyc9 and epyc10.
- "Error 241" (SIGTERM) is classed as an earlyoom kill whatever sent the signal. Since 12:00 this label was put on 2
  no-progress cancels (slw_fw_v1 x2 on epyc2, 12:35 and 12:55: resubmitted with place memory x1.5) and on the HUNG-WATCH
  cancel of slw_fe_v2__cle312294d (13:33, classed 13:40, epyc10 had no earlyoom kill since 11:28).

Admissions (heavy scopes started per hour, 6 hosts): 282 (09), 209 (10), 127 (11), 47 (12), 68 in the first 45 min of
hour 13. Five of six build hosts admit 0 GB at 13:43 and 13:53; epyc7 admits 281 to 348 GB. Waiters 178 (11:47), 245
(13:43), 220 (13:53); running 351 to 369. The rise in waiters is the 150 J5 launches at 13:19 to 13:28. So: a drop in
hour 12, no collapse, and the fleet stays full. intel1 (avail 260) and epyc2 (avail 210) admit 0 because the charged
growth is now 144 to 184 GB and 373 to 403 GB: that is the 0.5 setting working as intended.

Owner condition (kills about 0, admits continue): met on epyc10, epyc2, intel1; not met on epyc8 and epyc9.

## (b) Unsignable watchdog report list

- Hosts it sees (epyc2, intel1, epyc7): 0 jobs over 3 h with latest setup under -300 ps. 9 rows carry a setup number,
  worst -133 ps (col_h9_r0_p3__t1, tt_setup_repair_grt). The stage column now names the latest stage, so 6a81626d91 is
  live. cbx_q10, listed at -776 ps post-CTS at 12:00, now reads -18.6 ps at postcts_gate_TT: the old read would have
  cancelled a job inside the gate.
- intel2: 2 private KV jobs (opus-kv-hg h1, h2: kv3_hg_v1p6) at -539 and -547 ps, 10.9 h, stage pregrt_ff_hold. They
  are in a hold pass, so by 6a81626d91 they must read as unmeasured; they still carry a setup number. Check before act
  mode.
- 71 of the 91 rows over 3 h have no setup number. Act mode would be safe but nearly inert.
- The 13:15 post still says "post-CTS setup" (wording only) and listed col_h9_r0_p1__t1 at -356 ps; that row is gone.
- epyc8, epyc9, epyc10: report.json has 0 rows; journal says "noprog scan: 0 containers" on every pass. All 7 hosts run
  the same watchdog file (md5 e428761b) and the user is in the docker group, so the cause is in the unit environment,
  not the code. Not diagnosed further.

Verdict: not ready to enable. Conditions: the three blind hosts list their containers; the two intel2 rows read as
unmeasured or are put in NOPROG-KEEP; a cancel writes a marker the classifier reads (still open from 12:00, see class 2).

## (c) Launch-defers and receipt misses

None left. Last HOST-RECEIPT-MISS 12:11, last LAUNCH-DEFER 12:12:50; totals for 11:09 to 12:13 were 15 misses and 61
defers. S81 launched 53 rows at 12:00 to 12:30 and 145 on J5 after 13:19.

What replaced it: GEN-HOST-TREE, 136 lines in hours 12 and 13 (123 at 13:2x), "epyc7 lacks tree ...d8j5_1117_work;
launching on epyc2 instead". epyc7 has neither the D8i nor the J5 tree and S81 gen_hosts (derive_gen_hosts 10:07) are
epyc8, epyc2, epyc9, epyc10, intel1. 117 of the J5 rows went to epyc2, which has 100 waiters.
Also: RESUME-MOVE failed 15 of 16 times today (13 rc 11 "No such file", 2 rc 23 "Permission denied"). The rc 11 cases
copy from the host the hub believes (epyc8) while the run dir is on another host (epyc10), so a killed job is
resubmitted on the host that killed it (slice_station__t43 and __t37 back to epyc8 at --mem 126).

## (d) After the J5 apply (13:13 config commit, rows switched 13:19)

- Superseded-plan launches on D8i: none. All 145 S81 LAUNCH lines after 13:14 are event 224567138ab on the J5 tree.
  Old-event rows kept by the owner rule: 94 RUNNING on 465cb9fe2d3 (D8i), ENQUEUED 20 (D8i), 51 (b05c98f7919), 19
  (3fa87b84b18). 26 RESTAGE lines after 13:19 are host moves of old-event waiters, not new launches. D8i jobs still
  start on hosts as their waiters are admitted (epyc10 13:40, 13:42), which is the rule.
- The 76 holds are 74 leaf types ("representatives first", wait for ot_s81sl_leaf__t7 GRT iteration 10) and the two
  families col_h9_r1__* and col_h9_r2__* (wait for the two J6 masters to route).
- Leak: none. HOLD-AUDIT 13:36 reads HELD-BUT-LAUNCHED=0. The 13 held items with launch lines since 11:00 were all
  launched at 12:21 to 12:56, before the holds (13:04 and 13:13).
- Over-hold: yes, by construction. No held key has a current-event row. The leaf term depends on one job: t7 on J5 was
  launched at 13:28 and at 13:53 was still a waiter at kit_rtl (4 CPU seconds, epyc9 admits 0), with no priority. It is
  pinned to rt eae58257326f, so it will be placed without the slew limit that moved t60 from -964 to -288 ps: the
  representative read will answer the wrong question. Neither hold has a term the autopilot can evaluate
  (HOLD-AUTO-RELEASE 0 keys), so the lift needs a live lane.
- Post-apply bind (postbind-s81-1120131333, epyc8, 13:13 to 13:18): ELAB_RC=2 with no output line, then "no
  asbuilt.json" and "no *_bound_top.sv". This is an elaboration that did not run, not a bind or LATCHECK failure. No
  rerun exists. J5 has 131 running rows and no bind or LATCHECK result. bind + LATCHECK is one of the blocking gates.

## (e) How already-generated kits pick up e7ebced0c4e

Facts: the limit is an "export OT_PLACE_MAX_TRANSITION" line in the kit config.mk plus the PRE_RESIZE hook, both written
at gen. Tools are pinned at launch (rt_tools_launch/<tree>@<sha>). rt/current has the fix since 13:47. It is a code
default, not an env key, so the autopilot change detection (FLOW-REGEN, RELAUNCH-ON-FIX) does not see it.

| kit state | action | cost |
|---|---|---|
| Launched, not generated yet (about 141 J5 rows and other waiters pinned before 13:47) | re-pin to rt/current before gen; make it automatic by putting OT_PLACE_MAX_TRANSITION=320 in die_gen_env of s81, qwen_kvsys, qwen_compute so FLOW-REGEN fires for rows with no place output | none, they have not run |
| Generated, before place repair (3_4) | regen (minutes) | gen only |
| Past place, measured slew-limited (post-place setup under -300 ps with core pin slew over 320 ps: the 12 rows ROUTE-RELEASE-1300 kept held, D8i leaf rows) | new attempt forked from the kit inputs (kit_fork), reusing synthesis; sign-off SDC and bound identity are unchanged | place onward |
| Past CTS and able to sign, or old plan and able to sign | leave | none |

Resume is the wrong tool: the hook acts before place repair and a resumed run keeps the placed DB. A blanket regen is
also wrong: it would restart jobs that can sign. Wait for the two proofs (proof/t60, proof/cbf on epyc10) before the
env key goes in; both are queued behind about 30 waiters and need plan priority.

## (f) WAIT-VISUAL rows with no reviewer

55 rows outside HBM: QC 27, S81 14, KV 11, HEAD 3 (HBM 17, parked). Trend: 16 (11:38), 58 (13:10), 28 (13:29), 36
(13:36), 42 (13:48). The last GEOM VERDICT is 12:54 by ROUTE-RELEASE-1300, which has finished; no lane has written one
in the hour since. lanes/VISUAL-QUEUE.tsv lists 41 rows and none of the 14 S81 rows.
Root cause: the route hold is an event-wide review-before-route added during the Codex cover. The owner rule (11-13) is
that the visual verdict never blocks route. ROUTE-RELEASE-1300 showed the release test is mechanical (placed_scan,
auto_geom, place log, post-place setup).
Fix: the autopilot applies that test itself and writes ISSUES-ACCEPT; rows under -300 ps post-place go to the die owner
instead of waiting. Note the CORE-LIB-LIMITS caveat: post-place setup is not a release or cancel signal when the worst
slew is over about 1 ns.

## (g) Unchanged retries

- Design and plan classes: 6 types failed the same text 3 to 4 times since 12:00 (20 of 47 FAIL lines): kv3_pc_v1 two
  forms (kit_topology packed banks), kv3_hub_C (KIT_NOT_SELF_CONTAINED), QC sle_su_l0, sle_su_l1, slw_su_l0 (plan
  contract metadata missing). Cause: 00eec2a423 (12:50) changed every fail key, so the streaks restarted at x1 and each
  blocked type got three more tries. One-off; they re-block at 3. All fail at gen in minutes.
- Infra classes are the larger unchanged retry: 16 HUNG-WATCH cancels relaunched as "free infra retry" into the same
  queue; 2 no-progress cancels resubmitted as OOM with more memory; earlyoom victims resubmitted on the same host.
- REPEAT-STOP 45 lines in hour 13 are the apply (inputs:block releases), not new stops.

## Classes

| # | class | count, trend | root cause | structural fix | owner | fleet time |
|---|---|---|---|---|---|---|
| 1 | Watchdog blind on 3 hosts | epyc8, epyc9, epyc10: 0 containers on every pass, at least 30 h | unit environment cannot list containers there (not diagnosed) | the tick fails loudly when docker lists 0 and ot-run reports running jobs; fix the unit on the 3 hosts | FLEET-WATCH-1400 (new) | 167 of 369 jobs unwatched; no bound on hung or unsignable time there |
| 2 | Cancel classed as OOM | 3 since 12:00 (2 no-progress, 1 hung-watch); 3 at 11:4x | any SIGTERM exit is "earlyoom"; a cancel leaves no marker | cancel writes a marker in the run dir and the row; classifier maps it to its own terminal class | FLEET-WATCH-1400 | 3 slots, about 80 GB, repeats |
| 3 | Host OOM kills | 17 build processes in 95 min (was 32 in 70 min); epyc8 5, epyc9 12, epyc10 0 | epyc8: growth of jobs admitted before 12:10, no stage peak charged, victims not age-scored. epyc9: sub-step tools started inside running jobs are not charged | epyc8: stop new admits until avail is over the headroom (it already admits 0) and fix age scoring; earlyoom --avoid for wrappers and waiters; charge sub-step tools to their job | FLEET-WATCH-1400 | about 2 to 3 percent (9 jobs of 22 to 39 GB lost a stage); estimate |
| 4 | HUNG-WATCH cancels waiters | 16 since 11:45 (2, 5, 7, 1, 1) | a row waiting for memory has no container and no CPU; the window used is the silent time (31 to 48 min), not hung_watch_min 120 | a row whose ot-run client is waiting for admission is not judged; use hung_watch_min | FLEET-WATCH-1400 | under 1 percent; each row loses its queue place |
| 5 | epyc7 idle for S81 | 136 GEN-HOST-TREE lines; 281 to 348 GB admit unused | no S81 tree on epyc7, not in gen_hosts | sync the J5 tree to epyc7, add it to gen_hosts; RESUME-MOVE takes the source host from ot-run | FLEET-WATCH-1400 | about 5 percent of fleet memory, 11 to 14 jobs |
| 6 | J5 pinned to tools without the slew limit | 145 launches, 4 generated, 0 with the limit | tools pinned at launch; code default invisible to change detection | env key in die_gen_env after the proofs; re-pin rows with no gen output | S81-DIE-R4 with CORE-LIB-LIMITS-1330 | 131 running J5 rows (36 percent of slots) at risk of placing without it; risk, not measured |
| 7 | J5 post-apply bind did not run | 1, open 35 min | elab rc 2, empty log, on a host with 44 GB available | rerun on epyc7; postbind reports UNMEASURED, not FAIL, when elab writes nothing | S81-DIE-R4 | 0 now; all J5 work if the bind fails |
| 8 | Holds without a machine term | 76 keys, 0 leaks | the lift waits for one unprioritised job and a live lane | t7 on rt/current with plan priority; term "t7 5_1_grt iteration 10 present" | S81-DIE-R4 | 74 leaf types idle on J5 |
| 9 | WAIT-VISUAL without a reviewer | 55 rows, rising 28 to 42 since 13:29 | event-wide review-before-route, reviewer lane finished | autopilot applies the mechanical release test | ROUTE-RELEASE-1400 (new), then FLOW-NOADV-R2 | 0 compute; 55 placed kits wait at route |
| 10 | Unchanged retries (design) | 6 types, 20 fails | streaks reset by the key change | none (one-off) | FLOW-NOADV-R2 | under 0.5 percent |
| 11 | Receipt gate | 0 since 12:13 | fixed (6a81626d91) | none | closed | 0 |

Standing: HBM plan-of-record alert 12 per hour (parked); TOOLS-LAG and TOOL-SKEW warnings unchanged.

## Do now (ordered)

1. S81-DIE-R4: rerun the J5 post-apply bind on epyc7. Relaunch t7 on rt/current with plan priority.
2. FLEET-WATCH-1400 (new): make the watchdog see containers on epyc8, epyc9, epyc10; keep report mode until then.
3. FLEET-WATCH-1400: HUNG-WATCH skips admission waiters; cancel marker; J5 tree to epyc7 and gen_hosts.
4. CORE-LIB-LIMITS-1330: proofs with plan priority; then the env key so unstarted rows regenerate.
5. ROUTE-RELEASE-1400 (new): release pass over the 55 rows; then the test moves into the autopilot.

Not checked: why docker lists 0 for the watchdog unit; whether ot-oom-age runs on epyc8 (its unit shows "activating");
that every HUNG-WATCH victim was an admission waiter (inferred from no container and under 210 CPU seconds; one
relaunched unit confirmed waiting); whether an unstarted waiter re-pins its tools at start; the order of e7ebced0c4e
and eae5825732 on main (taken from the rt tree contents); job-hours lost per kill.
