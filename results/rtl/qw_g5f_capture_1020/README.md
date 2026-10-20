# First-edge fault capture source receipt (STOP handoff)

Branch codex/qw-g5f-fault-1020: source5259e4c1a + bench740c71dc3. Source only, opt-in --early-sticky; legacy qfd_fault_or and defaults unchanged. Actual clock/reset grouping retained. No GEN adoption, physical source qualification or actual STATUS sink exists.

Fleet ep6 unit oth-ubuntu-3209177-1792509072 terminal exit0. Verilator5.050 nominal PASS133checks covers all16 bit inputs pulsing on first/second real reset-release edges, N1/N16, sticky hold, later pulse and repeated reset/rearm. Delayed-capture and nonsticky mutants both fail first_two_edge_pulse_retained. Committed run.sh/source.json pin exact artifacts.

Model: N+4 flops; actual group rs directly controls N sticky inputs +2 release flops, <=18 raw endpoints; rl[1] controls only2; clock <=20 raw endpoints. Actual mapped census, asynchronous reset release suitability, native placement/pins/reach, full STATUS calendar, landed transport and real obs_fault sink/view are OPEN. The distinct capture uses existing group rs, never a fabricated global reset. No roots from different clock/reset groups are ORed together.

The last attempted actual-g5 proposal regeneration refused an absolute source path physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv lacking local/source-prefix authority. Fail-closed; no regenerated early proposal is claimed. Original frozen g5 legacy proposal remains unchanged. Current inventory remains425ports/498bits/340clock-reset groups/344nodes/1874FF model, pending actual opt-in regeneration. CLAUDE IS BACK STOP: no additional launch or source edit performed.
