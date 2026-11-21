# FABLE-FLOW-0800: procedural / flow review, window 11-21 03:43 to 05:55 PST

Lane FABLE-FLOW-0800 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled or launched.
Previous: lanes/FABLE-FLOW-0400.md. This file replaces the 11-18 report of the same name.
Sources: autopilot/log.txt (5,591 lines in the window), autopilot/kit_wave.json, lanes/FLOW-HEALTH.tsv (05:08),
tools/failure_breakdown.py (run 05:45), `ot-run --status` (05:50), lanes/posts/*.md since 11-20 18:00, lanes/LANE-STATUS.tsv,
tools/post_redirect.py, rt/current (b8c28cb91890), hub commits d442c09bb6e, 69b9219941b, a29412b66af, e3ecd2a631d.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Fleet base: 292 running units (V, ot-run status), so about 584 unit-hours in the window.

## Headline

1. **The 0400 top class is closed (V).** A newer attempt stopping the live older one: 0 in the window (62 in the 15.7 h before).
   LAUNCH-KEEP fired once (05:22, s81 col_h9_r2) and held the relaunch. `restage_min_wait_s` is 1800 again.
2. **New top class: private kits on hand-written env subsets.** 5 lanes confirmed it after ruling d442c09bb6e, on at least
   7 kits. No tool builds a private kit spec from the wave env; each lane copies a spec or writes exports by hand. Class (a).
3. **Lane turnover is the second cost.** 11 lanes stood down between 04:13 and 05:41. 20 posts went to stood-down lanes and 23
   came from them. The redirect table exists but 14 of its 58 stood-down rows do not parse, so the redirect skips them. Class (b).
4. **Each plan apply rewrites fleet settings in the die block.** The S81 J6 apply (04:14) and the KV D26 apply (05:40) put
   intel1 and epyc9 back into `gen_hosts`. Five S81 kits, three of them J6 representatives, sat on intel1 (admit 0) and were
   moved after up to 77 min. Class (c).
5. **Sign-off count: 493 any plan, 409 current plan (V), +0 / +1 since 03:45.** STALE 105 (0400: 106).
6. **Disk: intel1 scratch2 120 GB, 97 percent full (161 GB at 03:5x); first two disk refusals in the window (V).**

## Recent fixes: are they live

rt/current on the hub and all six build hosts is b8c28cb91890 = origin/main tip (history.log 05:39) (V).

| Fix | State |
|---|---|
| d629bdc540 reclaim guard, cancel-rows lock wait | Live (V). 10 CANCEL-ROWS after 04:51, all closed. 22 terminal attempts reaped through the delete guard; 1 protected path refused (03:46). No lock timeout line. |
| 9dff8693c2 WAIT-VISUAL advisory | Live (V). 3 VISUAL-PENDING "(routes anyway)" at 05:36. UNDER-USE still lists `route_hold:WAIT-VISUAL=1` at 05:4x (was 9): one row not re-evaluated, watch one more tick. |
| b8c28cb918 stale-for-review advisory, ot-run cancel by unit | In rt (V). No stale-for-review line since adoption, so not exercised. COORD cancelled two hd_lep0N kits by exact dir at 05:46 (R). `WAIT-FORM=53` is still a hard route hold, see class (h). |
| a5603de7c5 LAUNCH-KEEP | Live and working (V), see headline 1. Restages after 04:20 waited 54 to 77 min. |
| a5603de7c5 BIND-GEN-TOOLSKEW | Code present (kit_wave.py:8648). 0 log lines ever, so not exercised. Its fallback prints "skipped: no checker in this rt"; that path is silent in the wave log (P: log it once per die). |
| a5603de7c5 per-cause cap, drt-nopath hold | Hold code present (11031). Cap lines still read "(mixed errors)" at 05:44 (kv3_hub_Wo 9 attempts, col_h10_r1 7). 7 `route-make-fail: make exit 2 (see run_route.log)` in the window, cause still not read. Not working yet. |
| c3755c6b21b main test fix | On main. `test_landing_place_origin_home.py` 10 passed on rt/current (V). |
| 69b9219941b OT_MAXWIRE_POST_SKIP dropped | Live in kit_wave.json (0 occurrences) (V). It is a hub config commit, so it is not on main by design. Kits generated before 05:41 keep the skip. |

0400 leftovers: s81 pin is now a sha, TOOLS-LAG s81 measures 11 commits (fixed). HUB-SYNC alert cleared. Not done: GRT
booked as 2 threads (2,428 threads granted on 752 cores), `parked` flag for hbm (30 ADOPT-GUARD alerts, STALE 104).

## Classes, ranked by fleet time and decision cost

### (a) Private kits on a hand-written env subset (NEW, largest decision cost)

- Count (R, each lane's own diff against the wave kit, posts 05:32 to 05:53):

| Lane, kit | Keys missing or different | State |
|---|---|---|
| HEAD hd_lep0N shelf_bf, col_bf (R4) | OT_PGCAP, OT_PLACE_MAX_FANOUT, OT_CLAND_STRIP_DENS, OT_PG_CELL_KEEPOUT, flow_tag, OT_IO_HOLD, OT_SIGNED_VIEW_SHA, OT_GPL_SPARSE_UTIL; extra `--cland-pinslot all` | Regenerated, old kits cancelled 05:46 |
| S81 lepe_mu_LP t2 proof7, 7b, 8 | OT_CBC_REACH_UM, OT_PLACE_MAX_TRANSITION, OT_ABC_RECIPE, OT_ABC_TARGET_PS; tap window 208 vs 51, tap sinks 1500 vs 1000, hold margins | Still in GRT |
| S81 col_h9_r0 rep kits (2) | OT_NATIVE_RESET_SCOPE, OT_GEN_M8_GRANT | Caught before gen |
| S81 slice t9, t36 | OT_GPL_SPARSE_OVERFLOW | R3 at 05:50: this one is the current gen rule; the wave kit is the stale side |
| QC cb fp3, fp4 | named by COORD | Not re-read this round |

  OPUS-FIX-S81-SVC-R6 and TAP-GRID-R2 already build from the wave spec and diff before launch.
- Trend: same class as hd_serdes (a week on S81 gpl settings) and the 405 um default (723 of 816 gens refused). Third time.
- Root cause (V): kit_wave.py has no command that emits a kit spec for a private plan. The wave env is assembled inside the
  launch path (die_gen_env + item_env + gen_args + flow_tag + tools sha), so a lane can only copy an old spec.json or retype
  exports. A second defect shows in the slice case: "the wave kit of the same type" is an old attempt and may itself predate a
  gen rule, so a config.mk diff against it gives false differences. The ruling asks for a manual diff; a manual diff is a
  discipline, and this class has already beaten discipline twice.
- Structural fix (P), three parts, all in the existing code paths:
  1. `kit_wave.py private-spec DIE ITEM --plan P --src TREE --out DIR [--delta KEY=VAL --why TEXT]...`. It calls the same
     function the wave launch uses, so the env is computed fresh from the current die config, never copied from a kit. It
     writes spec.json with `env_parent` (sha of the wave env for that item) and the declared deltas. `run-item SPEC` then
     builds the kit as today.
  2. `run-item` writes `kit_env_provenance.json` into the kit (wave env sha, deltas with reasons, tools sha, plan sha).
     `run_kit.sh` KIT_PREFLIGHT fails with ENV-PROVENANCE when the file is missing, or when the config.mk export hash is not
     wave env plus the declared deltas. A hand-built kit then cannot start place. Wave kits pass by construction.
  3. ot-run DONE/DIED posts for a kit print `env=wave` or `env=wave+N(keys)`. A result is comparable or it says why not.
  Test: the 7 kits above; preflight must refuse hd_lep0N shelf_bf and lepe proof8, and pass the 05:46 regenerated kits.
- Owner: FLOW-NOADV-R3 (gen env, flow tag) for parts 1 and 2; FLEET-WATCH-R5 for part 3.
- Fleet time: about 7 unit-hours in the window, 1.2 percent (I: three lepe kits in GRT, two hd_lep0N kits 0.6 h each). The
  larger cost is that every conclusion drawn from those kits has to be re-measured.

### (b) Stood-down lanes: posts from them, posts to them, work left behind

- Count (V, lanes/posts since 11-20 18:00): 18 stand-downs, 11 of them in this window (context limits, 04:13 to 05:41).
  - 20 posts addressed to a lane after its stand-down. PRECHECK-1119 cc to ADOPT-CENSUS-1800: 7 (stood down 11-20 18:55,
    still a fixed cc). FAM-S81-COL-R3: 5. PLAN-GATE-PRE-1115 WAITER-FAIL relays to SVC-R5, LEAF-R3, KV-HUB-R2: 4.
  - 23 posts from a lane after its stand-down. 13 are automatic ot-run DONE/DIED lines filed under the dead lane's name.
    10 are RESULT or HANDOFF lines written by hand "after stand-down" (SVC-R5 3, KV-PLAN-R4 2, KV-HUB-R2 2, LEAF-R3 2,
    SLICE-R2 1). They are useful, but they sit in a post file no successor is told to read.
  - Work racing across the handoff: QC-PLAN-R9 launched a duplicate that truncated b13.out (R, 03:48). OPUS-FIX-S81-LEAF-R3's
    t39 unit died rc 143 while it still read it ("someone else stopped it", R, 05:29); the successor had taken over 05:33.
    Waiters are armed on one unit id and are lost when it is relaunched (QC b12 to b13; S81 C3d fired on a rewritten bind out).
- Root cause (V): lanes/LANE-STATUS.tsv is written by hand at stand-down. tools/post_redirect.py needs column 2 to be exactly
  `stood-down` and column 3 to be exactly a lane name. **14 of 58 stood-down rows fail that** (date or reason typed into the
  status cell, prose after the successor). Measured with the tool itself: posts to FAM-S81-COL-R3, FAM-S81-SLICE-R2 and
  OPUS-FIX-HEAD-LEP0N-R4 pass through unchanged; ADOPT-CENSUS-1800 has no row; FLEET-WATCH-R4 to R5 is one of the 14.
  3 lanes have two rows. The redirect also only rewrites addressees. Nothing moves unit ownership, and the ot-run notifier
  and the waiter relay post under the name captured at launch.
- Structural fix (P):
  1. `bin/stand-down.sh LANE SUCCESSOR "note"` is the only writer of LANE-STATUS.tsv: fixed columns, the note in column 5,
     one row per lane. coord-commit refuses a commit whose LANE-STATUS.tsv row fails the schema. Repair the 14 rows now.
  2. post.sh treats a post whose text starts with STAND-DOWN / STOOD DOWN and has no row as an error with the command to run.
  3. The ot-run notifier, PLAN-GATE-PRE relays and PRECHECK cc lists resolve the lane through `post_redirect.py --resolve`
     at post time, so DONE/DIED and WAITER-FAIL lines land in the live successor's file.
  4. `ot-run` submit and cancel read OT_LANE; a stood-down lane gets a refusal that names the successor. A dead lane's
     chain script then stops at its next launch. `ot-run --list --lane X` gives the successor the units it inherits.
- Owner: new Sonnet lane (LANE-REGISTRY-1) for 1 to 3; FLEET-WATCH-R5 for 4.
- Fleet time: under 0.5 percent of compute. The cost is latency: 4 unanswered WAITER-FAIL relays in 30 min, and each
  successor re-arms waiters by hand (KV-HGI-R3 left 6 units in flight with no waiter).

### (c) A plan apply rewrites fleet settings; kits generated on a host that admits nothing (NEW)

- Count (V): 5 RESTAGE in the window, all away from intel1, each with "the last attempt was killed on intel1": leaf t31
  (6 min), col_h9_r1 (7 min), serdes t2 (77 min), lepe_mu_LP t2 pilot (54 min), col_h9_r2 (61 min). About 3.4 h of queue
  wait, on three J6 representatives. intel1 admitted 0 GB for the whole window (250 GiB admit rule, avail 170 to 274 GB).
- Root cause (V): hub a29412b66af 05:50, FLEET-WATCH-R5: "KV-D26 atomic apply re-added epyc9 + intel1 to qwen_kvsys
  gen_hosts ... removed again". The S81 RESTAGE-PICK lines show the same: gen_hosts held intel1 and epyc9 from the 04:14 J6
  apply until about 05:14. The apply writes the whole die block from the event's copy, so a fleet edit made after that copy
  was cut is lost with no log line. This is the unpushed-config class in a new place.
- Structural fix (P): (1) fleet keys (`gen_hosts`, host caps, restage settings) move out of `dies.<die>` into a top-level
  `fleet` block that apply_reviewed_tree_marker never writes; until then the apply merges and logs APPLY-KEPT for every
  non-plan key it leaves alone. (2) The gen-host pick drops a host whose current ot-run admit is below the job's memory,
  whatever the list says. Test: replay the D26 apply on the 05:39 config; gen_hosts must be unchanged.
- Owner: FLEET-WATCH-R5. Fleet time: 5 gen stages redone (under 0.3 percent); about 1 h lost on each of three representatives.

### (d) Kits launched minutes before their own lane's plan switch

- Count (V): 6. S81 col_h9_r1 and col_h9_r2 (60 replicas each) launched 04:07 on event 224567138ab; the J6 apply landed
  04:14 and both were launched again on dc92652f0d5 at 04:16 and 04:20. KV kv3_hgi_v3, v5, v8 and kv3_sys_c launched 05:31 on
  KV-D25e3 by retry keys that KV-PLAN-R5 committed at 05:23; the same lane applied KV-D26 at 05:40. Plus 1 SKIP-OLDPLAN
  (slice_station t18, 05:03), which is the guard working.
- Root cause: the owner rule (never start an old-plan kit when a current-plan row is queued) can only see an event that is
  already applied. An apply that is composed and in its gate is invisible to the wave, so hold releases and retry keys
  written just before it launch on the old plan.
- Structural fix (P): the apply tool writes `dies.<die>.event_pending = {event, since}` when its gate starts and clears it
  at apply or failure. While it is set (cap 60 min, then it expires with a log line) the wave starts no new gen for that
  die and logs LAUNCH-WAIT-EVENT. Running kits are untouched, so the owner rule on running kits holds.
- Owner: FLEET-WATCH-R5 (wave), the die PLAN lanes (set the key). Fleet time: about 3 unit-hours, 0.5 percent (the J5
  col_h9_r2 attempt runs on beside its J6 twin; 4 KV kits 0.4 h each before the switch).

### (e) Retries on a tool defect already fixed on main: stale flow files in the kit

- Count (V, R): 5 KV rows (kv3_hgi_v3, v5, v8, kv3_sys_c, kv3_hub_Wo) at 6 to 9 attempts. kv3_hub_Wo attempt 9 ran 5.5 h and
  died at `cts.tcl line 89 cannot read tb_cdirect`, fixed on main 5294e088f553 (R, FAM-KV-HUB-R2). The wave filed it as
  `CRASH route-make-fail` and then BLOCKED-CAP "9 attempts (mixed errors)". e3ecd2a631d names the mechanism: "KIT_FLOW_REFRESH
  EBUSY skipped".
- Root cause: the kit flow refresh skips a busy file and continues, so the kit runs with a mix of old and new flow files
  and nothing records it. The classifier stops at the make exit code (0400 class c, still open), so a CTS Tcl error counts
  as a route failure and as one more design attempt.
- Structural fix (P): (1) KIT_FLOW_REFRESH is all or nothing: on EBUSY it retries, then fails the kit at preflight with
  FLOW-REFRESH-PARTIAL (an infra key, no attempt counted). (2) The kit records the flow-file manifest sha; preflight compares
  it with the rt manifest. (3) The fail key is the first `[ERROR` or Tcl error line of the failing stage log, not "make exit 2".
- Owner: FLOW-HEALTH-1 (classifier), KIT-OPS-5 (refresh). Fleet time: about 3 unit-hours in the window, 0.5 percent
  (kv3_hub_Wo 2 h, the four relaunches 0.2 h each); about 30 unit-hours over the 6 to 9 attempts (I).

### (f) Waiters on the wrong log, and waiters tied to one unit

- Count (V): 1 confirmed in the window (hd_lep0N R4 waiter grepped run_place.log on a GOAL=route kit, which logs to
  run_route.log; found by FABLE-FIX-HEAD-LEP0N, in ruling d442c09bb6e). 8 handoff files carry a `grep ... run_place.log`
  wait loop that the next lane will copy. 2 waiters lost by a relaunch or a rewritten output, see (b).
- Root cause: a waiter is a hand-written ssh grep on a log name. The log name depends on GOAL, the marker text depends on the
  flow version, and the unit id changes on relaunch. A wrong name waits for ever and looks like a slow job.
- Structural fix (P): one `ot-wait --kit DIR --until place|cts|grt|route|signed|end`. It reads the stage status that
  run_kit.sh already writes and the ot-run unit state, never a log. It exits non-zero when the unit dies, follows the kit
  dir across a relaunch, and exits 3 with "stage not in this GOAL" when the stage can never be reached. The handoff template
  lists waiters as ot-wait lines only.
- Owner: new Sonnet lane (can be LANE-REGISTRY-1). Fleet time: none in compute; hours of lane latency per wrong waiter.

### (g) Plan-file and tool path errors in private G0 / census / bind scripts

- Count: no post in the window reports a wrong plan path in a private G0 or census script (text search of 1,275 posts; not
  seen is not the same as none, COORD named the class). Related, measured: QC b12 ended R8_STALE because a copied
  r8_refresh.py could not find land_r8_derive.py (R, fixed 7ff721a009; one bind cycle lost). HEAD-PLAN-R16 handoff carries
  "rewrite plan paths" as an open item. hbm config points at an unreadable plan file (30 alerts, die parked).
- Root cause: private scripts take the plan, the tree and the tool as three free paths, and copy tools out of rt. Nothing
  ties them together, so a stale path gives a green result on the wrong input.
- Structural fix (P): G0, census and strict bind take `--bind-out DIR` or `--plan P --expect-sha S` and refuse on mismatch;
  the first output line is `PLAN <path> sha <12> TREE <path> RT <sha>`, and a RESULT post must quote it. Tools run as
  `rt/<sha>/tools/...`, never from a copy (a copied tool fails its sibling-import self-check at start).
- Owner: PRECHECK-1119 (census, G0 wrappers). Fleet time: under 0.2 percent measured (one bind cycle, about 1 h).

### (h) Holds, stale state, unowned

- 3 S81 leaf rows (t9, t28, t5) were filed `infra-orphan: client lost, kit logs idle 28.8 to 30.6 h` when the 04:50 cancel
  sweep reached them (V). They were counted as running for more than a day; REAP-DEAD only reports. About 6 unit-hours in
  the window, 1 percent, if they were idle the whole time (I). Fix (P): REAP-DEAD posts one NEEDS-OWNER line when the kit
  logs are idle over 8 h and CPU has not grown; it still stops nothing. Owner: FLEET-WATCH-R5.
- `route_hold:WAIT-FORM=53` (QC, "visual verdict ISSUES; rebuild on a changed form", set 11-20 07:33 on event ...V0E) is
  unchanged for 22 h and across a plan event (V). The owner lever says a visual verdict gates sign-off, not route. Check
  whether these rows belong to a superseded event and should be retired. Owner: FLEET-WATCH-R5 with QC-PLAN-R9.
- 319 S81 rows held by S81-J6-ASSEMBLY-R2 "representatives first"; the lane is now R3. HOLD-AUDIT reads 0 on all seven
  counters (V). The hold text names a lane that no longer exists; release terms should name the event, not the lane.
- STALE (V): KV qkd_pv_fin_s8_pin CANCELLED 20.3 h, unowned (third review). kv3_io_cor STRUCT-STOP 7.2 h. HBM 104, parked.
- Skew (V): TOOL-SKEW s81 177 of 18,884 modules differ from pin 39d243610bd2 (537 before the re-pin); KV 349 of 18,891
  from pin 4e46a7ec46c5; KV was UNMEASURED 04:13 to 05:43 (pin manifest missing on the hub). TOOLS-LAG: QC 170, HEAD 116
  commits, both missing r708.
- ot-run DONE lines from epyc10 and one more host print the end time in UTC ("ended 13:10:26") under a PST post stamp (V).
- Successors named as needed and not seen started by 05:55: OPUS-FIX-KV-HGI-R4, a successor for OPUS-FIX-KV-PV-R4.

### (i) Disk and admission

- Measured (V, 05:50): scratch free intel1 120 GB (97 percent used; 161 at 03:5x, about 20 GB/h), epyc9 169, epyc2 179,
  localhost 267, epyc8 285, epyc10 576, epyc7 639. Admits: intel1 0, epyc7 0, epyc10 46, epyc2 66, epyc8 84, epyc9 137,
  localhost 213 GB.
- Refusals (V): 2 `NOT RUN: no host qualifies (intel1: /srv/opentallas-scratch has 26 GB free < floor 50 GB)`. Earlier
  lines show that disk falling 46, 39, 35, 30, 26 GB. No memory admission refusal line.
- Root cause (I): intel1 keeps being chosen (class c) while it is the fullest host, and the reaper has no trigger on the
  rate of fall. Fix (P): class (c) part 2 with disk added (no gen target under 250 GB free), and CLEAN-ALL runs on intel1
  when the 2-h slope reaches the floor inside 4 h.
- Owner: CLEAN-ALL-1115, FLEET-WATCH-R5. Fleet time: none yet; intel1 scratch2 reaches 50 GB in about 3.5 h at this rate.

## Do now (ordered)

1. FLOW-NOADV-R3: `kit_wave.py private-spec` plus the ENV-PROVENANCE preflight, class (a). Until it lands, lanes build
   private kits from a fresh wave spec, not from an old kit's config.mk.
2. New Sonnet lane LANE-REGISTRY-1: repair the 14 LANE-STATUS rows today, then stand-down.sh, schema check, notifier and
   relay resolution, and `ot-wait`. Classes (b) and (f).
3. FLEET-WATCH-R5: fleet keys out of the die block (or APPLY-KEPT merge), admit-aware gen-host pick, `event_pending`
   launch wait, the 3 idle-29-h rows, WAIT-FORM=53. Classes (c), (d), (h).
4. FLOW-HEALTH-1 and KIT-OPS-5: all-or-nothing flow refresh, fail key from the first error line, per-cause cap that
   actually prints the cause. Class (e).
5. CLEAN-ALL-1115: intel1 scratch now.
6. PRECHECK-1119: drop ADOPT-CENSUS-1800 from the fixed cc list; plan sha line in G0 and census output. Class (g).
