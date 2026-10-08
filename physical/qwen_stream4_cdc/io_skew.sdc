# MARGIN (owner rule 2026-10-06) die context for ot_qwen_stream4_cdc_pc, one clock domain at a time: each boundary delay
# is referenced to the propagated arrival L at a register of the block's own tree in that domain, keeps the 0.2 T outside
# budget, and budgets an adverse die clock-arrival difference of OT_IO_SKEW ps (default 150):
#   input  max = 0.2 T + L_max + sk     input  min = L_min - sk
#   output max = 0.2 T - L_max + sk     output min = -L_min - sk
# Single-corner exact (one scalar arrival per run, as io_lat.sdc); post-CTS only.
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
# hold side (coordinator decision 2026-10-06): a 50 ps die-clock IO hold allowance (OT_IO_HOLD_SKEW), not the setup skew
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk ins outs} {
  clk  {l_pop w_v w_sec* w_data* w_tag*} {l_v l_sec* l_row* l_data* w_room wd_v wd_tag* c_fault}
  hclk {h_lv h_lsec* h_lrow* h_ldata* h_hand h_wcon h_av h_atag*} {h_cred* h_wv h_wsec* h_cv h_csec* h_cdata* h_ctag* h_fault}
} {
  set ref [lindex [all_registers -clock $clk -clock_pins] 0]
  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
  set T [get_property [get_clocks $clk] period]
  puts "OT_IO_SKEW $clk ref [get_full_name $ref] L max $lmax min $lmin skew $ot_sk"
  set_input_delay  [expr {0.2*$T + $lmax + $ot_sk}] -max -clock $clk [get_ports $ins]
  set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]          -min -clock $clk [get_ports $ins]
  set_output_delay [expr {0.2*$T - $lmax + $ot_sk}] -max -clock $clk [get_ports $outs]
  set_output_delay [expr {-$lmin - $ot_hk}]         -min -clock $clk [get_ports $outs]
}

# the raw reset epoch: asynchronous assertion, released through the element's own synchronizers (async assert false-path)
set_false_path -from [get_ports {c_arst_n h_arst_n}]
