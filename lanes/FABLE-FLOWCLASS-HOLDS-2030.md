# FABLE-FLOWCLASS-HOLDS-2030: holds that leak, over-hold or drift

2026-11-15 21:05 PST. Read-only review. Sources: autopilot/kit_wave.json (75 revisions today, each replayed),
autopilot/log.txt, autopilot/kit_wave_state.json, journal of autopilot.service, rt/current kit_wave.py,
rulings r187-r216. Builds on FABLE-FLOW-2000 section 1; what is new here is marked NEW.

## 1. Why the 60 S81 items launched

60 launches 18:17-19:35 = 16 items (51 slice_station, 9 serdes), 60 of 60 FAIL sdc_lint at gen, 15.9 wall-h.

Cause: a hold was never applied. It was not a pattern miss, not a key-format error, not an auto-release.

1. Replay of fnmatch for each launch against the config revision in force: 0 of 60 held. HOLD-AUTO-RELEASE
   never fired today.
2. The 16 items lost their earlier holds in two bulk releases: 7 at 13:32 (8fd00a1, B6gE adopt, "release
   rest"), 8 at 16:27 (efdd837, the SIGNED-UNVERSIONED release), 1 was never held.
3. The sdc_lint holds added later (16:09, 16:30, 17:10) were built from two lists that exclude these items
   by construction: "items whose last FAIL is sdc_lint" (theirs was @kit_rtl, BLOCKED-FLOW at 14:11) and the
   G1d tap-offset drop list (r198: the failing set is the 59 types NOT in that list).
4. NEW, proven from code + journal: the trigger was the 18:11 die_gen_env edit (OT_TT_SETUP_REPAIR=both, a
   P&R variable). rearm_changes() returns "die_gen_env" for every failed row whose spec differs;
   journal 18:16:51: "KW_REARM s81: 883 failed attempt(s) ... re-armed without a retry key" (QC 494, KV 272,
   HEAD 55 in the same tick). input_digest() changed too, so the BLOCKED-FLOW 3x count of 14:11 was dropped.
   16 launches followed at 18:17-18:19.
5. NEW: SdcLintError is a Python exception at gen, so it is classed INFRA. fail_signature() returns None for
   INFRA: it never counts toward RETRY_CAP. fail_sigs has 0 of 261 entries at n >= 3 and
   kit_wave_blocked.tsv holds only its header after 1,867 FAILs today. Each item got its INFRA resubmits.
6. NEW: stale retry keys. dies.s81.retry has 1,650 "item@N" entries from old events (QC 1,006, HBM 475,
   KV 403). Attempt numbers restart per plan block, so an old key fires on a new attempt: 19:04
   "RETRY-RELEASE slice_station__t6__cl54a9ceeb@6 ... released once" -> launch 19:05. The same item still
   has keys @9..@14 armed. 563 RETRY-RELEASE lines today.
7. r198 item (2) (18:25) reached the config at 20:20: 115 min, 44 launches in between.

## 2. The structural fault

The wave is default-launch, and about 1,700 failed rows are permanently re-armed (KW_REARM now: S81 874,
QC 488, KV 273, HBM 156, HEAD 53; a row whose spec has an older src_sha or host list is "changed" for
ever). hold_items, a hand-kept deny list of names, is the only barrier. Every name missing from the list
launches; every list is written after the fail. That is why S81 keys went 252 (13:32) -> 483 and still
leaked.

Release side, measured on the current file:

| die | keys | release term can be checked by the tool | cannot |
|---|---|---|---|
| S81 | 483 | 227 (`event_adopt:B6gG1d`) | 256 ("Event F" 216, "Event G" 33: names under 3 characters are refused by the code) |
| QC | 53 | 11 | 42 |
| KV | 43 | 0 | 43 |
| HBM | 107 | 0 | 107 |
| HEAD | 4 | 0 | 4 |

NEW, urgent: the 227 S81 `event_adopt:B6gG1d` terms will never be met. DIE-S81-92 gated the stacked event
as B6gG3 (20:43) and r198 orders G3b; the die event will never carry the token "B6gG1d". At the adopt these
227 keys over-hold, and the lift will be by hand again.

## 3. Design: no name lists on either side

One rule: a row launches only if its own inputs are not known to fail. Holds are compiled, not typed.

A. Fail key at every launch path (FLOW-HEALTH-1; extends r201 / r216 (2)).
   - key = (stage, normalized class, digest of the inputs read up to that stage: die tree sha, plan block
     sha, item kit-input digest, env keys that stage reads). No hub rt digest, no host list.
   - one function launch_allowed(row), called from fresh select, RETRY-INFRA, RETRY-RELEASE, KW_REARM and
     restage. A key that failed once does not launch until one member changes. No timer, no half-open.
   - INFRA exemption only for the transient patterns (_TRANSIENT_INFRA, NO_HOST, infra_kill). A tool
     refusal (SdcLintError, "plan invalid", proof ValueError) is class TOOL, counted.
   - env-to-stage table: a die_gen_env key re-arms only rows that failed at or after the first stage
     reading it. Unknown key = P&R (does not re-arm kit_rtl / gen fails).
B. Probe table instead of family holds (PLAN-GATE-PRE-1115, r198 (4)).
   - at compose/adopt run the cheap deterministic checks per item (sdc_lint, plan schema, kit_rtl bind
     arity) on every item of the release list; write probe.tsv (item, check, PASS/FAIL, input digest).
   - launch reads it: FAIL row = not launchable; PASS = launchable. "Release only the types that lint 0"
     becomes automatic and per item. No glob can miss or over-catch.
   - when a new class appears mid-event (2 items, same key class), the probe for that class runs on all
     items of the die before the next tick.
C. Holds for classes with no cheap probe (DRT-0255, far-negative setup, design waits) as records, one file
   per hold (new lane, on ruling_holds.py):
   {id, ruling, die, plan_sha, selector, release, owner}. selector = explicit item list from the event's
   release list, or a predicate on plan data (for example "type has M7 face pins"). The compiler expands it
   against the plan item list each tick and prints id, matched count, items. Zero matches = error. A hold is
   bound to its plan_sha and expires at the next adopt unless marked carry. hold_items in kit_wave.json
   becomes generated output.
D. Typed release terms only: plan_sha:<sha>, merge:<sha>, key_changed, probe_pass:<check>,
   signed:<item>, post:<queue line hash>. Free text (lane_ready, event nicknames) is rejected at write
   time. A probe-type release is per item.
E. Rulings in a fixed grammar: "HOLD <die> <selector> UNTIL <terms>". ruling_holds.py applies it in the
   same tick; no lane in between (removes the 115 min of r198).
F. Audit line every tick, section in FLOW-HEALTH hourly. Each must be 0:
   HELD-BUT-LAUNCHED, LAUNCHED-KNOWN-FAIL-KEY, RELEASED-TERM-UNMET (key removed while a term is false),
   HOLD-ZERO-MATCH, HOLD-TERM-DEAD (plan sha / merge sha / post that cannot occur), RULING-NOT-APPLIED,
   RETRY-KEY-OTHER-EVENT. Replay test: today's log gives at most 16 S81 sdc_lint fails (one per item).
G. retry keys carry the plan block: item@block@attempt. Old-format keys are dropped at load.
H. Owner labels from one lane registry; a successor line updates it. (die_owner was corrected tonight;
   owner_lane text still names DIE-S81-90, KV-101, HEAD-98, DIE-QC-101.)

Not proposed: launch caps, pilot gates, per-tick limits. A and B refuse known-failing inputs only.

## 4. Owners

| piece | lane |
|---|---|
| A fail key, env-stage table, F audit | FLOW-HEALTH-1 |
| B probe table at compose/adopt | PLAN-GATE-PRE-1115 |
| C, D, E, G hold records, compiler, grammar, retry key format | new Sonnet lane HOLDGEN-1115 (takes ruling_holds.py from KIT-OPS-5) |
| H registry; per-family smoke before any die-wide env edit | KIT-OPS-5 |
| operating the table until C lands; then retired | WAVE-HOLDS-1115 |

## 5. Tonight, config only

1. S81: re-term the 227 `event_adopt:B6gG1d` keys to the G3b plan sha before the adopt; release per item
   on sdc_lint 0 of the G3b gen, never by family.
2. Purge `retry` entries that do not name an attempt of the current plan block (S81 1,650, QC 1,006,
   HBM 475, KV 403, HEAD 38).
3. S81: `auto_rearm: false` until G3b adopts (the adopt gives new plan blocks, so rows launch fresh).
4. QC: 3 failed rows INFRA@gen on S4Q3C match no hold key now; hold or probe them.
5. No die-wide die_gen_env edit without the list of rows it re-arms (dry run of rearm_candidates).

## 6. Wasted share (00:00-20:20)

- 2,198 launches, 1,867 FAIL (85%), 1,639 before P&R (75% of launches).
- 926 fails repeat an error the same item already had today (42% of launches); 249 wall-h launch-to-fail.
- Pre-P&R fails: 445 wall-h at 1-2 threads, about 3% of fleet thread-hours. Fleet load at 20:50: 340 of
  736 threads. The loss is not CPU: S81 had 2 h with 100% of its launches failing while 480 keys wait on
  terms nothing can check, and 54% of the fleet is idle.

## 7. Stop list

1. Adding hold keys per failed item after the fail.
2. Holding or lifting by glob without the printed match list (r211: lift and correction 2 min apart).
3. Release terms that are event nicknames or lane names.
4. Lifting a hold on "fix merged" without one probe pass per family (15:37 lift of `*` -> 54 sdc_lint
   fails in the next hour).
5. Die-wide env edits that re-arm rows failing before the stage that reads the variable.
6. Classing deterministic tool refusals as INFRA.
7. Breaker timers and half-open releases.
8. Reusing item@N retry keys across plan events.
9. Bulk "release rest" at an adopt without the probe table.
