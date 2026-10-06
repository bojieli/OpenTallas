set b [ord::get_db_block]
set n 0
foreach i [$b getInsts] {
 if {[string first g_native_grant_receiver [$i getName]]>=0 && [string match DFF* [[$i getMaster] getName]]} {incr n}
}
if {$n!=4} {error "Native checked permission requires4 clocked receivers; found$n"}
puts "C22_REAL_GRANT_RECEIVER_PASS count=$n"
