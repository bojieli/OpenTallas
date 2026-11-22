# FABLE-PIPELINE-R1 handoff (Fable) -- own memory across context compression

Task (OWNER via COORD 11-21 20:1x): one dependency-driven command plan -> sign-off: tools/autopilot/ot-build DIE TYPE --plan P [--tree T].
Input-hash stamps per derived artefact, staleness detection, automatic R8 refresh from bound depths, early consistency checks.
Added scope (COORD 20:3x): incremental bind -- (1) per-type bind input hash, re-bind only changed types, die checks on merged result;
(2) seconds-fast pre-check before elab (plan keys vs schema, row modules in RTL, landing depths vs station counts, taps in outline);
(3) binds on least-loaded host. Measure before/after on one real QC or KV row change.
Steps: 1 design post (DONE 20:3x), 2 land small steps via ot-push-main with tests, 3 prove e2e on one real type of a live family lane
(ask first, passing bind), 4 kit_wave wave rows use it. Report COORD <250 words at design / each landing / proven.

Peers: FLOW-PRIVSPEC-R1 (private-spec --tree/--bind-out/--rt, run-item --goal; LANDED, in rt/current), FLOW-TREEFORK-R1 (tools/fleet/ot-tree-fork, landed),
FLOW-OPS-1300 (drain, push tests).

## Landed on main
- 11fc581363: tools/die_plan/bind_emit_par.py + Binder._emit_one (OT_BIND_EMIT_J=N forked per-type emit, default serial) ; tools/autopilot/build_graph.py
- a593d9b734: tools/autopilot/ot-build, ot_build.py (bind stage + plan-overlay), ot_build_hub.py (DIE TYPE driver), tests (26)
Push recipe: scratchpad fp/ files -> scp to intel2 clone /srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/clone -> git add explicit paths, commit
(trailer Fable 5.2) -> nohup python3 -I rt/current/tools/fleet/ot-push-main > tmp/pushN.log. Tests: /srv/opentallas-scratch2/claude/mq-gate/venv/bin/python -m pytest
(the -q summary line is suppressed there: use the exit status). Local working copies: scratchpad/fp/*.py (source of truth = clone).

## Measurements (KV D27d3 sealed tree kw45/src_kv_pin_eb1e73448bd0_hg15_48b92c30_t4e46a7ec_d27d3, plan_c 48b92c30, epyc8 load ~0.65/cpu)
- BEFORE (KV-PLAN-R6 portable bind, serial, warm caches): elab ~2 min + strict bind + LATCHECK + BPC = 4567 s (76 min) total (ot-run oth-ubuntu-593030-1795318945).
- My phase-timed serial baseline (OT_BIND_GATE_CACHE=off): epyc8 kvbase/ (unit oth-ubuntu-1198688-1795321386): elab 649 s (540 s = plan_package cold),
  bind head 108 s (analyse 38, _bind_through_landings 108), regen_params 16 s, emit = the rest (running). out kvbase/out = diff -r reference.
- AFTER run 1: ot-build bind stage, same inputs, --emit-j 8: epyc8 kvob/b_55caed3292c4 (unit oth-ubuntu-1778893-1795323490, client log intel2 tmp/kvpar1.log):
  pre 34 s, elab 88 s, r8 ..., bind ... (waiters bp2igjao3 / bube5fnxa in my session; else read the logs).
- TODO after both finish: diff -r kvbase/out/rtl kvob/b_*/rtl (+ bind_report.json) = byte-identity proof of parallel emit on KV;
  then row-change run: ot-build plan-overlay + one row (kv3_io_cor_v1 reset.bank_taps or a lane station) -> time pre/adopt elab/r8/bind.

## Open
- ASK posted 21:0x to FAM-KV-IOPC-R4: use kv3_io_cor_v1 on D27d3 as the e2e proof (ot-build qwen_kvsys kv3_io_cor_v1 --lane FAM-KV-IOPC-R4); default at 22:00 = a KV type nobody has in flight.
- Hub driver untested against the real private-spec / run-item (only fake fleet): expect fixes during e2e (result.json location, --rt arg form, --goal).
- The wave config still points KV at D26 (apply of D27d3 pending by KV-PLAN-R6): for e2e pass --tree <d27d3 tree> (plan/asbuilt follow by prefix swap).
- Step B (per-type emit memo keyed on type inputs, verify mode) not started; decide after measuring J=8.
- Step 4: kit_wave uses ot-build for wave rows (bind freshness via stamps; KIT_TOPOLOGY_BIND_STALE / R8_STALE class) not started.
- R8 pre-check: no exact plan-only invariant exists (bound == lane cycles holds for 48% of KV members only); staleness is decided by the r8 node
  (bind head ~2 min KV) + stamps.
