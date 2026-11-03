set b [ord::get_db_block]
proc need {ok msg} {if {!$ok} {error $msg}}
set original {}
foreach i [$b getInsts] {dict set original [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
set cn {};foreach n [$b getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend cn [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
set driver [$b findInst {_279616_}]
set sink [$b findInst {u_u_exp1.u_exp.nint\[6\]$_DFF_P_}]
need [expr {$driver ne "NULL" && $sink ne "NULL"}] {missing exact driver/sink}
need [expr {[[$driver getMaster] getName] eq "XNOR2x2_ASAP7_75t_R"}] {driver master mismatch}
set net [[$driver findITerm Y] getNet];set st [$sink findITerm D]
need [expr {[$st getNet] eq $net && [$net getSigType] eq "SIGNAL" && [llength [$net getITerms]]==2 && [llength [$net getBTerms]]==0}] {tail is not exact sole-sink DATA net}
need [expr {[$b findInst codex_l1_exp_tail_buf] eq "NULL" && [$b findNet codex_l1_exp_tail_net] eq "NULL"}] {names exist}
set master [[ord::get_db] findMaster BUFx6f_ASAP7_75t_R]
need [expr {$master ne "NULL"}] {BUF master missing}
# Every original cell remains fixed during legalisation, including CLOCK and all FFs.
foreach i [$b getInsts] {if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
global_route -start_incremental
set bi [odb::dbInst_create $b $master codex_l1_exp_tail_buf]
set nn [odb::dbNet_create $b codex_l1_exp_tail_net];$nn setSigType SIGNAL
[$bi findITerm A] connect $net
[$bi findITerm Y] connect $nn
$st disconnect;$st connect $nn
$bi setLocation 106704 190080;$bi setOrient R0;$bi setPlacementStatus PLACED
source /work/pg_connect.tcl
ot_pg_connect_all l1_tail
ot_pg_require_bound l1_tail
detailed_placement
check_placement -verbose
dict for {nm record} $original {
 set i [$b findInst $nm]
 need [expr {$i ne "NULL" && [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]] eq [lrange $record 0 2]}] "original master/location/orient changed: $nm"
 $i setPlacementStatus [lindex $record 3]
}
set ca {};foreach n [$b getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend ca [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
need [expr {[lsort $cn] eq [lsort $ca]}] {CLOCK connectivity changed}
set pf [open /work/tail_placement.tsv w];foreach i [$b getInsts] {puts $pf [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]]};close $pf
write_db /work/tail_place.odb
source /work/geom_dump.tcl
puts L1_TAIL_PLACE_COMPLETE
