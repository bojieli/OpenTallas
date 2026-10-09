read_db $::env(ODB)
set b [ord::get_db_block]
foreach pattern {*wire85399 *wire85407} {
 set cur NULL
 foreach i [$b getInsts] {if {[string match $pattern [$i getName]]} {set cur $i;break}}
 if {$cur eq "NULL"} {puts "MISSING $pattern";continue}
 set start $cur
 foreach direction {up down} {
  set cur $start
  puts "TRACE $pattern $direction"
  for {set k 0} {$k<256} {incr k} {
   set n NULL
   foreach t [$cur getITerms] {if {[[$t getMTerm] getName] eq [expr {$direction eq "up"?"A":"Y"}]} {set n [$t getNet]}}
   if {$n eq "NULL"} {puts "END [[$cur getMaster] getName] [$cur getName]";break}
   set nxt NULL
   foreach t [$n getBTerms] {puts "ROOT_PORT [$t getName]"}
   foreach t [$n getITerms] {
    set i [$t getInst]
    if {$i eq $cur} {continue}
    set typ [[$t getMTerm] getIoType]
    if {($direction eq "up" && $typ eq "OUTPUT") || ($direction eq "down" && $typ eq "INPUT")} {
     puts "STEP $k [$i getName]/[[$t getMTerm] getName] [[$i getMaster] getName] NET [$n getName]"
     if {![string match BUF* [[$i getMaster] getName]]} {set nxt END;break}
     set nxt $i
    }
   }
   if {$nxt eq "NULL" || $nxt eq "END"} {break};set cur $nxt
  }
 }
}
