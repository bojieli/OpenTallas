# Private PVM prototype. Every guard refuses logical graph drift; no mutation.
proc pvm_bf_cells {block} {
  set cells {}; set counts [dict create]
  foreach i [$block getInsts] {
    set name [string map {\\ ""} [$i getName]]
    if {![regexp {^u_core\.g_safe\.g_madd\[([0-9]+)\]\.g_fan32\.u_m\.genblk1\.g_native7\.u_native\.} $name -> lane]} continue
    dict incr counts $lane
    lappend cells $i
  }
  if {[llength $cells] != 56000 || [dict size $counts] != 16} {error "PVM_BF_COHORT_COUNT $counts"}
  dict for {lane count} $counts {if {$lane < 0 || $lane > 15 || $count != 3500} {error "PVM_BF_LANE_COUNT $counts"}}
  return $cells
}
proc pvm_bf_graph {block} {
  set cellrows {}; set nets [dict create]
  foreach i [pvm_bf_cells $block] {
    set pins {}
    foreach t [$i getITerms] {
      if {[$t getSigType] in {POWER GROUND}} continue
      set n [$t getNet]; set name ""
      if {$n ne "NULL"} {set name [$n getName]; dict set nets $name $n}
      lappend pins [list [[$t getMTerm] getName] [$t getIoType] [$t getSigType] $name]
    }
    lappend cellrows [list [$i getName] [[$i getMaster] getName] [lsort $pins]]
  }
  set netrows {}
  dict for {name n} $nets {
    set endpoints {}; set ports {}
    foreach t [$n getITerms] {lappend endpoints [list [[$t getInst] getName] [[$t getMTerm] getName] [$t getIoType] [$t getSigType]]}
    foreach t [$n getBTerms] {lappend ports [list [$t getName] [$t getIoType] [$t getSigType]]}
    lappend netrows [list $name [$n getSigType] [lsort $endpoints] [lsort $ports]]
  }
  return [list [lsort $cellrows] [lsort $netrows]]
}
proc pvm_bf_guard {stage} {
  if {![info exists ::env(PVM_BF_EXPECTED)] || ![info exists ::env(PVM_BF_RECEIPTS)]} {error PVM_BF_MISSING_PROOF_PATHS}
  set f [open $::env(PVM_BF_EXPECTED) r]; set expected [read $f]; close $f
  set actual [pvm_bf_graph [ord::get_db_block]]
  if {$actual ne [string trimright $expected "\n"]} {
    # Preserve the first rejected state without changing any flag or graph.
    set out [open [file join $::env(PVM_BF_RECEIPTS) "$stage.failed.graph.tcllist"] {WRONLY CREAT EXCL}]
    puts $out $actual; close $out
    write_db [file join $::env(PVM_BF_RECEIPTS) "$stage.failed.odb"]
    error "PVM_BF_GRAPH_DRIFT $stage"
  }
  set out [open [file join $::env(PVM_BF_RECEIPTS) "$stage.graph.tcllist"] {WRONLY CREAT EXCL}]
  puts $out $actual; close $out
  puts "PVM_BF_GRAPH_PASS $stage cells=56000 nets=[llength [lindex $actual 1]]"
}
proc pvm_bf_private_data_nets {block} {
  set ids [dict create]; set nets [dict create]
  foreach i [pvm_bf_cells $block] {
    regexp {g_madd\[([0-9]+)\]} [string map {\\ ""} [$i getName]] -> lane
    dict set ids [$i getId] $lane
    foreach t [$i getITerms] {set n [$t getNet]; if {$n ne "NULL"} {dict set nets [$n getId] $n}}
  }
  set result {}
  dict for {id n} $nets {
    if {[$n getSigType] ne "SIGNAL" || [llength [$n getBTerms]]} continue
    if {[regexp -nocase {(^|[._])((rst|reset|clk|clock)[^.]*)|(^|[._])(VDD|VSS|tie|const)([._]|$)} [$n getName]]} continue
    set good 1; set drivers 0; set loads 0; set owner ""
    foreach t [$n getITerms] {
      set i [$t getInst]; set pin [[$t getMTerm] getName]
      if {![dict exists $ids [$i getId]] || [$t getSigType] ne "SIGNAL" ||
          [regexp -nocase {^(CLK|CK|CP|RESETN?|SETN?|RN|SN|R|S)$} $pin] ||
          [regexp -nocase {TIE|LOGIC[01]|CONST} [[$i getMaster] getName]]} {set good 0; break}
      set lane [dict get $ids [$i getId]]
      if {$owner eq ""} {set owner $lane} elseif {$owner ne $lane} {set good 0; break}
      if {[$t getIoType] eq "OUTPUT"} {incr drivers} elseif {[$t getIoType] eq "INPUT"} {incr loads} else {set good 0}
    }
    # Retain the complete frozen SSA, including 113 one-driver/zero-load nets
    # per kernel. These are private cell outputs, not boundary or tie nets.
    if {$good && $drivers == 1} {lappend result $n}
  }
  return $result
}
