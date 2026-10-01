read_db /inputs/5_1_grt.odb
set b [ord::get_db_block]
set r [lindex [$b getRows] 0]
set s [$r getSite]
puts "DIAG|SITE|[$s getWidth]|[$s getHeight]|[$r getOrigin]"
exit
