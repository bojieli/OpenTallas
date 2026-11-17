# FABLE-FLOW-2000: procedural and flow failures, 16:50-20:02 PST

Reviewer: FABLE-FLOW-2000 (Fable). Read-only. Measured 2026-11-16 19:54-20:02 PST on hub intel2.
Sources: autopilot/log.txt 16:50-19:50 (1,403 lines, 34 ticks), lanes/FLOW-HEALTH.tsv (hour rows to 18, skew 19:07),
tools/failure_breakdown.py (19:55), `ot-run --status` (19:58), df and ot-heavy hashes on 6 build hosts (20:00),
kit_wave.json, merge-queue gate records, lanes/posts, CODEX-LOG handoff 19:51. Previous: FABLE-FLOW-1900.
Scope: process and tooling only.

## Headline

1. The largest loss is not a failure, it is a hold. 203 S81 col types (52% of the 394 S81 types) sat 47-62 h behind
   release terms that could not fire. In the same 3 h the fleet ran at 39-45% of 624 threads (idle 343-382).
   The hold released at 19:49 (233 HOLD-AUTO-RELEASE lines) by retyping the terms to the event sha (r414).
   The code fix cca8efdc426 is GREEN 140/140 at 19:55 and waits for COORD approval. Approve it now.
2. Event 1 is misdiagnosed. The 19:16 wave step was skipped because another process held kit_wave.lock, not because
   the hub was dirty. The wave step ran normally (78-137 s) on five other ticks with a dirty kit_wave.json
   (18:10, 18:14, 18:55, 19:13, 19:34). Cost: one tick, about 5 min. The real risk is the reverse: the wave reads
   uncommitted config, so a half-finished lane edit goes live. The hub is dirty again at 20:00 (kit_wave.json M).
3. KV got 0 kits past gen again: 23 fails at 17 h, then 59 LAUNCH-REFUSED at 18 h, 1 new fail at 19:49 (D5).
   Three tree versions (D3, D5, D8) each failed on metadata that one dry gen would have caught.
4. Disk: epyc8 scratch2 fell from 627 GB (17:48) to 362 GB (20:00), about 120 GB per hour, full near 23:00.
   epyc9 71 GB, epyc2 145 GB (was 48), epyc10 478 GB (was 360).
5. Hub memory recovered: 900 GB available (36 GB at 17:48). No memory boundary was installed.

## Kit wave by hour

| Hour | 16 (from :50) | 17 | 18 | 19 (to :50) |
|---|---|---|---|---|
| LAUNCH + ENQUEUE | 22 | 5 | 5 | 21 |
| FAIL | 0 | 23 (all KV) | 0 | 1 (KV) |
| LAUNCH-REFUSED same key | 0 | 5 | 59 | 1 |
| LAUNCH-HELD by class breaker | 0 | 0 | 9 | 0 |
| HUB-SYNC-FAILED | 1 | 7 | 3 | 4 |

Tick time: median 167 s, max 535 s (17:53). 1900: median 207 s. ADOPT-GUARD alerts: 100 (hbm 70, s81_head 28).
TOOL-SKEW UNMEASURED s81: 34 of 34 ticks. STALE current-event: 257 (1900: 202), of which S81 296 rows listed,
203 owned by FIX-S81-COL-STALE. The live check still does not see intel2, epyc4 and epyc8.

## Which 1900 fixes landed

| 1900 fix | Landed | Evidence |
|---|---|---|
| Hub memory slice, HUB-MEM alert | no | proposal written (fleet-ops-r/PROPOSAL-intel2-mem-protect.md), waits for owner |
| Publish refuses a third tree; replaced tree deleted in the same step | partly | ot-retire-superseded.timer on all 7 hosts 18:47; first run retired nothing (no die lists superseded_trees). epyc10 still 48 trees, epyc9 44 |
| Guard reads structured roots only | yes | autoprune passes handoff prose as advisory (18:47) |
| Delete at result (d02d0f4d5bc) | yes | merged (COORD 19:05) |
| ALERT DISK-RATE | no | 0 lines |
| Place/CTS/route to the host with most memory | no | epyc10 load 169-188 on 96; four hosts at load 14-39 |
| Adoption gate = one dry gen per kit class | no | KV D5 and D8 failed after publish |
| Skew check on a gen host | no | s81 UNMEASURED 34 times |
| Wave mode PILOT at die switch (215be2f) | no | GREEN 140/140 at 19:06, approved r398, not on main at 19:06 |
| release_on names the plan sha | partly | 4 S81 records retyped by hand (r414); code fix cca8 pending |
| Self-heal at most twice | no | SRC-SYNC 13, PLAN_MISSING 49 |
| OWNERS.tsv with live lanes; live check fails loudly | no | NOT SEEN: intel2 epyc4 epyc8 |
| Clone registry | no | |
| Merge service posts one line per train | not checked | |

## The ten known events

| # | Event | Verified | Count, trend | Share of fleet time | Owner |
|---|---|---|---|---|---|
| 2 | Hold terms that cannot fire | yes | 203 types, 47-62 h; 19 more dead records in the audit | largest: 52% of S81 types idle while 55-61% of threads were idle | FIX-S81-COL-STALE, HOLD-FLOW-R |
| 3 | KV D5 face_guard hash | yes (19:49 fail line) | 1 pilot; third KV tree to fail at gen | under 1% compute; KV 0 kits in 5 h | KV-R |
| 4 | KV HG2b schema | yes (KV-R 19:43) | 1 PRE/G0; new | one bind + gate cycle, about 1 h of one host | KV-R |
| 5 | HEAD SPE export, false seam PASS | yes (HEAD-DIE-R 19:50) | 566 aliases, 1 false PASS; new | none direct; one archived view invalid | HEAD-TYPES-R2 |
| 1 | Dirty hub, wave skip | partly: skip real, cause is the lock | 1 tick; dirty hub 6 episodes, 15 alerts (1900: 14) | under 0.1% | FLEET-OPS-R |
| 8 | epyc2 cleanup by apparent size | yes (FLEET-OPS-R 19:14) | 15 trees freed about 0 GB; second pass 51 to 159 GB | none direct; one cleanup round | FLEET-OPS-R |
| 10 | Stale ot-heavy in /usr/local | yes, fixed by hand | 6 of 6 hosts were stale; 20:00 all 6 equal rt/current (4b40ef39f849) | unknown: admission ran old code for hours | FLEET-OPS-R |
| 9 | ot-run plan priority by script name | yes (ot-run line 861, 1608) | count not logged | small: a plan job with another name queues behind type builds | FLEET-OPS-R |
| 6 | QC gate, SRAM libs not mounted | not found in posts or log | 1 per brief | one gate run | QC-TYPES-R |
| 7 | Waiter matched its own cmdline | not found in posts or log | 1 per brief | none direct; one lane step stalled | new |

## Classes and structural fixes

### A. Holds that cannot release (event 2)

Root cause: a release term is free text checked against two strings (event sha, plan file name). A term that names
anything else is accepted and never matches. `result:` terms name a lane, and nothing checks the lane is alive.
The matcher needs a whole token, so `event_adopt:S4q9l2` will not fire for a plan named s4q9l2d (FIX-S81-COL-STALE
19:59): the same class is already planted in the new QC Kf holds.
Fix:
- (FIX-S81-COL-STALE) merge cca8efdc426.
- (HOLD-FLOW-R) a hold is refused at write time unless each term resolves: event names come from the die's
  planned_events list, result lanes from the live lane list. No free text.
- (HOLD-FLOW-R) every tick: a hold older than 12 h whose term has no possible producer posts one NEEDS-ACTION and
  is listed in LOOP-GAPS. This makes the class self-stopping.
- (QC-PLAN-R via HOLD-FLOW-R) check the two Kf terms against the S4q9l2d and S4q9m event names today.

### B. Tree published without a dry gen (events 3, 4; 1900 class 4)

Count: D3 24 fails, D5 1, D8 1 gate; QC and S81 earlier. Trend: flat, third review.
Root cause: publish checks that files were copied, not that gen and PRE/G0 accept them. Frozen views are picked
by path; D5 took 3 wrong ones (w652, w653, w672) while the correct bytes sat in w1057. The schema rejects unknown
advisory fields, so a harmless record fails a gate after an hour of bind.
Fix:
- (FLEET-OPS-R) publish runs schema check, PRE/G0 static checks and one dry gen per kit class in a sandbox that
  mounts only the tree. It also recomputes every hash named in provenance.json. Any miss fails the publish.
- (KV-R) frozen views are addressed by content hash, not directory name.
- (FLEET-OPS-R) the schema check runs first, before bind, and takes seconds. Advisory fields go under one
  `advisory` key that the schema ignores.

### C. Checkers that pass on empty input (event 5)

Root cause: the seam check reported PASS with link_i max and min null. No arcs measured was read as no violation.
The export wrote 566 output aliases that cycle; nothing reads the exported Verilog back.
Fix (HEAD-TYPES-R2, then all dies): every checker prints the count of objects measured and fails when it is 0 or
below the expected count from the plan. The export step re-reads its own netlist and runs a loop check before
the archive step. A view is archived only after that read-back passes. b5bd2c9e3a2 is not gated yet.

### D. Hub checkout as working copy and config store (event 1)

Root cause: lanes edit kit_wave.json in place. The wave reads the file as it is on disk, and hub sync stops for
everyone until the edit is committed. The lock skip is silent about who holds the lock.
Fix (FLEET-OPS-R):
- Lanes never edit kit_wave.json in the hub. One command applies a JSON patch under the lock and commits in the
  same step. The wave loads the committed blob (`git show HEAD:autopilot/kit_wave.json`), so an uncommitted edit
  has no effect.
- The lock file records pid and command; a skip prints them. Two skipped ticks in a row post an ALERT.
- Move generated files (NOPROG.tsv, STALE.tsv, kit_wave_state.json at 711k changed lines) out of the checkout.

### E. Installed tools differ from main (events 9, 10)

Count: ot-heavy 6 of 6 hosts; noprog_stage.py DIFFERS on 7 of 7 hosts now (FLOW-HEALTH 19:07).
Root cause: sync flips rt/current only. Copies in /usr/local and ~/.local/lib are separate files.
Fix (FLEET-OPS-R): installed entry points are symlinks into rt/current, so a flip updates them. The drift table
in FLOW-HEALTH gains ot-heavy and ot-heavy-reconcile, and any DIFFERS row is an ALERT. For event 9: plan priority
is granted by a marker the plan-event apply writes (job spec field), not by script basename.

### F. Disk measured wrongly, and still filling (event 8; 1900 class 2)

Root cause: the cleanup counted apparent size; sparse and hard-linked trees free almost nothing.
Fix (FLEET-OPS-R): the cleanup reports `df` before and after and sorts candidates by blocks with one link.
DISK-RATE alert is still missing; epyc8 needs it tonight.

### G. Environment and wait scripts (events 6, 7)

Fix: (QC-TYPES-R) the sign-off container start checks that every lib and LEF named in the kit exists inside the
container and stops in the first second with the missing path. (new, small) one shared wait helper that waits
on a pid or unit name, never on a command-line pattern; lanes do not write their own pgrep loops.

## Order of work

1. COORD: approve cca8efdc426; confirm 215be2f is on main.
2. HOLD-FLOW-R: hold term validation at write time and the 12 h dead-term alert. Check the QC Kf terms.
3. FLEET-OPS-R: publish gate (schema + PRE/G0 static + dry gen + hash check). Third request.
4. FLEET-OPS-R: wave reads committed config; patch command; lock owner in the skip line.
5. FLEET-OPS-R: epyc8 disk tonight; DISK-RATE alert; symlinked entry points.
6. HEAD-TYPES-R2: fail on zero coverage; export read-back.

## Not checked

- Who held kit_wave.lock at 19:16 (the lock file has no owner record).
- Events 6 and 7: I found no post or log line; counts are from the brief.
- How long /usr/local ot-heavy was stale and which jobs it mis-admitted.
- QC "other flow error 26" and S81 "other flow error 7" were not opened. Admission refusals: none in the log
  window; epyc10 admits only 35 GB, epyc7 refuses jobs without --dir on scratch2 (root 103 GB under the 150 floor).
