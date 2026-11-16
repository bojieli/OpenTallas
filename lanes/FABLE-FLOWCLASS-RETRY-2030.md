# FABLE-FLOWCLASS-RETRY-2030: retries on unfixed causes, classification, fail-to-fix loop

Reviewer: Fable (read-only). Measured 2026-11-15 20:19-20:58 PST on hub intel2.
Sources: autopilot/log.txt (today, 26,190 KIT-WAVE lines), kit_wave_state.json (20:24), kit_wave.json, rt/history.log,
rt/c34f6a980b1e tools/autopilot/{flow_guard.py,kit_wave.py}, FABLE-FLOW-1800.md, systemd user timers.
Method: each LAUNCH line is paired with the next FAIL or ENQUEUE line of the same item. "Pre-P&R" = fail at gen, kit_rtl,
gen_lint, kit_topology, prov_views, unit. "Reached P&R" = fail at place or ENQUEUE (place done).

## 1. Funnel today, 00:00-20:20 (wave log)

| Die | Launches | Items | Launches per item (max) | Fail before P&R | Fail at place | Past place (ENQUEUE) | Open |
|---|---|---|---|---|---|---|---|
| QC | 1038 | 111 | 9.4 (23) | 764 (74%) | 56 | 122 (12%) | 17 |
| KV | 404 | 39 | 10.4 (21) | 318 (79%) | 46 | 9 (2%) | 1 |
| S81 | 662 | 208 | 3.2 (13) | 511 (77%) | 22 | 80 (12%) | 22 |
| HEAD | 90 | 22 | 4.1 (9) | 27 (30%) | 10 | 47 (52%) | 3 |
| HBM | 0 | - | - | - | - | - | parked |
| All | 2194 | 380 | 5.8 | 1620 (74%) | 134 | 258 (12%) | 43 |

Reached P&R: 392 of 2194 (18%). Past place: 258 (12%).
18:30-20:35: S81 44 launches, 60 fails, all at gen sdc_lint, 16 items, up to 4 launches each, 0 reached P&R.
QC 30 launches, 20 fails at gen, 5 past place, 10 open. HEAD 18 launches, 11 past place, 2 stopped by signal 15.

## 2. Wasted share

- 1814 of 2194 launches (83%) are a second or later launch of an item already launched today.
- 985 of 1866 fails (53%) repeat the same (item, stage, cause). 364 of 881 keys failed 2 or more times, 21 keys 10 or more.
- By cause, repeat fails: pruned bind sources 349 (QC kit_rtl), tool/tree vintage mix 267 (KV gen), roam note read as the
  cause 72, sdc_lint 68, generator refusal 48.
- CPU cost is small (gen and kit_rtl are minutes). The real cost: the fail stream hides the first fail of each class, and
  rows whose fix landed are not told apart from rows whose cause stands.

## 3. Labels against the real cause (1866 fails)

Wave label: FLOW 1025, INFRA 735, PLAN 55, RTL 51.
- INFRA 735: host causes are 83 (11%): disk full 28, copy-back 25, signal/OOM kill 22, admission 8. The other 652 (89%)
  are deterministic: tool/tree vintage mix 292, sdc_lint refusal 116, stale child view sha 84, missing file 79,
  generator refusal 43, other 38.
- FLOW 1025: 419 pruned bind sources, 183 tool vintage mix, 214 where the quoted "decisive line" is
  `KW_ROAM kit_rtl: ran on epycN, outputs copied back` (a note, not the error; the cause is unread), 41 kit not self contained.
- Signal 15 (operator stop, plan switch) lands in the same INFRA bucket as OOM and enters the breaker count.

## 4. Why each class keeps being retried (code, rt/c34f6a980b1e)

R1. One INFRA bucket by rule. kit_wave.py RULES line 2321: any Traceback, KeyError, TypeError, AttributeError or
    "plan invalid" at gen/kit_rtl is "INFRA: tool or source skew". INFRA means own resubmit, not counted by RETRY_CAP,
    re-armed by any input change.
R2. The key check sits on the wrong path. retry-infra-key-1115 (5ff490b12ac) is merged (82b7e71d98f) and live since
    18:45. It has fired 0 times (0 INFRA-KEY-REPEAT lines, infra_posted 0). Line 8418 runs only when the row status is
    RETRY-INFRA. s81/slice_station__t17 attempt 34: infra budget spent (infra_base 31), status FAIL INFRA, infra_key
    None; it failed 18:33, 18:54, 19:33 on one plan sha and was launched again each time. The relaunch comes from the
    re-arm path (rearm_changes), not from RETRY-INFRA.
R3. Re-arm on any tool merge. rearm_changes adds reason "rt_tools" when rt_tools_digest changes. The digest covers all of
    tools/die_plan, physical/common_flow and tools/autopilot. rt/current changed 22 times between 16:00 and 20:33 (one
    per 12 min; the tick is 10 min). Every merge re-arms every failed row of every die. infra_key uses the same digest,
    so even on the RETRY-INFRA path a repeat is seen as a new key after each merge.
R4. The breaker opens now, and releases at once. Since 18:53: 8 opens, 6 releases. flow_guard.pf_kind matches the text
    "tool or source skew" (which the wave's own INFRA reason always carries) and "KIT_NOT_SELF_CONTAINED", so the class
    is marked "preflight can judge". The preflight checks paths and imports, not sdc_lint or the kit recipe; it passes;
    the class closes. S81 sdc_lint: open 18:54, "preflight passes again for all 6 held" 19:15, 16 launches 19:16-19:18,
    15 fails 19:33. KIT_NOT_SELF_CONTAINED: open/release 4 times (18:53/18:56, 19:23/19:24, 19:43/19:55, 20:22/20:24).
R5. The class key keeps the type name. norm_class masks digits and hex of 7+ only; "type slice_station__tN__clNaNc"
    stays distinct per content hash. The 18:30-20:35 S81 fails spread over 9+ keys; only "slice_station__tN" reached 10.
R6. The breaker holds only items whose LAST fail was the class. An item of the same family that has not failed yet
    still launches and must fail once. Cooldown release (30 min) frees all held items, with no single probe.
R7. Fix landed, rows not relaunched: the reverse of R3. Re-arm keys on tools digest, src_sha, src_overlay, die env,
    hosts. A fix in plan rows, an overlay, a view, or a hold lifted by hand changes none of them for a row that is
    BLOCKED or held, and nothing posts "fix X releases rows Y". QC rows waited 4.5-6.5 h for a person.
R8. Stale RETRY-INFRA: 136 rows (S81 92, HBM 20, KV 13, QC 11). HBM rows are 146 h old, S81 col rows 22-25 h. They
    count as in flight and launch when a hold lifts, whatever the cause.
R9. Routing. The wave addresses fails to kit_wave.json die_owner: DIE-S81-90, KV-101, DIE-QC-101, HEAD-98. None of the
    four has a post today. Live lanes are DIE-S81-92, KV-102, HEAD-100. 37 KIT-WAVE lines today went to a dead label.
    FLOW-GUARD alerts go to "COORD; cc KIT-OPS" (no lane of that name). infra NEEDS-LANE posts: 0.

## 5. Structural design (one mechanism, five parts)

P1. Classify at the failing stage, by who can fix it. Each stage tool exits with a typed line
    `KW_FAIL <CLASS> <stage> <key-text>`; the wave reads that line first and uses regex rules only as fallback.
    Classes: HOST (disk, OOM, docker, ssh, copy-back: retry on another host), STOPPED (signal 15, cancel, plan switch:
    no fail, no count, resume), INPUT-MISSING (file, view, pruned bind: preflight can judge), TOOL-SKEW (import,
    attribute, argument: tree against tools), TOOL-DET (lint or schema refusal, kit recipe), PLAN-DET (generator
    refusal on plan content), RTL, DESIGN (P&R result). Only HOST retries on its own. Roam and admission notes are never
    a decisive line. Delete rule 2321 as an INFRA rule.
P2. One fail key, checked at the launch gate. key = sha(kit input digest of the item, error class, masked first error
    line). Kit input digest = plan block sha + src sha + overlay + the tool files the failing stage imports (closure,
    already computed by flow_guard.closure_files), not the whole tools tree. Stored per item as `fail_key`. Every launch
    path (pick, RETRY-INFRA, re-arm, retry key, breaker release) calls one function: same key as the last non-HOST fail
    means no launch. This replaces RETRY_CAP counting, infra_seen, kill_digest and the rt_tools re-arm.
P3. Auto-relaunch on fix. The same digest gives the release: each tick, a FAIL row whose kit input digest differs from
    its fail_key digest is launched once, with a log line `RELAUNCH-ON-FIX item: changed <plan|src|overlay|tool file>`.
    A fix that changes nothing for a row leaves it stopped. No hand relaunch list, no wait for a person.
P4. Class breaker, die-wide. Count per (die, stage, class, masked line with the type/item name removed), HOST and
    STOPPED excluded. At 10 fails in 60 min the class is held for the die: no launch of an item whose family (item
    name without __cl/__pv/__t suffix) is in the class, failed or not. Release only by a probe: after a digest change
    (P3) one item per family runs; pass at that stage opens the family, fail keeps it shut. No cooldown release, no
    preflight release except for INPUT-MISSING and TOOL-SKEW, decided by class and never by reason text.
P5. Route to a live owner. Owner = newest lane with a queue post in the last 3 h among the die's lanes (from
    OWNERS.tsv plus queue.md), else COORD. One line per new fail key (not per fail): `FAIL-KEY die stage class n items
    first log owner`. Table lanes/FAIL-KEYS.tsv: key, die, class, n rows, first, last, owner, ack. No ack line from the
    owner within 30 min: post `NEEDS-LANE <key>`; COORD starts a Sonnet lane. kit_wave.json die_owner is refreshed from
    the same lookup each tick.

## 6. Built against missing

| Part | Built | Missing |
|---|---|---|
| P1 | 60+ regex rules; OOM, docker, admission, signal rules | typed KW_FAIL line; TOOL-DET/PLAN-DET/STOPPED classes; rule 2321 still INFRA; roam note as decisive line |
| P2 | infra_key (live 18:45, 0 hits), kill_digest, note_fail_sig, RETRY_CAP, "relaunch refused: inputs equal" for resumes | one key at the launch gate for all paths; digest by stage closure instead of whole tools tree |
| P3 | rearm_changes (src_sha, overlay, env, hosts, rt_tools) | plan block and view changes; narrow tool digest; release of BLOCKED rows; log line |
| P4 | flow_guard class breaker 10/h per (die, stage, class), INFRA counted since 18:45, opens | name-free key; family hold; probe release; remove text-based pf_kind; kit_wave_blocked.tsv still header only |
| P5 | grouped die line, NEEDS-LANE for design fails (2 rows), waiter_fail_relay.timer installed 20:40 | live-owner lookup; FAIL-KEYS.tsv; 30-min escalation; die_owner labels stale on 4 dies |

## 7. Owners

- FLOW-HEALTH-1 (last post 18:56; if silent, a new Sonnet lane FLOWCLASS-KEY-1115): P2, P3, P4 in kit_wave.py and
  flow_guard.py, with a replay test on today's log: S81 sdc_lint must hold after 10 fails and stay held until the plan
  sha changes; slice_station__t17 must stop at its second fail.
- KIT-OPS-5: P1 (typed KW_FAIL in gen, kit_rtl, kit_topology, sdc_lint, bind) and the kit_wave.json die_owner refresh.
- New Sonnet lane FAIL-ROUTE-1115: P5 (FAIL-KEYS.tsv, live-owner lookup, NEEDS-LANE timer); it also checks that
  waiter_fail_relay posts (4 lines so far).
- COORD today: set die_owner to DIE-S81-92, KV-102, HEAD-100 and the live QC lane.

## 8. Stop list (now, by config, before the code lands)

1. S81 gen sdc_lint (slice_station*, serdes*): hold by family until the plan clock tap window changes (G1d / Event F).
   60 fails in the last 2 h, 0 passes; item attempts up to 37.
2. QC gen KIT_NOT_SELF_CONTAINED (slw_st_a_v2__cl9f076a5c and class): 41 fails today, 12 in the last 2 h.
3. QC gen "hard landing actual child proof failed" (5 in 2 h, breaker open 20:22, kind "skew" so it will release).
4. KV: keep the die hold until one kit builds on the rebuilt tree (KV-102).
5. No relaunch on rt_tools change alone: set the re-arm off for reason rt_tools until P2 lands.
6. Do not release a FLOW-GUARD class on "preflight passes" for sdc_lint, kit recipe or generator refusals.
7. Reap the 136 RETRY-INFRA rows older than 6 h to FAIL with their real class (R3 rule exists for spent budgets).
