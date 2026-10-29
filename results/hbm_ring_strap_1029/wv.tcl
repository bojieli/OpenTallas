read_db $::env(ECO_IN)
set block [ord::get_db_block]
foreach n {"qid\[0\]" "strap_qid\[0\]" "strap_qid\[1\]"} { set b [$block findBTerm $n]; puts "BT $n -> $b [expr {$b ne "NULL" ? [[$b getNet] getName] : "-"}]" }
write_verilog $::env(ECO_V)
exit
