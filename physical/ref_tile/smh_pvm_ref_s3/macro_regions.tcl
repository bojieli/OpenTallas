# Source-bound macro endpoint regions. One legal north row band remains intact.
# OpenDB EXCLUSIVE is DEF FENCE: https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/dbTypes.h
# Dynamic STA traversal binds cells by actual connectivity, never a stale cell-name list.
foreach pin {TIEHIx1_ASAP7_75t_R/H TIELOx1_ASAP7_75t_R/L} {repair_tie_fanout -separation 1 -max_fanout 1 $pin}
set pb [ord::get_db_block]
set pdu [[ord::get_db_tech] getDbUnitsPerMicron]
set pindex [dict create]
foreach pi [$pb getInsts] {
 regsub -all {\\} [$pi getName] {} pn
 if {[dict exists $pindex $pn]} {error "PVM_REGION ambiguous instance $pn"}
 dict set pindex $pn $pi
}
proc pvm_region_inst {sta_name} {
 global pindex
 if {![dict exists $pindex $sta_name]} {error "PVM_REGION missing exact STA/DB instance $sta_name"}
 return [dict get $pindex $sta_name]
}
set pboundary [dict create]
set pports [dict create]
foreach pp [get_ports *] {
 set pn [get_full_name $pp]
 if {$pn in {clk rst_n}} continue
 set dir [get_property $pp direction]
 if {$dir in {power ground}} {
  set bt [$pb findBTerm $pn]
  if {$bt eq "NULL" || [$bt getSigType] ni {POWER GROUND}} {error "PVM_REGION inconsistent power port $pn:$dir"}
  continue
 }
 if {$dir eq "input"} {set ends [get_fanout -from $pp -flat -endpoints_only]} elseif {$dir eq "output"} {set ends [get_fanin -to $pp -flat -startpoints_only]} else {error "PVM_REGION unsupported port direction $pn:$dir"}
 foreach ep $ends {
  foreach pc [get_cells -of_objects $ep] {
   set cn [get_full_name $pc]
   dict set pboundary $cn 1
   dict lappend pports $cn $pn
  }
 }
}
set pmacros {}
foreach pi [$pb getInsts] {if {[[$pi getMaster] isBlock]} {lappend pmacros $pi}}
if {[llength $pmacros]!=1} {error "PVM_REGION expected actual one SRAM"}
set pm [lindex $pmacros 0]
if {[[$pm getMaster] getName] ne "ot_sram_1r1w_64x512_m1_r2c2_p192_mir"} {error "PVM_REGION wrong macro identity"}
set pmn [$pm getName]
regsub -all {\\} $pmn {} psta_mn
set pmc [get_cells -quiet $psta_mn]
if {[llength $pmc]!=1} {error "PVM_REGION macro namespace not unique"}
set pcritical [dict create]
set pio [dict create]
foreach pp [get_pins -of_objects $pmc] {
 set pn [lindex [split [get_full_name $pp] /] end]
 if {[regexp {^(wd_in|w_addr_in|w_ce_in|r_addr_in)} $pn]} {set cone [get_fanin -to $pp -flat]} elseif {[string match {rd_out*} $pn]} {set cone [get_fanout -from $pp -flat]} else {continue}
 foreach cp $cone {
  foreach pc [get_cells -of_objects $cp] {
   set cn [get_full_name $pc]
   if {$cn eq $psta_mn} continue
   if {[dict exists $pboundary $cn]} {dict set pio $cn [dict get $pports $cn]} else {dict set pcritical $cn [pvm_region_inst $cn]}
  }
 }
}
# Coherent declared input ranges cover every actual boundary register on a macro cone.
set pf [open /work/pvm_region_boundary.tsv w]
puts $pf "cell\tports"
set pactual [dict create]
dict for {cn ports} $pio {
 puts $pf "$cn\t[join $ports ,]"
 foreach port $ports {regsub {\[[0-9]+\]$} $port {} base;dict set pactual $base 1}
}
close $pf
puts "PVM_REGION ACTUAL_BOUNDARY_PORTS=[lsort [dict keys $pactual]] count=[dict size $pio]"
set expected_ports {ev fold_a fold_start pub_slot pub_start sum tag_d}
set seen [dict create]
dict for {cn ports} $pio {
 foreach p $ports {
  regsub {\[[0-9]+\]$} $p {} base
  if {$base ni $expected_ports} {error "PVM_REGION unmodeled macro-cone boundary port $p"}
  dict set seen $base 1
 }
}
if {[lsort [dict keys $seen]] ne [lsort $expected_ports]} {error "PVM_REGION macro boundary set changed"}
set pa 0.0
dict for {cn pi} $pcritical {
 set mm [$pi getMaster]
 if {[$mm isBlock]} {error "PVM_REGION extra hard child in functional cone"}
 set pa [expr {$pa+double([$mm getWidth])*[$mm getHeight]/$pdu/$pdu}]
}
set ph [expr {ceil($pa/(172.8*0.45)/0.27)*0.27}]
if {$ph<=0 || $ph>45.0} {error "PVM_REGION unmodeled cone area $pa / height $ph"}
set ptop [expr {230.04+$ph}]
if {$ptop>300.24} {error "PVM_REGION cone region outside sole north band"}
proc pvm_make_region {name coords cells} {
 global pb pdu
 if {[$pb findRegion $name] ne "NULL"} {error "PVM_REGION duplicate region $name"}
 set rg [odb::dbRegion_create $pb $name]
 $rg setRegionType EXCLUSIVE
 lassign $coords x0 y0 x1 y1
 odb::dbBox_create $rg [expr {round($x0*$pdu)}] [expr {round($y0*$pdu)}] [expr {round($x1*$pdu)}] [expr {round($y1*$pdu)}]
 set grp [odb::dbGroup_create $pb $name]
 $grp setType PHYSICAL_CLUSTER
 $rg addGroup $grp
 foreach ci $cells {$rg addInst $ci;$grp addInst $ci}
 puts "PVM_REGION $name count=[llength $cells] box=$coords"
}
pvm_make_region pvm_macro_cone [list 86.4 230.04 259.2 $ptop] [dict values $pcritical]
# Standard per-sink tie repair preserves the actual constant sink/value graph.
set pties [dict create]
set nw 0
foreach it [$pm getITerms] {
 set pn [[$it getMTerm] getName]
 if {![regexp {^(w_mask_in|rr_en|rr_addr|cr_en|cr_sel)} $pn]} continue
 # All these exact constant ports lie on the W face after whole-macro R180.
 set nn [$it getNet]
 if {$nn eq "NULL"} {error "PVM_REGION undriven constant $pn"}
 set ds {}
 set nl 0
 foreach jt [$nn getITerms] {
  if {[[$jt getMTerm] getIoType] eq "OUTPUT"} {lappend ds [$jt getInst]}
  if {[[$jt getMTerm] getIoType] eq "INPUT"} {incr nl}
 }
 if {[llength $ds]!=1 || $nl!=1} {error "PVM_REGION constant $pn lacks one actual local driver"}
 set ti [lindex $ds 0]
 set want [expr {[string match {w_mask_in*} $pn] ? "TIEHIx1_ASAP7_75t_R" : "TIELOx1_ASAP7_75t_R"}]
 if {[[$ti getMaster] getName] ne $want} {error "PVM_REGION wrong physical constant value $pn"}
 if {[dict exists $pties [$ti getName]]} {error "PVM_REGION duplicate constant driver"}
 dict set pties [$ti getName] $ti
 incr nw
}
if {$nw!=546} {error "PVM_REGION W constant inventory drift: $nw"}
pvm_make_region pvm_macro_W_constants {86.4 229.23 172.8 229.77} [dict values $pties]
puts "PVM_REGION source-bound area=$pa, local density=[expr {$pa/(172.8*$ph)}], boundaryregs=[dict size $pio], fullband unchanged"
