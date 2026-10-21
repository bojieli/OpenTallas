read_db /work/input.odb
set b [ord::get_db_block]
puts "H9_XOK_DB instances=[llength [$b getInsts]] nets=[llength [$b getNets]]"
proc plain {s} {regsub -all {\\([\[\]])} $s {\1} s;return $s}
for {set k 0} {$k<4} {incr k} {
 set output [format {xok[%d]} $k];set source [format {xk[%d]} $k];set target [format {u_xo%d} $k]
 set term [$b findBTerm $output]
 if {$term eq "NULL"||[$term getIoType] ne "OUTPUT"} {error "H9_XOK missing actual output $output"}
 set n [$term getNet];set visited [dict create];set inv 0;set hops {};set found 0
 for {set d 0} {$d<64} {incr d} {
  if {$n eq "NULL"||[dict exists $visited [$n getName]]} {error "H9_XOK floating/cyclic clock path"};dict set visited [$n getName] 1
  set inputs {};foreach t [$n getBTerms] {if {[$t getIoType] eq "INPUT"} {lappend inputs $t}}
  set drivers {};foreach t [$n getITerms] {if {[$t isOutputSignal]} {lappend drivers $t}}
  if {[llength $inputs]} {
   if {[llength $inputs]!=1||[llength $drivers]||[plain [[lindex $inputs 0] getName]] ne $source||!$found||($inv%2)} {error "H9_XOK wrong source/polarity/multidriver on $output"}
   lappend hops "INPUT:$source";puts "H9_XOK_PASS output=$output root=$source macro=$target extra_inversions=$inv path=[join $hops { <- }]";break
  }
  if {[llength $drivers]!=1} {error "H9_XOK missing/multidriver on [$n getName]"}
  set t [lindex $drivers 0];set i [$t getInst];set m [[$i getMaster] getName];set pin [[$t getMTerm] getName]
  lappend hops "[$i getName]:$m/$pin/net=[$n getName]"
  if {$m eq "dsfd_dvrly_276_NS"} {
   if {[$i getName] ne $target||$pin ne "ck_o"||$found} {error "H9_XOK unauthorized forwarded macro/path"}
   set a [$i findITerm ck];if {$a eq "NULL"||![$a isInputSignal]} {error "H9_XOK no actual macro ck input"};set found 1
  } elseif {[regexp {^BUF} $m]&&$pin eq "Y"} {
   set a [$i findITerm A]
  } elseif {[regexp {^INV} $m]&&$pin eq "Y"} {
   set a [$i findITerm A];incr inv
  } else {error "H9_XOK reject data logic/gating/unknown driver $m/$pin"}
  if {$a eq "NULL"||[$a getNet] eq "NULL"} {error "H9_XOK absent buffer/macro input"};set n [$a getNet]
 }
 if {$d>=64} {error "H9_XOK exceeded64 bounded clock ancestors"}
}
puts "H9_XOK_READONLY PASS pairs=4 mutation_commands=0 write_db=0"
