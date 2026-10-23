# FT-HBM die what-if probe: r18h5 place.odb with relay/landing tiles DECIMATED to <= HOP um along current routes
# (no liberty is read: setRC/set_wire_rc need liberty units and are not used by global_route)
# (tools/hbm_ft/decimate_plan.py drop list), then the same GRT probe settings as the r18h5 die case (norep, iterations 0).
# Dropped tile: every output bit net merged into its input bit net (o<-i, b<-a, ck_o<-ckf, eb<-ea); the tile is deleted.
read_db /work/place.odb
set blk [ord::get_db_block]
set t0 [clock seconds]
set pairs {o i b a ck_o ckf eb ea}
set f [open /work/drop_tiles.txt r]; set names [split [string trim [read $f]] "\n"]; close $f
set nd 0; set nm 0; set nmiss 0; set nundr 0
foreach nm_ $names {
  set inst [$blk findInst $nm_]
  if {$inst eq "NULL"} { incr nmiss; continue }
  set pin [dict create]
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL"} { continue }
    dict set pin [[$it getMTerm] getName] $n
  }
  foreach it [$inst getITerms] { if {[$it getNet] ne "NULL"} { $it disconnect } }
  dict for {mt nb} $pin {
    if {![regexp {^([a-z_]+)(\[\d+\])?$} $mt -> base idx]} { continue }
    set k [lsearch -exact $pairs $base]
    if {$k < 0 || $k % 2 != 0} { continue }
    set src "[lindex $pairs [expr {$k + 1}]]$idx"
    if {![dict exists $pin $src]} { incr nundr; continue }
    set na [dict get $pin $src]
    if {$na eq $nb} { continue }
    foreach it2 [$nb getITerms] { $it2 disconnect; $it2 connect $na }
    foreach bt [$nb getBTerms] { $bt connect $na }
    if {[llength [$nb getITerms]] == 0 && [llength [$nb getBTerms]] == 0} { odb::dbNet_destroy $nb }
    incr nm
  }
  odb::dbInst_destroy $inst
  incr nd
}
puts "OT_FT_DECIMATE dropped=$nd merged_nets=$nm missing=$nmiss undriven_outputs=$nundr secs=[expr {[clock seconds]-$t0}] insts=[llength [$blk getInsts]]"
foreach n [$blk getNets] { if {[string match dk?_* [$n getName]] || [string match n_dk?_* [$n getName]] || [string match ckg_pll_* [$n getName]]} { $n setSigType CLOCK } }
if {[$blk findNet p_host_N__pma_rck] != "NULL"} { [$blk findNet p_host_N__pma_rck] setSigType CLOCK }
set_routing_layers -signal M4-M9 -clock M7-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M7 0.146
set_global_routing_layer_adjustment M8 0.346
set_global_routing_layer_adjustment M9 0.146
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set t0 [clock seconds]
global_route -congestion_iterations 0 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {[clock seconds]-$t0}]"
write_db /work/out/grt.odb
set ::env(OT_LAYOUT_OUT) /work/out/layout_dump.json
set ::env(OT_LAYOUT_LINKS) 1
set ::env(OT_LAYOUT_TOP) "hbm r18h5 FT-HBM relay-decimated GRT"
if {[catch {source /work/layout_dump.tcl} e]} { puts "OT_LAYOUT_FAIL $e" }
if {[catch {
  set grid [$blk getGCellGrid]
  set gx [$grid getGridX]; set gy [$grid getGridY]
  set nx [llength $gx]; set ny [llength $gy]
  set sx [expr {max(1, $nx / 256)}]; set sy [expr {max(1, $ny / 192)}]
  set out [open /work/out/gcell_usage.txt w]
  puts $out "GRIDX [join $gx ,]"
  puts $out "GRIDY [join $gy ,]"
  puts $out "STRIDE $sx $sy"
  foreach ln {M4 M5 M6 M7 M8 M9} {
    set layer [[ord::get_db_tech] findLayer $ln]
    for {set j 0} {$j < $ny} {incr j $sy} {
      set row {}
      for {set i 0} {$i < $nx} {incr i $sx} { lappend row "[$grid getCapacity $layer $i $j]/[$grid getUsage $layer $i $j]" }
      puts $out "L $ln $j [join $row { }]"
    }
  }
  close $out
} e]} { puts "OT_GCELL_FAIL $e" }
puts "OT_GRT_PROBE DIAGNOSTIC FT-HBM decimated relays (not a gate)"
puts OT_DONE
