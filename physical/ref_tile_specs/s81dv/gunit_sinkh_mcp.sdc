# S81U-GUNIT2 (2026-10-17) dsdv_gunit_l5: the exact HC tail's Sinkhorn (u_tail/u_sinkh = ot_hdc_sinkhorn, unchanged, one
# whole normalisation per unit edge, 6.58 ns routed TT) is clocked through an integrated clock gate of the stream clock
# (u_tail/u_gate = ot_hdc_cg, ICGx1) enabled one core edge in SK = 9 (rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_tail.sv).
# Every register of the unit therefore captures only on an enabled edge, and every value it captures (its own state,
# the tail's t[8..23] exp results, sink_launch) is stable for >= SK core cycles before that edge: a designed SK-cycle
# path.  Paths OUT of the unit (y -> final_result, out_valid / fault) are ordinary single-cycle paths and stay timed;
# the gate enable (divider -> ICG) is a single-cycle clock-gating check and stays timed.  One clock, no generated clock.
set ot_gu_sk 9
set ot_gu_sk_regs {}
foreach ot_gu_c [all_registers -cells] {
    if {[string match "*u_sinkh*" [get_full_name $ot_gu_c]]} { lappend ot_gu_sk_regs $ot_gu_c }
}
if {[llength $ot_gu_sk_regs] > 0} {
    set_multicycle_path -setup $ot_gu_sk -to $ot_gu_sk_regs
    set_multicycle_path -hold [expr {$ot_gu_sk - 1}] -to $ot_gu_sk_regs
}
