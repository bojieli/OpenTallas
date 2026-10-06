set b [ord::get_db_block]
set n 0
foreach i [$b getInsts] {
 if {[string first g_native_grant_receiver [$i getName]]<0 || ![string match DFF* [[$i getMaster] getName]]} {continue}
 incr n
 set data 0; set clock 0; set output 0
 puts "C22_RECEIVER instance=[$i getName] master=[[$i getMaster] getName]"
 foreach t [$i getITerms] {
  set mt [$t getMTerm]; set pn [$mt getName]
  if {$pn ni {D CLK CK Q QN}} {continue}
  set net [$t getNet]
  if {$net == "NULL" || $net == ""} {error "Unconnected receiver pin [$i getName]/$pn"}
  puts "C22_RECEIVER_PIN instance=[$i getName] pin=$pn direction=[$mt getIoType] net=[$net getName]"
  if {$pn == "D"} {incr data}
  if {$pn == "CLK" || $pn == "CK"} {incr clock}
  if {$pn == "Q" || $pn == "QN"} {incr output}
  report_net -digits 6 [$net getName]
 }
 if {$data!=1 || $clock!=1 || $output!=1} {error "Receiver D/clock/Q pin topology invalid: [$i getName]"}
}
if {$n!=4} {error "Native checked permission requires4 clocked receivers; found$n"}
puts "C22_REAL_GRANT_RECEIVER_PASS count=$n connected_D_clock_Q=4"
