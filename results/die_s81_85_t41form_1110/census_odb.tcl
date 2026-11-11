# T41FORM post-3_4 fanout census on the placed ODB: input-pin loads (+ output bterms) per signal net, limit 24.
read_db $::env(ODB)
set lim 24; set over {}; set h [dict create]
foreach n [[ord::get_db_block] getNets] {
  set t [$n getSigType]
  if {$t eq "POWER" || $t eq "GROUND"} continue
  set c 0
  foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "INPUT"} { incr c } }
  foreach bt [$n getBTerms] { if {[$bt getIoType] eq "OUTPUT"} { incr c } }
  if {$c > $lim} { lappend over [list $c $t [$n getName]] }
}
set over [lsort -integer -decreasing -index 0 $over]
set ncl 0; set nsig 0
foreach o $over { if {[lindex $o 1] eq "CLOCK"} { incr ncl } else { incr nsig } }
puts "T41FORM_CENSUS_ODB limit $lim over [llength $over] clock $ncl signal $nsig"
foreach o [lrange $over 0 40] { puts "T41FORM_CENSUS_ODB_NET $o" }
