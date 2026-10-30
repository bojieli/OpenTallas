DIE-HEAD-33 strict die port-bind on src25m (HEAD plan of record, source_plan.json sha256 a7435da4), Thu Oct 29 06:25:52 PM PDT 2026.
RECIPE run_source_portbind.py = DIE-HEAD-30 claude/die-head-30-bind-1029 driver (head_die_portbind steps 0,2-7 on a realized source),
       tools = main ca6c3203d (incl. start_stage_emit start_d fix 552e1a1b3 and nested_check).  run.sh via ot-run (exit 0).
SOURCE intel2 die-head-33/bind/src = DIE-HEAD-31 bind source (codex-head-0830/source_realized1 = 25-type source of record adddcbdc, RTL
       incl. station realization, + the DIE-HEAD-31 start_d delta on start_stages.sv) with source_plan.json := src25m a7435da4.
       hk5m is a plan-only delta (pin/bus-order/capture geometry, 0 cycles, 0 flops) -> RTL not regenerated.  source.sha256 lists inputs.
VERDICT HEAD_DIE_PORTBIND_SOURCE PASS (CHECKED; replay in a narrowed sparse wt -> port_bind_strict.txt + nested_portbind.json byte-identical):
  module check PASS missing 0 unresolved 0
  tie audit PASS accepted 1669 rejected 0; count-strap audit PASS; pads 321 inst / 2953 spare wavefront outs
  DIE_PORT_BIND PASS masters 26 / instances 358, every error class 0 (unbound/stub/ambiguous masters, port_not_in_rtl, width, input
    unconnected/tied, unparsed, duplicate, undriven, multi-driven, unread, output_open, top_assigns, params_not_in_rtl); strap_ports 119
  PORT_BIND_NESTED PASS instances 4335, unbound 0, unknown 0, width 0, unresolved 0, no_master 0
