# Extracted-path probes for the routed one-PC K request slice.  This is a
# timing report, not a Liberty characterization or a chip timing claim.
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
foreach lib [list \
  $platform/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz \
  $platform/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz \
  $platform/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz \
  $platform/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  $platform/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz] {
  read_liberty $lib
}
read_db $::env(OT_KARB_PC_ODB)
read_sdc $::env(OT_KARB_PC_SDC)
read_spef $::env(OT_KARB_PC_SPEF)
set_propagated_clock [all_clocks]

foreach {label from to} {
  b_v_to_state b_v @registers
  b_addr_to_state b_addr* @registers
  b_wdata_to_state b_wdata* @registers
  k_v_to_state k_v @registers
  k_addr_to_state k_addr* @registers
  k_wdata_to_state k_wdata* @registers
  h_rdy_to_state h_rdy @registers
  h_wr_done_to_state h_wr_done @registers
  state_to_b_rdy @registers b_rdy
  state_to_k_rdy @registers k_rdy
  state_to_h_v @registers h_v
  state_to_h_addr @registers h_addr*
  state_to_h_wdata @registers h_wdata*
  state_to_h_wstrb @registers h_wstrb*
  state_to_k_grants @registers k_grants*
  b_v_to_b_rdy b_v b_rdy
  k_v_to_k_rdy k_v k_rdy
  b_we_to_b_rdy b_we b_rdy
  k_we_to_k_rdy k_we k_rdy
  h_rdy_to_b_rdy h_rdy b_rdy
  h_rdy_to_k_rdy h_rdy k_rdy
  h_wr_done_to_b_wr_done h_wr_done b_wr_done
  h_wr_done_to_k_wr_done h_wr_done k_wr_done
} {
  if {$from eq "@registers"} {set a [all_registers]} else {set a [get_ports $from]}
  if {$to eq "@registers"} {set z [all_registers]} else {set z [get_ports $to]}
  puts "\n=== $label ==="
  report_checks -from $a -to $z -path_delay max -group_count 1 -digits 4
}
