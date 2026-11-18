# NOMCAP-1118 census (tools/die_plan/nomcap.py): masters on the clock network of a routed DB.  ODB=<6_final.odb> openroad -no_init -exit nomcap_clkcells.tcl
# list masters of single-input buffers/inverters (and ICGs) on the clock network: backward walk from sequential CLK pins
read_db $::env(ODB)
set blk [ord::get_db_block]
array set seen {}; array set cnt {}; array set sinkm {}
set front {}
foreach inst [$blk getInsts] {
  set m [$inst getMaster]
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getName] eq "CLK" && [$mt getIoType] eq "INPUT"} {
      set sinkm([$m getName]) 1
      set n [$it getNet]; if {$n ne "NULL"} {lappend front $n}
    }
  }
}
set depth 0
while {[llength $front] && $depth < 200} {
  set nxt {}
  foreach n $front {
    set id [$n getId]; if {[info exists seen($id)]} continue; set seen($id) 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
      set inst [$it getInst]; set m [$inst getMaster]; set mn [$m getName]
      if {[$m isBlock]} continue
      set ins {}
      foreach i2 [$inst getITerms] { set t [$i2 getMTerm]; if {[$t getIoType] eq "INPUT" && [$t getSigType] ne "POWER" && [$t getSigType] ne "GROUND"} {lappend ins $i2} }
      set isicg [string match ICG* $mn]
      if {[llength $ins] == 1 || $isicg} {
        incr cnt($mn)
        foreach i2 $ins { if {$isicg && [[$i2 getMTerm] getName] ne "CLK"} continue; set nn [$i2 getNet]; if {$nn ne "NULL"} {lappend nxt $nn} }
      }
    }
  }
  set front $nxt; incr depth
}
foreach k [lsort [array names cnt]] { puts "CLKCELL $k $cnt($k)" }
foreach k [lsort [array names sinkm]] { puts "SINKM $k" }
puts "DEPTH $depth"
