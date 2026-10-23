# Source-owned regional clock topology for the frozen one-ck TX parent.
# Use as spec.pre_cts_extra AFTER canonical clock_spine.tcl/spine_ins.tcl.
# Related clocks keep the original propagated ck and all data timing checks.
set ::ot_sp_internal_roots [dict create \
  ga [list u_sm.g_s.g_ring.u_ck_a/u_ck/Y BUFx24_ASAP7_75t_R A ck] \
  gb [list u_sm.g_s.g_ring.u_ck_b/u_ck/Y BUFx24_ASAP7_75t_R A ck]]
set ::env(OT_SPINE_PORTS) {ck,ga,gb}
set ::env(OT_SPINE_CTS_REST) 0
set ::env(OT_SPINE_MACRO_LEAF) 1
set ::env(OT_SPINE_MACRO_PIN_LEAF) 1
# The local landing-ring endpoint and hard-child INPUT clock pin are co-timed.
# ETM setup/hold and clock-to-output arcs already contain the hard child's
# timing reference. Adding the child's internal insertion to local soft FF
# clocks creates the measured y 765ps adverse skew. This changes physical
# topology only: there is no SDC latency, exception, or IO budget change.
set ::ot_ref_child_ins [dict create]
set ::ot_sp_child_ins [dict create]
puts "TX_REGIONAL_CLOCK: parent ck then kept ga/gb output-net spines; child input-pin reference"
