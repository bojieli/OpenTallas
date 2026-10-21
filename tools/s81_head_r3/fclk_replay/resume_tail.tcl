# Authorized diagnostic physical continuation in a FRESH directory; original case/repair are read-only.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l {SEQ_RVT_TT_nldm_220123.lib INVBUF_RVT_TT_nldm_220122.lib.gz SIMPLE_RVT_TT_nldm_211120.lib.gz} {read_liberty $P/lib/NLDM/asap7sc7p5t_$l}
foreach f [glob /baseline/views/*.lib] {read_liberty $f}
read_db /repair/repaired.odb
source /baseline/die_repeaters.tcl
source /baseline/cluster_bounds.tcl
source /candidate/fclk_audit.tcl
source /work/resume_state.tcl
set ::ot_die_rep_occ [dict create]
array unset ::ot_die_rep_fclk_old
dict for {n m} $::ot_die_rep_pre {set ::ot_die_rep_fclk_old($n) 1}
set new 0
foreach i [[ord::get_db_block] getInsts] {
    if {[dict exists $::ot_die_rep_pre [$i getName]]} continue
    if {![$i isPlaced]} {error "unplaced inserted repeater [$i getName]"}
    lassign [$i getLocation] x y
    set x1 [expr {$x+[[$i getMaster] getWidth]}]
    for {set sx $x} {$sx<$x1} {incr sx $::ot_die_rep_slw} {dict set ::ot_die_rep_occ "$sx,$y" 1}
    incr new
}
set f [open /baseline/run.tcl];set original [read $f];close $f
set found 0
foreach line [split $original "\n"] {
    if {[string match {set ::ot_die_rep_fclk_data_ports *} $line]} {uplevel #0 $line;incr found}
}
if {$found!=1} {error "missing/ambiguous original complete-payload contract"}
set ::ot_die_rep_fclk_args [list /work/die_repeaters.fclk.post_grt {n*_fck*} {BUFx8_ASAP7_75t_R}]
set bounds [ot_cluster_bounds /work/existing_bounds_pre_grt.json resumed_diagnostic]
puts "HEAD_RESUME_SCOPE diagnostic_only original_ideal_top_ports_preserved bounds=$bounds inserted_repeaters=$new"
if {[ot_die_rep_fclk_audit /work/die_repeaters.fclk.pre_grt {n*_fck*} {BUFx8_ASAP7_75t_R}] != 0} {error "complete fclk check failed before physical tail"}
source $P/setRC.tcl
set_wire_rc -signal -layer M8
# Preserve the original post-GRT checks and record their return; no silent absent Tcl state.
rename ot_die_rep_post_grt_audit ot_head_original_post_grt_audit
proc ot_die_rep_post_grt_audit {args} {set ::ot_head_post_grt_rc [ot_head_original_post_grt_audit {*}$args];return $::ot_head_post_grt_rc}
set start [string first "\ncreate_clock -name clk -period " $original]
if {$start<0 || [string first "puts OT_DONE" $original $start]<0} {error "missing original physical tail"}
set tail [string range $original [expr {$start+1}] end]
uplevel #0 $tail
if {![info exists ::ot_head_post_grt_rc]} {error "original post-GRT audit did not run"}
set final_fclk [ot_die_rep_fclk_audit /work/die_repeaters.fclk.final {n*_fck*} {BUFx8_ASAP7_75t_R}]
puts "HEAD_PHYSICAL_TAIL post_grt=$::ot_head_post_grt_rc fclk=$final_fclk"
if {$::ot_head_post_grt_rc || $final_fclk} {error "unchanged post-GRT checks failed"}
write_db /work/out/final_checked.odb
puts HEAD_PHYSICAL_TAIL_PASS_DIAGNOSTIC
