# FABLE-PIPELINE-R1 handoff (Fable) -- own memory across context compression

Task (OWNER via COORD 11-21 20:1x): one dependency-driven command plan -> sign-off: tools/autopilot/ot-build DIE TYPE --plan P [--tree T].
Input-hash stamps per derived artefact, staleness detection, automatic R8 refresh from bound depths, early consistency checks.
Added scope (COORD 20:3x): incremental bind -- (1) per-type bind input hash, re-bind only changed types, die checks on merged result;
(2) seconds-fast pre-check before elab (plan keys vs schema, row modules in RTL, landing depths vs station counts, taps in outline);
(3) binds on least-loaded host. Measure before/after on one real QC or KV row change.
Steps: 1 design post, 2 land small steps via ot-push-main with tests, 3 prove e2e on one real type of a live family lane (ask first,
passing bind), 4 kit_wave wave rows use it. Report COORD <250 words at design / each landing / proven.

Peers (do not duplicate): FLOW-PRIVSPEC-R1 = private-spec --tree bind/rt, env provenance, run-item --goal (commit 52bcb72f66, check landed);
FLOW-TREEFORK-R1 = tools/fleet/ot-tree-fork + private-spec --fork; FLOW-OPS-1300 = drain filter, push tests.

## State
- Clone: intel2:/srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/clone (cone tools, physical/die_plan), main cd2cd11c4e at start. tmp: ../tmp
- START posted 20:2x (coord ca0148b23c).
- BASELINE running: ot-run unit oth-ubuntu-1198688-1795321386 on epyc8, script epyc8:/srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/kvbase/base.sh
  (phase-timed elab + strict bind + LATCHECK of sealed KV D27d3 tree kw45/src_kv_pin_eb1e73448bd0_hg15_48b92c30_t4e46a7ec_d27d3, out kvbase/out,
  phases kvbase/ph_elab|ph_bind/bind_phases.json, OT_BIND_GATE_CACHE=off). Client log intel2 .../FABLE-PIPELINE-R1/tmp/kvbase.log.

## Findings so far
- Existing pieces on main: tools/die_plan/bind_fast.py (host / precheck / r8 / kits / phases), plan_gate_pre.py (SCHEMA INPUT TOOLS ROWS GEOM),
  bind_rowcheck.py (FIXEDCYC ROWSINK MODULES TOOLSTALE), r8_refresh.py + land_r8_derive.py, rt_pin.py, kit_topology.py, kit_wave private-spec/run-item.
  Nobody chains them: plan lanes hand-write apply_*.sh per event (see intel2 ~/tmp/kvplanr6/apply_d27d3_e8.sh).
- KV D27d3: elab ~2 min, strict bind >37 min on epyc8 (load 0.69/cpu); bindgate on loaded epyc7 2 h 7 min. Bind (Binder.emit per type) is the pole, not elab.
- bind_fast host: only epyc8 had the KV tree among least-loaded hosts -> locality (tree on few hosts) forces loaded hosts.

## Next
- read bind_phases of baseline; design post; code build_graph.py (stamps) + ot-build.
