# Default-off complete phase decoder banks. Source AFTER original phase/control banks.
uplevel #0 {
if {![info exists ::env(OT_INGEST_PHASE_DAG_LOCAL)] || !$::env(OT_INGEST_PHASE_DAG_LOCAL)} {return}
set pb_root [$ff_blk findNet {_069618_}]
set pb_seen {};set pb_frontier {};set pb_pi 0
proc pb_walk {net} {
 if {[dict exists $::pb_seen $net]} return
 dict set ::pb_seen $net 1
 if {[llength [$net getBTerms]]} {error "PHASE_DAG primary frontier forbidden"}
 set ds {};foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds]!=1} {error "PHASE_DAG driver count"}
 set i [[lindex $ds 0] getInst]
 if {[lb_isff $i]} {dict set ::pb_frontier [$i getName] $i;return}
 foreach t [$i getITerms] {if {[[$t getMTerm] getIoType] eq "INPUT" && [[$t getMTerm] getSigType] ni {POWER GROUND}} {pb_walk [$t getNet]}}
}
pb_walk $pb_root
if {[dict size $pb_frontier]!=7} {error "PHASE_DAG requires actual7 internal state frontier"}
set pb_roles {}
dict for {n i} $pb_frontier {
 set name [string map {\\ {}} $n]
 if {![regexp {st_(mode|d|ph)\[([0-9]+)\]} $name -> fam bit] || "$fam:$bit" ni {mode:0 mode:1 mode:2 d:3 ph:0 ph:1 ph:2}} {error "PHASE_DAG unexpected state $name"}
 if {[dict exists $pb_roles "$fam:$bit"]} {error "PHASE_DAG duplicate state role"}
 dict set pb_roles "$fam:$bit" $n
}
set pb_ffmap {};set pb_total 0;set pb_inputs 0;set pb_loads 0
set pb_log [open $::env(RESULTS_DIR)/phase_dag_banks.tsv w]
lb_begin $ff_blk [dict keys $pb_frontier] 64
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_171255_} {B}]] 91530 30780]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 1
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank0 loads1 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_120201_} {C}] [list {_120149_} {C}] [list {_120181_} {C}] [list {_120165_} {C}] [list {_120115_} {C}] [list {_120131_} {C}] [list {_171610_} {C}] [list {_120098_} {C}] [list {_120227_} {B}] [list {_120752_} {B}]] 247525 21168]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 10
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank1 loads10 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_120360_} {B}] [list {_121145_} {B}] [list {_121226_} {B}] [list {_121177_} {B}] [list {_121242_} {B}] [list {_121258_} {B}] [list {_121211_} {B}] [list {_121196_} {B}] [list {_121162_} {B}] [list {_121399_} {B}]] 278327 13014]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 10
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank2 loads10 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_121015_} {B}]] 276048 35640]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 1
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank3 loads1 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_123839_} {B}] [list {_121771_} {B}] [list {_123384_} {B}] [list {_122204_} {B}] [list {_122391_} {B}] [list {_122172_} {B}] [list {_122220_} {B}] [list {_123199_} {B}] [list {_122717_} {B}] [list {_122732_} {B}] [list {_123216_} {B}] [list {_123231_} {B}] [list {_123246_} {B}] [list {_122669_} {B}] [list {_121648_} {B}] [list {_123138_} {B}]] 329417 23929]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 16
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank4 loads16 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_122235_} {B}] [list {_122189_} {B}] [list {_122637_} {B}] [list {_122250_} {B}] [list {_123169_} {B}] [list {_122686_} {B}] [list {_122890_} {B}] [list {_122701_} {B}] [list {_123610_} {B}] [list {_122751_} {B}] [list {_123950_} {B}] [list {_122139_} {B}] [list {_123154_} {B}] [list {_122654_} {B}] [list {_123184_} {B}] [list {_122157_} {B}]] 331945 22849]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 16
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank5 loads16 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
set pb_previous [llength $::lb::created]
set pb_new [lb_bank $pb_root [list [list {_121276_} {B}] [list {_121523_} {B}] [list {_122016_} {B}] [list {_123263_} {B}] [list {_123012_} {B}] [list {_122768_} {B}] [list {_122515_} {B}] [list {_123495_} {B}] [list {_122267_} {B}]] 332514 35250]
set pb_new [lrange $pb_new $pb_previous end]
incr pb_loads 9
incr pb_total [llength $pb_new]
set pb_inputs [lb_audit]
set pb_ffs 0
foreach a $::lb::audit {lassign $a src copy pin old expected ff;if {$ff} {dict set pb_ffmap [$copy getName] [$src getName]}}
foreach i $pb_new {if {[lb_isff $i]} {incr pb_ffs}}
if {$pb_ffs!=7} {error "PHASE_DAG bank missing exact7 copied FFs"}
puts $pb_log "bank6 loads9 copies[llength $pb_new] audited_inputs[lb_audit] FFs$pb_ffs"
close $pb_log
if {$pb_loads!=63} {error "PHASE_DAG incomplete terminal census"}
puts "INGEST_PHASE_DAG_LOCAL banks7 loads$pb_loads copied_cells$pb_total audited_inputs$pb_inputs extra_cycles0"
}
