# Read-only extraction of original instance identities before repeaters.
read_db /baseline/out/place.odb
set f [open /work/old_names.tcl w]
puts $f {array unset ::ot_die_rep_fclk_old}
set count 0
foreach i [[ord::get_db_block] getInsts] {
    puts $f [list set ::ot_die_rep_fclk_old([$i getName]) 1]
    incr count
}
close $f
puts "ORIGINAL_INSTANCE_NAMES $count"
if {$count == 0} { error "empty original snapshot" }
