# Generated declared-clock continuity only: no net/instance/placement mutation.
proc ot_cland_export_check_one {where dst_name src_name inst_name master_name} {
  set block [ord::get_db_block]
  set dst [$block findBTerm $dst_name]
  set src [$block findBTerm $src_name]
  set inst [$block findInst $inst_name]
  if {$dst eq "NULL" || $src eq "NULL" || $inst eq "NULL"} {
    error "OT_CLAND_EXPORT_OPEN $where $dst_name: declared endpoint/driver missing"
  }
  if {[[$inst getMaster] getName] ne $master_name} {
    error "OT_CLAND_EXPORT_OPEN $where $dst_name: declared driver master changed"
  }
  set a [$inst findITerm A]; set y [$inst findITerm Y]
  if {$a eq "NULL" || $y eq "NULL" || [$a getNet] eq "NULL" || [$y getNet] eq "NULL"} {
    error "OT_CLAND_EXPORT_OPEN $where $dst_name: driver A/Y disconnected"
  }
  if {[$src getNet] eq "NULL" || [$dst getNet] ne [$y getNet]} {
    error "OT_CLAND_EXPORT_OPEN $where $dst_name: declared source/output net missing"
  }
  set ap [get_pins -quiet [list ${inst_name}/A]]
  if {[llength $ap] != 1} { error "OT_CLAND_EXPORT_OPEN $where $dst_name: A timing pin missing" }
  set roots {}
  foreach p [get_fanin -to $ap -flat -startpoints_only -trace_arcs all] {
    lappend roots [get_full_name $p]
  }
  set roots [lsort -unique $roots]
  if {$roots ne [list $src_name]} {
    error "OT_CLAND_EXPORT_OPEN $where $dst_name: root $roots != declared $src_name"
  }
  puts "OT_CLAND_EXPORT_CONNECTED $where $dst_name <- $src_name via $inst_name"
  return 1
}
proc ot_cland_export_require_continuity {where} {
  set count 0
  foreach row $::ot_cland_export_links {
    incr count [ot_cland_export_check_one $where {*}$row]
  }
  puts "OT_CLAND_EXPORT_BOUND $where links=$count open=0"
  return $count
}
set ::ot_cland_export_links [list]
lappend ::ot_cland_export_links [list {fclk_out_ad_o} {clk_t4} {cland_fwd_fclk_out_ad_o} {BUFx24_ASAP7_75t_R}]
lappend ::ot_cland_export_links [list {fclk_out_au_o} {clk_t8} {cland_fwd_fclk_out_au_o} {BUFx24_ASAP7_75t_R}]
lappend ::ot_cland_export_links [list {fclk_out_bd_o} {clk_t2} {cland_fwd_fclk_out_bd_o} {BUFx24_ASAP7_75t_R}]
lappend ::ot_cland_export_links [list {fclk_out_bu_o} {clk_t8} {cland_fwd_fclk_out_bu_o} {BUFx24_ASAP7_75t_R}]
lappend ::ot_cland_export_links [list {fclk_out_h_rx_ft_o} {clk_t8} {cland_fwd_fclk_out_h_rx_ft_o} {BUFx24_ASAP7_75t_R}]
