# BF G2 control isolation (CORES-EARLY-9, plan opentallas.bf_g2_control_isolation.v1 from Codex packer 6a8b07259):
# one touchable BUFx2 between each ICG enable pin (ENA/SE) and its existing control net, so timing repair can buffer
# the control net without touching dont_touch ICGs.  Clock pins / GCLK / masters / ICG sites are not touched.
# Input TSV (/work/bf_enable_isolation.tsv): name target pin x_um y_um orient.  Fail closed on any mismatch.
proc ot_bfi_dump {path} {
  set f [open $path w]
  foreach i [[ord::get_db_block] getInsts] {
    foreach it [$i getITerms] {
      set n [$it getNet]; if {$n eq "NULL"} continue
      puts $f "[$i getName]\t[[$it getMTerm] getName]\t[$n getName]\t[$n getSigType]"
    }
  }
  close $f
}
proc ot_bfi_boxes {path} {
  set f [open $path w]
  foreach i [[ord::get_db_block] getInsts] {
    set st [$i getPlacementStatus]
    if {$st ni {FIRM LOCKED COVER} && ![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]
    puts $f "[$i getName]\t$st\t[[$i getMaster] getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"
  }
  close $f
}
proc ot_bfi_apply {tsv} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
  set m [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
  if {$m eq "NULL"} {error "OT_BFI_MASTER"}
  set f [open $tsv r]; set k 0
  while {[gets $f line] >= 0} {
    if {$line eq "" || [string index $line 0] eq "#"} continue
    lassign [split $line "\t"] name target pin x y orient
    set i [$b findInst $target]
    if {$i eq "NULL"} {error "OT_BFI_TARGET $target"}
    if {![string match ICG* [[$i getMaster] getName]]} {error "OT_BFI_TARGET_MASTER $target [[$i getMaster] getName]"}
    if {$pin ni {ENA SE}} {error "OT_BFI_PIN $target/$pin"}
    set it [$i findITerm $pin]; set n [$it getNet]
    if {$n eq "NULL"} {error "OT_BFI_UNCONNECTED $target/$pin"}
    if {[$n getSigType] eq "CLOCK"} {error "OT_BFI_CLOCK_NET $target/$pin [$n getName]"}
    if {[$b findInst $name] ne "NULL"} {error "OT_BFI_EXISTS $name"}
    set bi [odb::dbInst_create $b $m $name]
    set no [odb::dbNet_create $b ${name}_y]
    if {$no eq "NULL"} {error "OT_BFI_NET_EXISTS ${name}_y"}
    set prot [$i isDoNotTouch]
    if {$prot} {$i setDoNotTouch 0}
    try {$it disconnect; $it connect $no} finally {if {$prot} {$i setDoNotTouch 1}}
    [$bi findITerm A] connect $n
    [$bi findITerm Y] connect $no
    $bi setOrient $orient
    $bi setLocation [expr {round($x*$u)}] [expr {round($y*$u)}]
    $bi setPlacementStatus FIRM
    incr k
  }
  close $f
  puts "OT_BFI_APPLIED $k"
  return $k
}
set ot_bfi_tsv [expr {[info exists ::env(OT_BFI_TSV)] ? $::env(OT_BFI_TSV) : "/work/bf_enable_isolation.tsv"}]
if {[file exists $ot_bfi_tsv]} {
  if {[info exists ::env(OT_BFI_DUMP)]} {ot_bfi_dump $::env(OT_BFI_DUMP).pre}
  set ot_bfi_n [ot_bfi_apply $ot_bfi_tsv]
  if {[info exists ::env(OT_BFI_DUMP)]} {ot_bfi_dump $::env(OT_BFI_DUMP).post; ot_bfi_boxes $::env(OT_BFI_DUMP).boxes}
}
