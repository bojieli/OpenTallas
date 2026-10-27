# Full placed register/async/output reach census; read-only. Macro endpoints use
# actual MTerm pin geometry, not the hard macro's centre. No timing exceptions.
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} {read_liberty $L/$f}
foreach f [glob /work/macros/*_tt.lib] {read_liberty $f}
read_db $::env(ODB)
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set locs {}
proc pxy {p} {
  global block dbu locs
  set name [get_full_name $p]
  if {[dict exists $locs $name]} {return [dict get $locs $name]}
  set it "NULL"
  catch {set it [sta::sta_to_db_pin $p]}
  set i "NULL"
  if {$it ne "NULL" && $it ne ""} { catch {set i [$it getInst]} }
  if {$i ne "NULL" && $i ne ""} {
    if {[[$i getMaster] isBlock]} {
      lassign [$it getAvgXY] ok x y
      if {!$ok} {error "macro pin has no physical shape: $name"}
      set ans [list [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
    } else {
      set bb [$i getBBox]
      set ans [list [expr {([$bb xMin]+[$bb xMax])/(2.0*$dbu)}] [expr {([$bb yMin]+[$bb yMax])/(2.0*$dbu)}]]
    }
  } else {
    set bt [$block findBTerm $name]
    if {$bt eq "NULL"} {error "no DB endpoint for $name"}
    set bb [$bt getBBox]
    set ans [list [expr {([$bb xMin]+[$bb xMax])/(2.0*$dbu)}] [expr {([$bb yMin]+[$bb yMax])/(2.0*$dbu)}]]
  }
  dict set locs $name $ans
  return $ans
}
set out $::env(OUT)
file mkdir $out
set fh [open $out/hops.tsv w]
set allh ""
if {[info exists ::env(OT_REACH_ALL)] && $::env(OT_REACH_ALL) eq "1"} {set allh [open $out/all_arcs.tsv w]}
set endpoints [concat [all_registers -data_pins] [all_registers -async_pins] [all_outputs]]
set count 0; set arcs 0; set maxhop 0; set over 0
foreach d $endpoints {
  lassign [pxy $d] dx dy
  set best 0; set bs ""; set bx 0; set by 0
  foreach s [get_fanin -to $d -flat -startpoints_only -trace_arcs all] {
    lassign [pxy $s] sx sy
    incr arcs
    set dist [expr {abs($sx-$dx)+abs($sy-$dy)}]
    if {$allh ne ""} {puts $allh "[get_full_name $d]\t$dx\t$dy\t$dist\t[get_full_name $s]\t$sx\t$sy"}
    if {$dist>$best} {set best $dist;set bs [get_full_name $s];set bx $sx;set by $sy}
  }
  if {$best>$maxhop} {set maxhop $best}
  if {$best>405} {incr over}
  incr count
  puts $fh "[get_full_name $d]\t$dx\t$dy\t$best\t$bs\t$bx\t$by"
}
close $fh
if {$allh ne ""} {close $allh}
set fh [open $out/summary.txt w]
puts $fh "endpoints $count arcs $arcs max_manhattan_um $maxhop endpoints_over405 $over"
close $fh
set fh [open $out/cells.tsv w]
foreach i [$block getInsts] {
 set bb [$i getBBox]
 puts $fh "[$i getName]\t[[$i getMaster] getName]\t[expr {[$bb xMin]/double($dbu)}]\t[expr {[$bb yMin]/double($dbu)}]\t[expr {[$bb xMax]/double($dbu)}]\t[expr {[$bb yMax]/double($dbu)}]\t[$i getPlacementStatus]"
}
close $fh
puts "SYS_C_REACH endpoints $count arcs $arcs max_um $maxhop over405 $over"
