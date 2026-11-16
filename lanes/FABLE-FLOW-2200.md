# FABLE-FLOW-2200: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 21:43-22:10 PST on hub intel2.
Window: autopilot/log.txt 19:45-21:45 PST (1,541 lines), lanes/FLOW-HEALTH.tsv (21:27), kit_wave.json and
kit_wave_state.json (22:00), tools/failure_breakdown.py (22:00), `ot-run --status` (21:50, 21:58), df on 7 hosts,
rt/history.log, user timers, lane posts 20:00-22:00 incl. rulings r216-r231.
Previous review: FABLE-FLOW-2000 (window 17:45-19:45). Scope: process and tooling only.

## Headline

1. The S81 relaunch loop is closed. S81: 0 launches, 0 fails (was 60 and 60). Fails fell from 72 to 19, all on
   QC and HEAD. The cause is the family hold of 20:20 and `auto_rearm: false` of 21:14, both config edits.
2. The price is launch volume: 39 launches in 2 h (20 per hour; was 119 and 60). S81 and KV launch nothing. Both
   wait on an adopt step whose input is READY: KV tree c1 READY at 21:19, S81 B6gG3b READY+ADOPT at 21:46. At
   22:00 the wave config still names the old KV tree with the `*` die hold, and the old S81 tree.
3. epyc7 scratch ran full during the window: 52 GB free at 21:03, 4 GB at 21:44, 0.47 GB at 21:52, then 85 GB at
   21:58 and 111 GB at 22:02. `ot-run` reported epyc7 REFUSED. The runtime sync to epyc7 at 21:54 failed
   ("mkdir: No space left on device"), so epyc7 runs rt 9eab0c06ef18 while the hub and the five other hosts run
   421b431493f1. I did not find the writer (see Not checked). No lane post names it.
4. The hub scratch swings by 50 to 160 GB inside 20 minutes: 67 GB at 21:23, 44 GB at 21:32 (wave launches
   refused for one tick, 21:32-21:42), 210 GB at 21:50, 154 GB at 22:02, 147 GB at 22:08.
5. Turning on `kit_snap` for QC (r221) made a new fail class: 4 fails on 2 items at kit_rtl, where the kit names
   a path under `kit-store/snaps/<sha>/root/...` and the self-contained check rejects it.
6. Of the nine r219-r230 fixes asked about: 4 work, 3 work in part, 2 have not landed. Table below.

## Kit wave, 19:45-21:45

| | 19:45-20:45 | 20:45-21:45 | 2 h | FABLE-FLOW-2000 |
|---|---|---|---|---|
| LAUNCH | 25 | 14 | 39 (QC 23, HEAD 16, S81 0, KV 0) | 119 |
| FAIL | 12 | 7 | 19 (QC 17, HEAD 2) | 72 |
| ENQUEUE (place done) | | | 25 | about 35 reached P&R |

Repeats: 9 distinct failing items for 19 fails, so 10 fails (53%) are repeats; was 49 of 72 (68%).

| Count | Die | Stage | Class | Items | State at 22:00 |
|---|---|---|---|---|---|
| 6 | QC | gen | hard landing child proof: shared rst_xn[i] 8-9 loads. Labelled "INFRA: tool or source skew"; it is a design proof failure | 3 | held, term "DIE-QC-103 reset-ring proof fix" |
| 4 | QC | gen | KIT_NOT_SELF_CONTAINED: view points into build dir tl-qcstav2/rk (epyc2 only) | 1 (slw_st_a_v2__cl9f076a5c, attempts 13-16) | held since about 21:00; closed-view branch READY 21:44, not merged |
| 4 | QC | kit_rtl | KIT_NOT_SELF_CONTAINED on a kit-store snapshot path (new) | 2 (cbn_q01__clab6e67f2 3 times, tt_ctlm) | cbn_q01 BLOCKED 21:32; tt_ctlm not held |
| 3 | QC | gen | WAIT-DEP: stub provenance, view not exported | 1 (cbn_q00__cldbcda913) | held |
| 2 | HEAD | place | exit 143, signal 15: operator stop of rows launched without the die-phase keys | 2 | relaunched with keys |

## r219-r230 score

| Fix | Ruling | State | Evidence |
|---|---|---|---|
| S81 holds re-termed | r223 | working | 483 of 483 S81 keys carry a release term; 227 moved to `event_adopt:B6gG3*`. 13 SUPERSEDED-KEEP lines show the family key matching. 0 S81 launches |
| S81 auto_rearm off | r223 | working | `auto_rearm: false` since 21:14; no S81 launch after it. Its removal is a hand step tied to the G3b adopt |
| ot-src-refresh disabled | r219 | working | timer disabled and inactive, absent from the timer list |
| fail_route timer | r229 | working | timer runs every 10 min; 5 posts 21:48-21:58 (4 NEEDS-ACTION, 1 NEEDS-LANE). One class is misrouted, see class 5 |
| kit_snap strict on all dies | r221 | partly | config: on with strict view refs for QC, S81, KV, HEAD; not HBM (parked). Only QC and HEAD launched, so S81 and KV are unproven. New fail class on QC (4 fails). The smoke was called at RUNNING; that row (cbn_q01 a10) failed at 21:12 |
| tool_skew warn gate | r219 | partly | live since rt 0d0eec1e3a01 (21:03), `warn` on 5 dies, launches go on (12 after 21:04). Three defects, see class 6 |
| KV tree from one sha | r219 | partly | c1 built and gated (tools whole from main 8989ba7b1755), READY 21:19. Not adopted: wave src is still src_kv_kvgeom7u, `*` hold still set. A second KV tree from another sha exists (class 2) |
| failkey-1115b key and family breaker | r226 | landed, not exercised | in rt since 21:43 (9eab0c06ef18): `fail_key_gate` is in `launch()`. No FAIL after 21:43, so `fail_keys` has 0 entries and there are 0 LAUNCH-REFUSED and 0 RELAUNCH-ON-FIX lines. Judge it at 00:00 |
| typed FAIL classes | r220 | not landed | branch kit-ops-5-typedclass-1115 @23ab2044be6 READY at 21:2x, not in rt. Every FAIL line to 21:32 carries the old FLOW/INFRA/PLAN label; signal 15 is still a FAIL |
| HOLDGEN | r223 | not landed | one post in lanes/posts/HOLDGEN-1115.md; no compiled hold records, no per-tick audit table |

## Summary, ranked by waste

| # | Class | Count | Trend vs 20:00 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Two dies launch nothing; adopt steps wait on a hand edit | S81 0 and KV 0 launches; about 279 of 624 build threads idle | worse (32% -> 45% idle) | 45% | KIT-OPS-5, WAVE-HOLDS-1115 |
| 2 | Host disk full without an owner | epyc7 under 5 GB for about 15 min; rt sync failed; hub 44-210 GB | worse (hub was 146-149 flat; epyc7 new) | epyc7 (96 threads) refused for at least 20 min; hub refused one tick | CLEAN-ALL-1115 |
| 3 | kit_snap against the self-contained check | 4 fails, 2 items, 40 min | new | under 1% CPU; blocks the QC rows that kit_snap was meant to cure | KIT-OPS-5 |
| 4 | Known-failing rows relaunched | 10 repeat fails, 5 QC items | better (49 -> 10) | under 1% | FLOW-HEALTH-1 |
| 5 | Untyped classes: wrong label, wrong owner | 6 of 19 fails mislabelled; 3 of 6 items in one fail_route post sent to the wrong lane | same | none directly | KIT-OPS-5 |
| 6 | tool_skew gate reads badly | 7 "refuse" lines in warn mode; two module counts; S81 and KV unmeasured | new | none | TOOLS-CONVERGE-1115 |
| 7 | Config does not reach the kit | HEAD rows launched without die-phase keys: 2 stops at 20:13, 2 more rows relaunched unchanged at 21:05 (r228) | new | 4 HEAD place runs of 25-40 min | KIT-OPS-5 |
| 8 | Periodic jobs fail each tick | SRC-INCOMPLETE epyc2 13, ADOPT-GUARD 24, ARCHIVE FAILED 12, HUB-SYNC-FAILED 11, REAP-DEAD native59 12 | same or worse (9, 18, 12, 9, 12) | epyc2 at 19/128 load | KIT-OPS-5, FLOW-HEALTH-1 |
| 9 | Stale and unowned rows | STALE 271 current (+158 superseded); unowned S81 198, QC 11, KV 8, HBM 11 | worse (191; S81 192) | none directly | WAVE-HOLDS-1115, COORD |
| 10 | Log noise | DEDUP 804 + RETRY-IGNORED 158 = 62% of 1,541 lines | same (64%) | none | FLOW-HEALTH-1 |

## 1. Adopt steps wait on a hand edit

Loads at 21:58: epyc2 19/128, intel1 99/112, epyc8 47/96, epyc9 47/96, epyc10 71/96; epyc7 refused (last
read 62/96 at 20:23). About 345 of 624 threads loaded. Every host but epyc7 admits 447 to 760 GB.

- KV: 0 launches for about 6 h. KV-102 posted READY at 21:19 with gates (G0 0 errors, strict bind RC 0,
  LATCHECK 2404/2404, kit_rtl RC 0 on three types) and asked for the hold lift. 40 min later nothing changed.
- S81: B6gG3b READY+ADOPT at 21:46. 227 holds release on it, and `auto_rearm` must come off in the same step.
  216 more keys wait on "Event F" and 33 on "Event G"; r226 lists event names under 3 characters as not yet
  matched by `apply_hold_release_on`. Those 249 keys can stay held after their event adopts.
- Signed off now: S81 types 41 of 394, QC 7 of 127, KV 5 of 56, HEAD 19 of 26.

Root cause: an adopt is three hand edits by three lanes (die owner posts READY, KIT-OPS-5 moves `src` and
`event`, WAVE-HOLDS lifts keys), each waiting for the previous post to be read.
Fix: one `adopt` command owned by KIT-OPS-5 that takes the READY post's tree, plan sha and event name, runs
adopt_guard on all gen hosts, and writes `src`, `event`, the hold releases and the `auto_rearm` removal in one
commit. HOLDGEN's typed release terms are the input it needs; until then KIT-OPS-5 does KV and S81 by hand now.
Decide first which KV tree is adopted: c1 (main 8989ba7b1755, KV-102) or src_kv_pin_0d0eec1e3a01
(TOOLS-CONVERGE, 34 GB on epyc10, built 21:49, not published). Two lanes built two successors from two shas.

## 2. Host disk

epyc7 /srv/opentallas-scratch2 (7.3 TB): wave log GEN-DISK-LOW 53, 44, 23, 11, 4 GB at 21:03-21:44; my df
0.47 GB at 21:52, 8.8, 20, 85, 111 GB after. No wave FAIL names ENOSPC in the window, so the loss is in lane
jobs and in the rt sync. epyc7 holds lane trees for S81 (s81-b3-clk, the S81 plan of record), KV (kv-102,
kv-pvgen) and GENBUG; a full disk there stops the two die owners that are about to adopt.
Hub: top recent trees under claude/: wt 99 GB (60 worktrees), rstxn-guard-1115 48 GB (new lane tree today),
rt 15 GB (37 trees), hub-coord 13 GB, restore-1115 10 GB. 19 top-level directories carry a .git.

Root cause: no component owns "free space on host X over time". The wave has a floor per launch, ot-run has
a floor per job, the cleaner runs hourly; lanes write outside all three. A lane's full clone or a view
restore of 50 GB lands between two cleaner runs.
Fix (CLEAN-ALL-1115): a 5-minute df sample per host into one table; when a host loses more than 20 GB in
10 min or falls under 2x its floor, post once with the three directories that grew most since the last sample
(keep a per-directory size table from the hourly pass, compare against it). Lane trees over 20 GB go to
epyc10 (4.4 TB free) or epyc9 (1.35 TB); the hub and epyc7 take none. FLOW-HEALTH-1: rt sync that fails on
a host posts once and the host leaves gen_hosts until its rt equals the hub's.

## 3. kit_snap against kit_self_contained

r221 turned kit_snap on for QC at about 21:10. cbn_q01__clab6e67f2 then failed at kit_rtl at 21:12, 21:22
and 21:32, and tt_ctlm at 21:22, each with KIT_NOT_SELF_CONTAINED on
`/srv/opentallas-scratch2/kit-store/snaps/<sha>/root/.../die-qc-103/treeA/.../plan_of_record/zz_s29_qc103_s4q3c.*`.
Reading from the path (I did not open kit_rtl.log): kit_snap redirects the plan input to the snapshot store,
and the later check treats any absolute path outside the kit as a leak. Two guards for one class disagree.
Fix (KIT-OPS-5): the self-contained check accepts a path under kit-store/snaps/<sha> when the sha is recorded
in the kit, since that store is content-addressed and replicated; or kit_rtl copies the file from the
snapshot into the kit. A config switch counts as smoked when one row passes the stage the switch touches,
not when the row is RUNNING. Do this before S81 and KV launch with kit_snap on, or the same class appears
on about 450 rows.

## 4. Relaunch of known-failing rows

Before 21:43: slw_st_a_v2__cl9f076a5c was BLOCKED-FLOW at 20:22 and launched again at 20:24 and 20:53;
cbn_q00__cldbcda913 was BLOCKED-PLAN at 20:33 and got RETRY-RELEASE at 21:13; cbn_q01 failed 3 times in
30 min before its block. The old breaker released once on preflight text (19:55). A BLOCKED line did not stop
the next launch. failkey-1115b replaces these paths and has been live since 21:43; there is no fail after it
yet. Existing FAIL rows (S81 748, QC 296, KV 250) have no stored key, so the first relaunch of each after an
adopt is not gated. That is correct for a new tree or plan; check that an env-only edit does not release
them (the 18:11 case).

## 5. Untyped classes

- The 6 "hard landing actual child proof failed: shared rst_xn" fails are labelled INFRA "tool or source
  skew". The cause is a reset-ring load count in the QC cland RTL (DIE-QC-103).
- fail_route class df55481680 (21:48) groups those 3 items with 3 KIT_NOT_SELF_CONTAINED items and sends all
  6 to QC-SRC-CLOSE-1115. Half the list has the wrong owner.
- BLOCKED lines at 20:22 and 20:33 name owner DIE-QC-101 (ended); the 21:32 line names DIE-QC-103.
Fix: merge kit-ops-5-typedclass-1115; fail_route then keys on the typed class, not on the first 60 characters.

## 6. tool_skew gate

- In `warn` mode the log line is "KIT-WAVE TOOL-SKEW refuse <die>: N module(s) differ from main", once per
  die per tick. Launches proceed. A reader takes it for a refusal.
- It reports 120 modules for QC and 136 for HEAD. FLOW-HEALTH.tsv SKEW (21:07) reports 38 and 43 for the same
  trees. The closures differ (433 modules against 229). One fleet, two skew numbers.
- The check runs inside `launch()`. S81 and KV launch nothing, so they have no reading and no NEEDS-LANE post.
Fix (TOOLS-CONVERGE-1115): one closure shared with the SKEW table; log "differ (warn, launching)"; measure
every enabled die once per tick outside `launch()`.

## 7. Config that does not reach the kit

HEAD NF13a rows launched at 19:47 without the die-phase keys; KIT-OPS-5 stopped and relaunched them (the two
signal-15 fails at 20:13). r228 (21:33) reports the config.mk files carry no OT_PG_* key, and hd_host_n and
hd_st_n3_turn were relaunched unchanged at 21:05; hd_host_n was stopped at 21:42 and launched again at 21:45.
r231 (kit_effective_env.json records the keys) is the audit. Add the gate: a row whose effective env lacks a
key that its item_env or die_gen_env sets fails at gen, before place.

## 8-10. Periodic failures, stale rows, log

- epyc2: SRC-INCOMPLETE 13 lines and ADOPT-GUARD 24 lines for the same QC plan file as at 18:24. Third review
  with this item open. epyc2 admits 760 GB at load 19/128.
- ARCHIVE FAILED 3054c87a89d6: 12 more lines. The backoff is in failkey-1115b (live 21:43); check at 00:00.
- HUB-SYNC-FAILED: 11 lines; lanes/NOPROG.tsv and now lanes/posts/HEAD-100.md edited in the hub checkout.
- lanes/CRON-HEALTH.tsv (FABLE-FLOW-2000 class 6) does not exist.
- STALE 271 current (was 191). Owner labels still name ended lanes: KIT-WAVE-1 116 rows, DIE-S81-90 39,
  FAIL-S81-1 25. S81 unowned 198.
- The runtime changed 3 times in 51 min (21:03, 21:43, 21:54), each a sync to 7 hosts.

## For COORD, in order

1. CLEAN-ALL-1115 now: epyc7 scratch (name the writer, free to 300 GB), then re-sync rt on epyc7. Hub: move
   rstxn-guard-1115 (48 GB) and restore-1115 off the hub.
2. KIT-OPS-5 + WAVE-HOLDS-1115 now: adopt KV c1 (or name the pin tree instead) and lift `*`; adopt S81 G3b,
   release the 227 keys and remove `auto_rearm` in the same commit.
3. KIT-OPS-5 before item 2 launches at volume: kit_snap and kit_self_contained agree on snapshot paths; hold
   tt_ctlm and cbn_q01 until then.
4. MERGE-QUEUE-1: kit-ops-5-typedclass-1115, kitpack-close-1115 (closed views).
5. FLOW-HEALTH-1: Event F / Event G release matching (249 S81 keys); rt sync failure removes the host from
   gen_hosts.
6. TOOLS-CONVERGE-1115: tool_skew wording, one closure, per-tick measurement of all dies.
7. HOLDGEN-1115: first deliverable is the per-tick audit (held-but-launched, release-term-unreachable).
8. KIT-OPS-5: replicate the QC treeA plan files to epyc2 or take epyc2 out of QC gen_hosts.

Not checked: which process or lane filled epyc7 (a find for files over 500 MB newer than 50 min returned
nothing in 120 s; du over the 7.3 TB disk timed out); kit_rtl.log of the snapshot-path fails; whether the
hub swings come from the cleaner or from lane deletes; failkey-1115b behaviour on a real fail; the HOLDGEN
post text; kit_snap on S81 and KV; lane-run job losses on epyc7 during the full-disk period.
