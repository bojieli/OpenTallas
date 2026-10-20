read_db {/srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_sf7w-20261019-221652/routes/gate/work/orfs/results/asap7/opentallas_qfd_d2d_static_ovl_sf7_asap7_ref_gate/base/4_cts.odb}
set block [ord::get_db_block]
set unbound 0; set protected 0; set fixed 0
foreach i [$block getInsts] { foreach t [$i getITerms] { if {[[$t getMTerm] getSigType] ni {POWER GROUND} || [$t getNet] ne "NULL"} continue; incr unbound; if {[$i isDoNotTouch]} {incr protected}; if {[$i getPlacementStatus] in {FIRM LOCKED}} {incr fixed} } }
puts "BEFORE unbound=$unbound protected=$protected fixed=$fixed"
global_connect
set unbound 0
foreach i [$block getInsts] {foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] in {POWER GROUND} && [$t getNet] eq "NULL"} {incr unbound}}}
puts "AFTER_GLOBAL_CONNECT unbound=$unbound"
