# Exact locked image's native TT library family; clock classification only.
foreach f {
 asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
 asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
 asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
 asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
 asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f}
read_db /work/input.odb
read_sdc /work/native_3_place.sdc
# This is STA findClkNets(), the same backend called by pinned FastRoute initClockNets.
if {![llength [info commands ::sta::find_all_clk_nets]]} {error SC_NATIVE_CLOCK_INVENTORY_API_MISSING}
set b [ord::get_db_block];set native_names {};set db_names {}
foreach n [$b getNets] {if {[$n getSigType] eq "CLOCK"} {dict set db_names [$n getName] 1}}
foreach n [::sta::find_all_clk_nets] {
 if {[string match "*odb__dbNet*" $n]} {set dn $n} else {set dn [$b findNet [get_full_name $n]]}
 if {$dn eq "NULL" || $dn eq ""} {error "SC_NATIVE_CLOCK_NET_UNRESOLVED $n"}
 if {[$dn isSpecial]} {error "SC_NATIVE_CLOCK_NET_EXCLUDED [$dn getName]"}
 dict set native_names [$dn getName] 1
}
set n [dict size $native_names]
set same [expr {[lsort [dict keys $native_names]] eq [lsort [dict keys $db_names]]}]
set f [open /work/native_clock_preflight.json w]
puts $f [format {{"scope":"NATIVE_CLOCK_CLASSIFICATION_ONLY_NO_TIMING_ANALYSIS","native_clock_nets":%d,"db_clock_nets":%d,"same_net_set":%s,"expected":2390}} $n [dict size $db_names] [expr {$same ? "true" : "false"}]];close $f
puts "SC_NATIVE_FASTROUTE_CLOCK_PREFLIGHT native=$n db=[dict size $db_names] same_set=$same expected=2390 no_timing_analysis"
if {$n!=2390 || !$same} {error SC_NATIVE_CLOCK_CLASSIFICATION_MISMATCH}
