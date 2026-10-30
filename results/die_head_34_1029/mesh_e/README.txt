DIE-HEAD-34 Thu Oct 29 19:19:27 PDT 2026: hd_mesh_e rekit (die-head-33/rekit/hd_mesh_e, src25m_cf + private raw RTL) copy, measured-view FF insertion delta
(COORD/Codex 18:59 approved: FF 342.67, TT 450 retained). Regenerated with main e4b3808d5 tools from source_plan_rekit + only hd_mesh_e
clock.insertion_ff_ps/basis; gen diff vs old kit = config.mk OT_VCLK_FF 380->342.67, constraint.sdc comment, clock_binding.json, budget.json,
pinreg_measure.tcl (main 62d8d8746 clock-family scope). RTL/synth/place identical (kept 1_*,2_*,3_*); 4_*/5_* moved to prev_fail/res; rerun from CTS.
LEC rerun in-flow (17 s; previous EQUIVALENT 1070/1070).
sdc_lint.json also from gen (FF 342.67)
