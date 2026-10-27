read_db [glob /srv/opentallas-scratch2/claude/core-lat-r13-1027/kits/ot_s81_sstn_base566_r14tk/run/results/asap7/*/base/5_1_grt.odb]
set b [ord::get_db_block]
set mode $::env(MODE)
if {$mode eq "moveport"} { set bt [$b findBTerm ck]; foreach p [$bt getBPins] { foreach x [$p getBoxes] { odb::dbBox_destroy $x } ; odb::dbBox_create $p [[ord::get_db_tech] findLayer M5] 43064 15024 43096 15216 } }
if {$mode eq "nondr"} { foreach n [$b getNets] { if {[$n getNonDefaultRule] ne "NULL"} { set nm [$n getName]; if {[regexp {^(ck|mp_ck_root|mp_ck_K_r|mp_ck_T[01]_br$)} [$n getName]] || 1} { $n setNonDefaultRule NULL } } } }
foreach nm {ck} { set n [$b findNet $nm]; puts "NET $nm ndr=[$n getNonDefaultRule] iterms=[llength [$n getITerms]]" }
set_thread_count 16
set_routing_layers -signal M2-M5 -clock M2-M5
detailed_route -droute_end_iter 3 -verbose 0
puts "DRT_DONE $mode"
