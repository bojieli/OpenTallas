# FABLE-FLOW-0200: procedural / flow review, window 11-20 23:45 to 11-21 01:47 PST

Lane FABLE-FLOW-0200 (Opus 5.5; Fable at its limit). Read-only review, process and tooling only. Nothing cancelled, signalled or launched.
Previous: lanes/FABLE-FLOW-2350.md.
Sources: autopilot/log.txt (1,861 lines 23:45-01:47, and 20-11 18:00 onward for trends), lanes/FLOW-HEALTH.tsv (01:08),
tools/failure_breakdown.py (run 01:59), `ot-run --status` (01:5x), df on 7 hosts, rt/current = 5d76c70f71f5 (01:36),
autopilot.py classifier source, LANE-STATUS.tsv, handoffs FLEET-WATCH-R4, FABLE-FIX-S81-SVC.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.

## Headline

1. **NEW, largest waste: a design stop is filed as an OOM kill and resubmitted up to 6 times (V).** A build that stops at
   PLACE-SETUP-STOP (wns below -300 ps, post-place) never writes postcts_gate_tt.json. The classifier reads "gate lost" as
   `infra-oom` (autopilot.py:1262), and `is_earlyoom_kill()` matches the text "post-CTS gate lost" (autopilot.py:3180), so
   the job gets 4 earlyoom resubmits, then 2 infra-oom resubmits at --mem x1.5, then KIT-LOST, and the wave builds a fresh
   attempt from the same src. Window: 85 such classifications, 74 resubmits, 36 items, **28.3 job-hours and 1,936 GB-hours of
   admission** (about 4.7 percent of the fleet's 598 unit-hours). It started at about 21:36 (22-23 h: 107, 00-01 h: 85; 18-21 h:
   6). earlyoom on epyc7 logged no kill since 00:00 while a8f016c67550 (slw_st_a_v2, wns -7,704 ps) was resubmitted 6 times
   there. The 2350 review saw this as "OOM kill x1.5: 10 QC items" and did not find the cause.
2. **All eight 2350 fixes are on main and in rt/current (V).** Watchdog installed SAME on all 7 hosts.
3. **Sign-off count flat: 492 any plan, 407 current plan, same as 23:05 (V, failure_breakdown 01:59).**
4. **19 S81 units silent 7.5 to 11 h, CPU busy (V):** svc_hi/svc_lo (12) and kv_leaf; FABLE-FIX-S81-SVC says these unsplit
   svc shells place at 555-819k cells (R) and need the att/rs split, which no lane owns now (row "COORD to assign").

## The 2350 fixes

| Fix | State (V) |
|---|---|
| xdist push gate d5ddb29bbaa | On main 00:12, in rt. |
| GRT 10 iterations / round wall / repair_timing stop 851bfded63 | On main 00:11, in rt. Applies to new kits only; no stop line seen in the window. |
| retry `fix=` key efd3b7f374 | On main 00:24, in rt. But at 00:30 slw_hc3__clccfc3e6b still launched on a key with REPEAT "same fail key x2": the wave ran an older rt until a later switch (rt moved 6 times 00:44-01:36). |
| watchdog install 639df6b7b2 | Done: FLOW-HEALTH 01:08 shows noprog_watchdog/noprog_stage SAME on all 7 hosts. |
| REPIN 5d87c872e3 | In rt from 00:46. 0 KW_REPIN lines in the window (FLEET-WATCH-R4 confirms). |
| visual unhold (coord b1a38f6fc0f) | Done 00:00; ROUTE-HOLD lines fell 113 (day) to 4 in window; 7 S81 rows owner-held (R). |
| latch restore e88352084d | On main 00:15, in rt. |
| istations fbc23d5034 | On main, in rt from 01:22. |
| R8 auto re-derive (QC-PLAN-R8, 5d76c70f71) | Pushed 02:00 (R), in rt/current. Fixes the R8_STALE class going forward. |

## Classes

Fleet base: 299 running units (ot-run --status), so 598 unit-hours in the window.

### (a) Design stop classified as infra-oom, resubmitted (NEW)

- Count and trend (V): above. 42 of the 85 lines carry PLACE-SETUP-STOP text; 88 of 91 infra-oom lines in the window are "gate
  lost". RESUME-MOVE copies for these fail ("No such file", 12 times) and the job resubmits on the same host anyway.
- Root cause: WF-1 11-14 made "gate never wrote a verdict" mean "host killed the gate". PLACE-SETUP-STOP (postplace_setup_stop.py,
  added later) ends the run by design before the gate, which looks identical. Two resubmit budgets (earlyoom 4, infra-oom 2)
  are chained, and neither asks the host journal (`earlyoom_kill_near` exists and is not required).
- Structural fix (P): (1) in `classify`, any `*-STOP` marker (PLACE-SETUP-STOP, STRUCT-STOP) in FAIL_POSTCTS/FAIL_POSTPLACE
  returns STRUCTURAL `place-setup-stop` before the gate-lost branch; (2) `is_earlyoom_kill` drops the "post-CTS gate lost"
  pattern and an oom resubmit requires `earlyoom_kill_near()` true or a kernel/guard kill record; (3) one shared infra budget per
  attempt, not two; (4) a STRUCTURAL setup stop counts toward BLOCKED-CAP like other design fails. Test: replay the 36 items.
- Owner: FLEET-WATCH-R4 (live 02:00). Fleet time: 4.7 percent of unit-hours, 1,936 GB-h reserved on hosts that admit 32-85 GB.

### (b) Oversized and unsplit types running long

- Count (V): 19 S81 units silent 456-661 min on the kit log with growing CPU (HUNG-WATCH "not cancelled (WF-1)", REAP-DEAD SILENT
  "progressing"); 12 svc_hi/svc_lo, kv_leaf t1/t2. CELL-BIG: 105 distinct items over 400k enqueued "anyway (stops_off)" in hour
  00 (22-23 h: 4), QC 56, KV 26, S81 24, 400-517k cells (largest closed type is 517k).
- Root cause: the 400k limit is advisory; nothing turns "over the cap and silent 6 h" into a decision, and the svc split has no
  owner since FABLE-FIX-S81-SVC stood down (01:3x).
- Structural fix (P): the wave launches one representative per family when the item is over 400k and holds siblings as
  SIBLING-BIG until the representative passes GRT; HUNG-WATCH silent over 8 h on an over-cap type posts NEEDS-OWNER with the
  stage and cell count once (not each tick). Assign the svc split (J7) to a lane now.
- Owner: COORD (svc split assignment), FLEET-WATCH-R4 (wave rule). Fleet time: 38 unit-hours (6.4 percent) in the 19 units (I:
  whether they can sign is not measured; none meets the cancel rule).

### (c) Infra cancels that do not come back

- Count (V): 12 geom_run waiters (waiting for admission 4-5 h, no container) stopped from outside at 01:03 by `ot-run --cancel`
  (rt 8a16e814 and 5d87c872 copies); 10 got INFRA-FREE-RETRY, 4 KILL-PIN; col_h9_r0_p3 a3 and c1x_C t4 a1 were refused by
  RETRY-INFRA-STOP because an older HELD class on the item still applies. FLEET-WATCH-R4 waiter w4 watches them (R).
- Root cause: the free INFRA retry is checked against the item's last design hold instead of the cancelled attempt's own result.
- Structural fix (P): an attempt cancelled with no design result inherits nothing; RETRY-INFRA-STOP applies only when the
  cancelled attempt itself recorded a design class.
- Owner: FLEET-WATCH-R4. Fleet time: none in compute; queue position lost (4-5 h each).

### (d) Thread oversubscription and admission

- Measured (V, 01:5x): threads granted vs cores epyc7 566/96, epyc8 406/96, epyc9 414/96, epyc10 366/96, epyc2 306/128, intel1 240/112,
  intel2 216/112; load 82-171. Admits 32-85 GB per host. No admission or disk refusal line in the window.
- Root cause: a GRT congestion loop is one thread but booked as 8; detail route uses 6-7. The budget counts nominal threads.
- Structural fix (P, repeated from 2350): book a 5_1_grt stage as 2 threads in the wave budget once the stage starts.
- Owner: FLEET-WATCH-R4. Fleet time: not wasted, but it hides spare cores.

### (e) Disk

- Measured (V): intel1 scratch2 233 GB free (94 percent; 162 GB at 01:40 per FLEET-WATCH-R4, so something was freed), epyc8 486 (94),
  epyc9 427 (94), epyc10 728 (91), epyc7 959 (88), epyc2 root/scratch3 421 (88). 13 DELETE deferrals, all on epyc9: "a running
  container mounts the kit".
- Root cause (I): on epyc9 one running container mounts a parent of many kits, so every reclaim there is refused.
- Structural fix (P): reclaim checks the mount source of each container against the exact kit path; log which container blocks.
- Owner: FLEET-WATCH-R4. Fleet time: none yet; epyc9 is the next host to reach the floor after intel1.

### (f) STALE and source skew

- STALE (V): 111 current-event (2350: 112): HBM 104 (parked, no parked flag, sixth review), QC 6 `__pv` types with no wave row and
  no owner (unchanged since 2350), KV 1 (qkd_pv_fin_s8_pin cancelled 16.5 h), S81 1 (iqf__t1 ROUTE-HELD 8.6 h, FAIL-S81-1).
- Plan holds (V): S81 217 type rows "held by die owner (plan event pending)", QC 10, KV 15.
- Skew (V): TOOLS-LAG s81 still unmeasured (`j5tree` not a sha, seventh review); KV 516 commits behind and missing r708 (nominal
  clock cap); TOOL-SKEW KV UNMEASURED (pin manifest rt/a2fb7e625dd8 missing on the hub); S81 489 of 18,020 modules differ from pin.
  HUB-SYNC-FAILED at 01:02 (lanes/NOPROG-ACTIONS.tsv local edit in the hub checkout).
- Structural fix (P): the die config stores the pin as a full sha (bind refuses a name); KV re-pins to a tree with r708 at its next
  bind; the 6 QC `__pv` types get rows or are retired by QC-PLAN-R8; NOPROG writer commits via coord-commit.sh.
- Owner: S81-J6-ASSEMBLY-R2 (s81 pin), KV-PLAN-R4 (KV pin), QC-PLAN-R8 (QC rows), FLEET-WATCH-R4 (NOPROG writer).

### Known items, state now

- 2 INFRA rows not relaunched: class (c). No KW_REPIN: 0 in window. intel1 scratch: (e). R8_STALE: fixed by r8_refresh 02:00 (R).
- kit_wave run-item refusing hardlinked private trees, ot-run refusing `--priority plan`, J6 C3g/C3i svc prov_1119 config.mk,
  lane waiters not harness-tracked: no log evidence in the window (they act outside the wave); not re-measured.

## Do now (ordered)

1. FLEET-WATCH-R4: class (a) classifier fix (STOP before gate-lost; earlyoom needs a journal hit; one budget). Largest saving.
2. COORD: assign the S81 svc split (J7) owner; the 19 silent units are the evidence for it.
3. FLEET-WATCH-R4: RETRY-INFRA-STOP looks at the cancelled attempt only; relaunch the 2 rows by that rule.
4. FLEET-WATCH-R4: over-400k representative-first; GRT booked as 2 threads.
5. S81-J6-ASSEMBLY-R2 / KV-PLAN-R4: real pin shas, KV r708.

Not checked: the stage of the 19 silent S81 units; who ran the 01:03 cancels; the epyc9 container that blocks deletes; whether the
CELL-BIG hour-00 burst is one rebind wave.
