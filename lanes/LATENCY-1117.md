# LATENCY-1117: why plan events and flow fixes take hours to reach kits (LATENCY-R, 11-17 23:xx PST)

Sources (intel2): lanes/posts/*.md, lanes/COORD-REVIEW-QUEUE.md, autopilot/log.txt (TICK-TIMES, ADOPT-ROWS, ENQUEUE, LAUNCH, TOOLS-REFRESH, TOOLS-LAG),
git log of autopilot/kit_wave.json, ~/merge-queue/gates/*.json, /srv/opentallas-scratch2/claude/rt/history.log, autopilot/tools_refresh_*.log +
tools_refresh_state.json, autopilot/publish_gate/*/*.json + ~/.local/state/publish-gate/ mtimes. WORK = a process computing; WAIT = queue, tick, person, disk.

## (A) Plan events: from composed to first kit

### QC N3 (s29q103S4Q9N3), still not applied at 23:00
| step | start | end | dur | kind | evidence |
|---|---|---|---|---|---|
| plan posted -> tree (N2B _d3 + main tools) | 18:11 | 19:05 | 54m | WORK | QC-PLAN-R3 18:11, 19:05 |
| N2B gate started, then abandoned (folded into N3) | 18:34 | 19:26 | 52m | WASTED | 19:13, 19:26 |
| bind launch (ot-run plan prio, epyc2) | 19:26 | ~19:45 | 19m | WAIT | 19:26 BIND-START |
| strict bind (fresh elab: bind.py changed) | 19:45 | 20:49 | 64m | WORK | 22:33 post |
| serial chain: R8, LATCHECK, hcparam, G0, PRE, CB16 S2-S4 | 20:49 | ~22:15 | ~85m | WORK (serial) | 22:33 |
| CB16 S5_KITRTL: bind.py kit-rtl 133 types serial, one core (qualification only) | ~22:15 | ~23:10 | ~55m | WORK (serial, 1 core) | 22:33 "111/133" |
| publish + delta_apply --link on E8/E9 (started in parallel at 22:4x by hand) | 22:40 | 22:51 | 11m | WORK | 22:51 |
| publish_gate refuses: gen host intel1 scratch2 100% full (derive_gen_hosts added intel1) | 22:51 | open | >=10m | WAIT (one full host) | 22:51 BLOCKER |
| gate (G0 again ~39-48 min, then dry gen ~53 min, serial) | - | - | ~1.5h ETA | WORK (serial) | QC gate record c961ac70: static 39m + dry 53m |
| apply -> tick -> first kit | - | - | ETA 01:15 + tick | - | 22:33 ETA |
Composed-to-first-kit projected ~7 h (18:11 -> ~01:30); ~4.5 h of it after the bind finished.

### KV D21b (KV-HG6): applied 19:30, first KV launch 22:39
| step | start | end | dur | kind | evidence |
|---|---|---|---|---|---|
| D21 publish gate fails (.orig manifest drift), re-gate | 15:25 | <=19:09 | ~70m+ | REWORK | FABLE-FIX-KV-HG 15:25, 19:09 |
| apply refused x2, replicate 4 hosts, apply | 19:09 | 19:30 | 21m | WAIT/REWORK | 19:09, 19:30 |
| wave adopts tree | 19:30 | 19:36 | 7m | WAIT (tick) | AP ADOPT-ROWS 19:36:56 |
| KV wave OFF: event not in gate_events_extra | 19:36 | 21:57 | **2h21m** | WAIT (config gap) | kit_wave.json 21:57 |
| tools_refresh (replicate rc1 x3, BUSY x5) | 19:36 | 20:59 | 83m | WORK + retries | tools_refresh_qwen_kvsys.log |
| ticks of 1286-1457 s after the fix | 21:57 | 22:39 | 42m | WAIT (tick) | TICK-TIMES; LAUNCH kv3_hg_v1 22:39:35 |

### S81 D7w (event 3fa87b84b18): apply 20:59, first launch 21:08
| step | start | end | dur | kind | evidence |
|---|---|---|---|---|---|
| publish gate (static 19m, then dry gen 14m) | 20:25 | 20:59 | 34m | WORK (serial) | publish_gate/s81/263d6d57f103 |
| apply | 20:59 | 20:59 | <1m | WORK | kit_wave.json 20:59:16 |
| tree switch + adopt (tick) | 20:59 | 21:08 | 9m | WAIT (tick) | AP 21:02, 21:08 |
| first launch | 21:08 | 21:08 | <1m | WORK | AP LAUNCH col_h10_r0_p1 |
D8c: bind and die GRT protos refused 19:35-19:40 (epyc8 scratch 5.6 GB free), no restart found. D8d building since 22:28.

### HEAD NF15f (head_rp21z20NF15f)
| step | start | end | dur | kind | evidence |
|---|---|---|---|---|---|
| rs8b compose + gates | 14:50 | 15:18 | 28m | WORK | HEAD-PLAN-R4 |
| clock GEN | 15:17 | 15:23 | 6m | WORK | 15:23 |
| tree build (2 fails, then delta) | 15:29 | 15:50 | 21m | WORK+REWORK | 15:29-15:50 |
| smoke + G0 contained fix (_d1 -> _d2) | 15:50 | 16:08 | 18m | REWORK | 15:58-16:08 |
| replicate, strict bind smoke, cohort, LATCHECK | 16:08 | 16:23 | 15m | WORK | 16:23 |
| publish gate (2 runs) | 16:24 | 16:32 | 8m | WORK | publish_gate/s81_head/06dc1568 |
| gap to apply (no record) | 16:32 | 17:23 | 51m | WAIT | receipt 17:23 |
| HEAD wave OFF: event not in gate_events_extra | 17:24 | 20:26 | **3h02m** | WAIT (config gap) | kit_wave.json 20:26 |
| first launch | 20:26 | 20:37 | 11m | WAIT (tick) | AP LAUNCH hd_mesh |

## (B) Flow fixes: from commit to first kit built with them
Merge and rt sync are not the bottleneck: commit -> gate -> READY -> RULING -> merge took 6-7 min for r641, r644 and r676 (gates 2-3 min, no
admission queue; epyc2 root 0 GB refused one gate, re-routed to epyc10 at no cost); rt/current reached the hub and all hosts 1-3 min later.
Getting the fix into a die's tree is the whole delay:

| sample | merged | tools_refresh | adopt | first kit with the fix | merge -> kit | kind |
|---|---|---|---|---|---|---|
| r641 s81_head | 17:45 | 19:36-19:52 APPLIED (no pass started 17:45-19:36) | 20:20 | 20:55 hd_turn_a | 3h10m | WAIT |
| r641 QC / KV | 17:45 | QC opted out (tools_refresh false); KV BIND-FAIL "no bind recipe" | - | only via plan events N3 / D21b | 3-7 h | WAIT |
| r644 s81_head | 17:55 | same pass as r641 | 20:20 | 20:55 | 3h00m | WAIT |
| r644 s81 | 17:55 | s81 tools_refresh enabled only ~22:19; OVERLAY-PRIVATE (hard_core_built_params.json private patch) | - | none at 23:03 (off-wave H17 run 19:59) | >5h | WAIT |
| r676 s81 | 22:20 | 22:19 + 22:45 OVERLAY-PRIVATE | - | none; 22:46 s81 enqueues on the old tree repeat the VPW_BANK fail | >40m | WAIT |
| r676 s81_head | 22:20 | 22:19 COMPOSE-FAIL (intel1 replicate refused, die STOPPED until the tree changes) | - | none | open | WAIT |
TOOLS-LAG at 22:19: s81 153 commits behind (r600 on), qwen_compute/qwen_kvsys 965, s81_head 9.

Ticks: kit_wave_step+admit was 50-120 s per tick until 12:00, 150-290 s to 21:00, then 594-1367 s (ticks of 12-24 min). ADOPT -> first ENQUEUE
takes 1-2 ticks (25-35 min at 20:20).

## Top 5 causes, ranked by hours lost (11-17)
1. **Die stays OFF or inert after an apply (~5.4 h):** HEAD 3.0 h + KV 2.4 h with the event not a plan of record; no reason logged. Fixed by r662
   (apply adds gate_events_extra) and r675 (NEEDS-LANE 2 ticks after adopt); the optimistic apply below also has no label step.
2. **Fixes never reach the die trees (>=10 die-hours):** tools_refresh opt-in only (QC off, s81 on at 22:19), KV has no strict-bind recipe so every
   bind-closure change BIND-FAILs, the S81 tree carries a private tools patch (OVERLAY-PRIVATE), and any structural exit stops the die until its tree
   changes. Kits keep launching on stale tools.
3. **One full host blocks a die (~4 h across samples):** replicate/apply were all-or-nothing over gen_hosts: QC N3 blocked by intel1 at 22:51;
   KV/HEAD refreshes COMPOSE-FAIL at 19:36, 20:27, 21:02, 22:19 (epyc8/epyc10/intel1) and then STOPPED; S81 D8c bind refused (epyc8) 19:35.
4. **Serial validation chain after the bind (~3-4 h per QC event):** R8 -> LATCHECK -> hcparam -> G0 -> PRE -> CB16 (S5 kit-rtl 133 types on one
   core), then publish, then a gate that repeats G0 (39-48 min) and only then runs the dry gen (13-53 min). Gate cost per event 15-92 min.
5. **Tick latency (~0.5-1 h per event):** 12-24 min ticks since 21:00 (kit_wave_step); adopt and enqueue land on different ticks; tools_refresh
   only starts from a tick.

## Cuts
| cut | where | status |
|---|---|---|
| optimistic apply on publish: gate record, source guard, smoke advisory; no pilot hold; every type launches; label in the same write | publish_apply.py apply, apply_reviewed_tree_marker --optimistic | claude/latency-r-optimistic-1118 (gate below) |
| strict bind / LATCHECK failure holds only the types it names | publish_apply.py bind-fail | same branch |
| publish gate: static (PRE/G0) and dry gen concurrent (gate = max, not sum: saves 13-39 min) | publish_gate.run_gate | same branch |
| a gen host that cannot take the tree is dropped from gen_hosts, not a refusal / die stop | apply ensure_tree_on_hosts, tools_refresh compose | same branch |
| cancel running rows of held types (hold_records cancel_running) | kit_wave.py | sent to WAVE-FLOW-R2 |
| keep running builds + signed results of types whose plan block, bound RTL and tools digest are unchanged | kit_wave.py cancel_superseded / REKEY | sent to WAVE-FLOW-R2 |
| enqueue on the adopt tick; launch-only pass right after a kit_wave.json apply commit | kit_wave.py / FLEET-OPS-R tick split | sent to WAVE-FLOW-R2, FLEET-OPS-R |
| tools_refresh on: QC opt-in + bind recipes for QC/KV; land the S81 hard_core_built_params patch (wave-flow-r2-hcparams-1117) | config / owners | asked of COORD |
| CB16 S5 kit-rtl in a process pool (or drop it: qualification only, the gate's dry gen runs real kit-rtl) | lane chain scripts | asked of QC-PLAN-R3 |
