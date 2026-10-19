# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}

read_db /data/ctlm_r6_first_gpl_failed.odb
set b [ord::get_db_block];set units [$b getDbUnitsPerMicron]
set groups {};foreach g [$b getGroups] {foreach i [$g getInsts] {dict set groups $i [$g getName]}}
set count {};set area {};set movable {};set prefix {}
set out [open /data/ctlm_r6_failed_groups.tsv w]
foreach i [$b getInsts] {
 set m [$i getMaster];if {[$m isBlock]} continue
 set g TOP;if {[dict exists $groups $i]} {set g [dict get $groups $i]}
 set a [expr {double([$m getWidth])*[$m getHeight]/$units/$units}]
 dict incr count $g
 if {![dict exists $area $g]} {dict set area $g 0};dict set area $g [expr {[dict get $area $g]+$a}]
 if {![$i isFixed]} {if {![dict exists $movable $g]} {dict set movable $g 0};dict set movable $g [expr {[dict get $movable $g]+$a}]}
 set n [$i getName];set pre other
 if {[regexp {^([a-zA-Z_]+)[0-9]} $n -> pre]} {}
 if {$g eq "TOP" && ![$i isFixed]} {dict incr prefix $pre}
 puts $out [join [list $n [$m getName] $g $a [$i getPlacementStatus] [$i getLocation]] \t]
}
close $out
foreach g [dict keys $count] {set mov 0;if {[dict exists $movable $g]} {set mov [dict get $movable $g]};puts "ACTUAL_FAILED_GROUP name=$g count=[dict get $count $g] total_std_area_um2=[dict get $area $g] movable_std_area_um2=$mov"}
puts "ACTUAL_FAILED_TOP_PREFIX $prefix"
