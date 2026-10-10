# io_min_vcut8.sdc (hbm-phys vm8 2026-10-10): FF hold credit of the connected die path for every VM8 vertical-cut half -- the
# approved spine recipe (spine_io_min.py / stations stn_io_min.py, coordinator decision 2026-10-06; io_min_hfd_vm.sdc for the
# 4-tile VM) restricted to its lower bound: every data input is launched by the neighbour's pin register (vcut8 seams: the
# other half's ot_hfd_oreg pin flops, abutted; die faces: the neighbour views' pin-launch flops), so its earliest arrival is
# at least that flop's FF clk->Q, 32.2 ps (CLKQ_FF_PS), plus a wire >= 0 (taken as 0 here; the die model's gaps are larger).
# Outputs keep -min 0 (credit_out = wire >= 0, taken as 0).  Read after vclk_corner_true.sdc, FF session only.
if {[llength [get_libs -quiet *_FF_*]] && [llength [get_clocks -quiet vclk]]} {
  set ot_iom_n 0
  foreach ot_q [all_inputs -no_clocks] {
    set ot_qn [get_full_name $ot_q]
    if {[regexp {^(ck[wens]?[0-9]*|rst|por)(\[0\])?$} $ot_qn]} { continue }
    set ot_d [expr {[llength [info procs ot_port_dir]] ? [ot_port_dir $ot_q] : "input"}]
    if {$ot_d in {input bidirect}} { set_input_delay -min 32.2 -clock vclk $ot_q; incr ot_iom_n }
  }
  puts "OT_IOMIN vcut8: clk->Q die-path hold credit 32.2 ps on $ot_iom_n input ports"
}
