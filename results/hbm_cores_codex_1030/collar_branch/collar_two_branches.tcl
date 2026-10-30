# Two exact DATA-only local branches; original upper operand branches retained.
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
foreach tail {place2708 place2717} yy {14.04 21.06} {
 set matches {}
 foreach i [$b getInsts] {if {[string match "*u_payload/$tail" [$i getName]]} {lappend matches $i}}
 if {[llength $matches]!=1} {error "collar expected one $tail"}
 set i [lindex $matches 0]
 if {[[$i getMaster] getName] ne "BUFx3_ASAP7_75t_R"} {error "collar wrong master"}
 set old [[$i findITerm Y] getNet]
 if {[$old getSigType] ne "SIGNAL"} {error "collar non-DATA net"}
 set bottom {};set top {}
 foreach it [$old getITerms] {
  if {[[$it getMTerm] getIoType] ne "INPUT"} continue
  set nm [[$it getInst] getName]
  if {![string match {*g_record*} $nm] && ![string match {*g_operand*} $nm]} {error "collar unexpected sink $nm"}
  set box [[$it getInst] getBBox]
  if {[$box yMax] < 30*$u} {lappend bottom $it} else {lappend top $it}
 }
 if {[llength $bottom]!=10 || [llength $top]!=2} {error "collar wrong branch partition [llength $bottom]/[llength $top]"}
 set name "ot_collar_local_$tail"
 if {[$b findInst $name] ne "NULL" || [$b findNet $name] ne "NULL"} {error "collar duplicate branch"}
 set c [odb::dbInst_create $b [$i getMaster] $name]
 set n [odb::dbNet_create $b $name];$n setSigType SIGNAL
 foreach it [$i getITerms] {
  set mt [$it getMTerm];set ct [$c findITerm [$mt getName]]
  if {[$mt getIoType] eq "OUTPUT" && [$mt getSigType] eq "SIGNAL"} {$ct connect $n} elseif {[$it getNet] ne "NULL"} {$ct connect [$it getNet]}
 }
 foreach it $bottom {$it disconnect;$it connect $n}
 $c setLocation [expr {round(47.52*$u)}] [expr {round($yy*$u)}]
 $c setOrient R0;$c setPlacementStatus PLACED
 puts "COLLAR_BRANCH $name original[$i getName] bottom10 upper2 xy47.52,$yy"
}
