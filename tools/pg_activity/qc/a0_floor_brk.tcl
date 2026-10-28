# QC-PG-4: floor breakdown of the A0 NK parent (activity 0, clock running) + ICG probe cells
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain $::env(OT_MACROS)/*_tt.lib] { read_liberty $f }
read_db $::env(OT_ODB)
read_sdc $::env(OT_SDC)
source $::env(OT_RC)
set block [ord::get_db_block]
set db [ord::get_db]
# ICG probes: x1/x2/x4 on the root net ck, EN static 0, GCLK unloaded
set cknet [$block findNet ck]
foreach m {ICGx1_ASAP7_75t_R ICGx2_ASAP7_75t_R ICGx4_ASAP7_75t_R ICGx8DC_ASAP7_75t_R} {
  set i [odb::dbInst_create $block [$db findMaster $m] probe_$m]
  [$i findITerm CLK] connect $cknet
  set en [odb::dbNet_create $block probe_en_$m]
  [$i findITerm ENA] connect $en
}
estimate_parasitics -placement; set_propagated_clock [all_clocks]
foreach r [all_registers] { foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity 0 -duty 0.5 } }
foreach p [all_inputs -no_clocks] { set_power_activity -input_ports $p -activity 0 -duty 0.5 }
foreach m {ICGx1_ASAP7_75t_R ICGx2_ASAP7_75t_R ICGx4_ASAP7_75t_R ICGx8DC_ASAP7_75t_R} { catch {set_power_activity -pins [get_pins probe_$m/ENA] -activity 0 -duty 0} }
report_power -digits 6
foreach m {ICGx1_ASAP7_75t_R ICGx2_ASAP7_75t_R ICGx4_ASAP7_75t_R ICGx8DC_ASAP7_75t_R} { puts "PROBE $m"; report_power -instances [get_cells probe_$m] -digits 8 }
# face regs vs other regs: sum instance power
set fpat {tap_q|tile_id_q|n_a_q|n_b_q|t_out_q|n_y_q|fy_q|mis_q}
set face {}; set oth {}
foreach r [all_registers -cells] { set n [get_full_name $r]; if {[regexp {^u_g/(tap_q|tile_id_q|n_a_q|n_b_q|t_out_q|n_y_q|fy_q|mis_q)} $n] || [regexp {^(u_g\.)?(tap_q|tile_id_q|n_a_q|n_b_q|t_out_q|n_y_q|fy_q|mis_q)} $n]} { lappend face $r } else { lappend oth $r } }
puts "NFACE [llength $face] NOTHER [llength $oth]"
puts "SAMPLE_FACE [lrange [lmap c [lrange $face 0 3] {get_full_name $c}] 0 3]"
puts "SAMPLE_OTH [lmap c [lrange $oth 0 5] {get_full_name $c}]"
report_power -instances $face -digits 8 > $::env(OT_OUT).face.pw
report_power -instances $oth -digits 8 > $::env(OT_OUT).oth.pw
set mac {}; foreach c [get_cells *] { if {[regexp {lsl|node|romleaf} [get_property $c ref_name]]} { lappend mac $c } }
puts "NMACRO [llength $mac]"; report_power -instances $mac -digits 8 > $::env(OT_OUT).mac.pw
# clock tree buffers and their levels
set lv {}
proc walk {net lvl} {
  global lvcnt lvbuf
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    set inst [$it getInst]; set mn [[$inst getMaster] getName]
    if {[regexp {^(BUF|INV|CKINV|HB)} $mn]} {
      lappend lvbuf($lvl) [$inst getName]
      foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { walk [$o getNet] [expr {$lvl+1}] } }
    } else { incr lvcnt($lvl) }
  }
}
array set lvcnt {}; array set lvbuf {}
walk $cknet 0
foreach l [lsort -integer [array names lvbuf]] {
  report_power -instances [get_cells $lvbuf($l)] -digits 8 > $::env(OT_OUT).lvl$l.pw
  puts "LEVEL $l nbuf [llength $lvbuf($l)] sinks_here [expr {[info exists lvcnt($l)] ? $lvcnt($l) : 0}]"
}
foreach l [lsort -integer [array names lvcnt]] { puts "SINKLEVEL $l $lvcnt($l)" }
