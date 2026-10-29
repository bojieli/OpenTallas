DIE-HEAD-31 Thu Oct 29 02:19:27 PM PDT 2026 nested port-bind re-run on the DIE-HEAD-30 hk5 source_realized1 bind (0a054fa865).
FIX   tools/die_plan/start_stage_emit.py @552e1a1b3: root stage binds ot_dp_landing_root.start_d (driven OUTPUT, FSTART
      D-side) to its own declared net st_<id>_start_d; no tie, no constant, no exemption, no logic/cycle change.
REPLAY the realized source's start_stages.sv was produced by the Codex realize pipeline (root rst_raw_n renamed to
      wrst_sp3__rst_start_raw_22), so it is not re-emittable from main inputs; the emitter's exact delta (1 wire decl +
      1 port binding, start_stages.delta.diff) was applied to a copy of die-head-30-bind/sr1/source on intel2
      (/srv/opentallas-scratch2/claude/die-head-31/bind); every other file byte-identical (diff -rq), manifest identical
      up to the copy path.  The next regenerated START source (hk5l on the 25-type source) gets it from the tool.
RUN   tools/s81_head/head_source_nested_check.py (main port_bind_gate.nested_check, tools @552e1a1b3) in docker -m 8g.
VERDICT PORT_BIND_NESTED PASS instances 4335, unbound 0 (was 1), unknown 0, width 0, unresolved 0, no_master 0 (CHECKED).
      Steps 0-6 of 0a054fa865 unchanged (DIE_PORT_BIND PASS 26 masters/358 inst; start_stages.sv is inside the wrapper scope).
