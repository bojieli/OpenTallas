# BF SAFE variant B (ot_s81_bf_native HALF=1, 2026-10-07): the element and the pin-capture registers run on eclk = clk
# gated every other cycle (u_hcg latch + AND, enable ph toggling), so every one of them launches and captures only on
# gated edges: paths among them (and into the element's own clock-gate enables) get two clk periods, multicycle
# setup 2 / hold 1.  Crossings stay single cycle: pins -> pin regs, element -> o_* output regs (clk), element ->
# g_pin.r_busy / r_fault (clk), ph -> u_hcg.  Read by the route SDC (run_bf_native_physical.py --half) and again after
# signoff_ref.sdc at sign-off (corner_sta --post-sdc).  The verdict check greps OT_BF_HALF in the sign-off log.
# bf-insertion 2026-10-08: patterns *u_elem.* -- since RECUT (260869fd0) the element is g_orig.u_elem / g_rc.u_elem, and
# {u_elem.*} matched none of it: halfphl routes got MC 2/1 on the 1,622 g_pin regs only (93,415 regs + 2,593 ICG/ROM
# expected), so 4,133 element paths were repaired/judged single-cycle (-192.5 at 730, all two-cycle paths).
# Wrapped in catch: a clock-period probe that reads the SDC without a linked design must not fail.
if {[catch {
  set ot_h {}
  foreach ot_c [all_registers] {
    set ot_n [get_full_name $ot_c]
    if {([string match {*u_elem.*} $ot_n] || [string match {g_pin.r_*} $ot_n]) &&
        ![string match {g_pin.r_busy*} $ot_n] && ![string match {g_pin.r_fault*} $ot_n]} { lappend ot_h $ot_c }
  }
  set ot_hn [llength $ot_h]
  foreach ot_c [get_cells -quiet {*u_elem.*u_icg* *u_elem.*u_rom?}] { lappend ot_h $ot_c }
  if {$ot_hn > 0} {
    set_multicycle_path -setup 2 -from $ot_h -to $ot_h
    set_multicycle_path -hold 1 -from $ot_h -to $ot_h
    puts "OT_BF_HALF multicycle on $ot_hn registers + [expr {[llength $ot_h] - $ot_hn}] ICG/ROM cells"
  } else {
    puts "OT_BF_HALF WARNING no element registers matched u_elem.* / g_pin.r_* (expected only before synthesis)"
  }
} ot_err]} { puts "OT_BF_HALF WARNING not applied: $ot_err" }
