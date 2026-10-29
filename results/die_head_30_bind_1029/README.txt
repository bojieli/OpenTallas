DIE-HEAD-30 Thu Oct 29 11:49:59 AM PDT 2026 head_die_portbind END-TO-END on hk5 source_realized1 (COORD condition on the DIE-HEAD-28 closure patch).
Results + one driver only; no tool change.
RUN   run_source_portbind.py (= head_die_portbind.py steps 0,2-7 with gen.py replaced by the realized source copy; prepare step
      = Codex codex-head-ca-0840/prepare_source_bind.py logic, path-parametric) on intel2, tools = main 88b244ad39 (incl. the
      DIE-HEAD-29 nested_check fix 49ab4269f), SRC = intel2 codex-head-0830/source_realized1, ot-run unit
      oth-ubuntu-759702-1793299616 (exit 1 = verdict FAIL, run complete), log sr1/run.log.
      Prepared pads.json / straps.json / s81_head_top_nonansi.sv byte-identical to DIE-HEAD-28 source3 (CHECKED);
      die_sha256 cf37500c... same as source7_bind.
VERDICT HEAD_DIE_PORTBIND_SOURCE FAIL (CHECKED), only on step 7:
  0 module check PASS missing 0 unresolved 0
  6 tie audit PASS accepted 1669 rejected 0; count-strap audit PASS; pads 321 inst / 2953 spare wavefront outs
  4 manifest 112 entries, landing closure ot_dp_clk_landing.sv + ot_dp_clk_landing_ca.sv + ot_meso_fifo.sv
  5 DIE_PORT_BIND PASS masters 26 / instances 358, every error counter 0, strap_ports 119, spare_out_bits 2953
  7 nested (tools/s81_head/head_source_nested_check.py, main port_bind_gate) FAIL 4335 instances: unbound 1, unknown 0,
    width 0, unresolved 0, no_master 0.  The 1 = ot_die_start_stages.u_st_b0 (ot_dp_landing_root).start_d: the START root
    FSTART D-side OUTPUT (DIE-HEAD-10) is left open in start_stages.sv (start_stage_emit); nothing reads it.
    DIE-HEAD-29 PASS 3084 walked the ot_s81hd_* wrappers only; the main tool also walks start_stages.sv + ot_dp_cells.sv.
    An open unused output loses no logic, but the rule (every master port bound) fails it as designed.
    FIX (DEFAULT, START source owner): start_stage_emit binds .start_d to a named spare wire declared like the 2953
    rst_o_/start_o_ spares (or emits a root variant without start_d where no FSTART consumer exists); no nested exemption.
