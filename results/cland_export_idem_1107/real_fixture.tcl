read_db /work/3_place.odb
set b [ord::get_db_block]
proc sig {b} {
 set out [list [llength [$b getInsts]] [llength [$b getNets]]]
 foreach n {cland_fwd_fclk_out_coll_o0 cland_fwd_fclk_out_ft0_o cland_fwd_fclk_out_ft1_o cland_fwd_fclk_out_cland_up} {
  set i [$b findInst $n]
  lappend out [list $n [[$i getMaster] getName] [$i getLocation] [$i getPlacementStatus] [[[$i findITerm A] getNet] getName] [[[$i findITerm Y] getNet] getName]]
 }
 return $out
}
set before [sig $b]
source /work/fixed_exports.tcl
source /work/fixed_exports.tcl
if {[sig $b] ne $before} {error "REUSE changed real checkpoint topology/geometry"}
set i [$b findInst cland_fwd_fclk_out_coll_o0]
set m [$i getMaster];set src [[$b findBTerm clk_t32] getNet];set dst [$b findBTerm {fclk_out_coll_o0[0]}]
if {![catch {ot_cland_existing $i $m [[$b findBTerm clk_t7] getNet] $dst} e] || ![string match *connectivity*mismatch* $e]} {error "bad source accepted: $e"}
if {![catch {ot_cland_existing $i $m $src [$b findBTerm {fclk_out_ft0_o[0]}]} e] || ![string match *connectivity*mismatch* $e]} {error "bad destination accepted: $e"}
set wrong {}
foreach x [$b getInsts] {if {[[$x getMaster] getName] ne [$m getName]} {set wrong [$x getMaster];break}}
if {![catch {ot_cland_existing $i $wrong $src $dst} e] || ![string match *master*mismatch* $e]} {error "bad master accepted: $e"}
if {[sig $b] ne $before} {error "Mismatch tests changed checkpoint"}
puts "CLAND_EXPORT_REAL_FIXTURE PASS reuse_calls8 exports4 input_mismatch_caught1 destination_mismatch_caught1 master_mismatch_caught1 topology_geometry_unchanged1"
