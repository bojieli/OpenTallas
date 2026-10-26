read_db /work/run/results/asap7/kq_qfd_dv_s8x_prog_aspect1713a1/base/5_1_grt.odb
source /work/shallow_clock.tcl
source /work/local_clock_depth.tcl
source /work/mscts_projection.tcl
set A {P0 516.2 R0E 526.5 R0W 515.8 R1E 521.7 R1W 520.2 R2E 511.4 R2W 519.8 R3E 524.0 R3W 525.5 S0 519.2 S1 508.1 S2 528.6 S3 524.2}
set steps {};dict for {k a} $A {dict set steps $k 23.0}
set proposal [ot_ms_projection::select $A $steps 20]
puts "PROJECT_PROPOSAL $proposal"
if {[dict get $proposal counts] ne {S1 1}} {error "unexpected measured-case proposal"}
set b [ord::get_db_block]
set ::ot_dtsh::blk $b
set ::ot_dtsh::master [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
ot_dtsh::capture
set tap [$b findInst ot_ms_S1_tap]
if {$tap eq "NULL"} {error "missing selected actual S1 tap"}
set ip [lindex [ot_dtsh::sigpins $tap INPUT] 0]
set source [$ip getNet]
lassign [$tap getLocation] x y
set u [$b getDbUnitsPerMicron]
lassign [ot_local_depth::site_near $x $y [expr {10*$u}] $::ot_dtsh::master] xx yy orient
set pi [odb::dbInst_create $b $::ot_dtsh::master ot_ms_proj_S1]
$pi setOrient $orient;$pi setLocation $xx $yy;$pi setPlacementStatus FIRM
ot_dtsh::pg $pi
if {[lrange [ot_dtsh::box $pi] 0 1] ne [list $xx $yy]} {error "projection actual/checked footprint mismatch"}
set next [odb::dbNet_create $b ot_ms_proj_S1_n];$next setSigType CLOCK
set sd [$source isDoNotTouch];set td [$tap isDoNotTouch]
if {$sd} {$source setDoNotTouch false};if {$td} {$tap setDoNotTouch false}
[lindex [ot_dtsh::sigpins $pi INPUT] 0] connect $source
[lindex [ot_dtsh::sigpins $pi OUTPUT] 0] connect $next
$ip disconnect;$ip connect $next
if {$sd} {$source setDoNotTouch true};if {$td} {$tap setDoNotTouch true}
$pi setDoNotTouch true;$next setDoNotTouch true
# Preserve every original cell placement and every non-clock FF connection.
dict for {name state} $::ot_dtsh::original {
 set i [$b findInst $name]
 if {[list [ot_dtsh::box $i] [$i getOrient] [[$i getMaster] getName]] ne $state} {error "projection moved original $name"}
}
dict for {key expected} $::ot_dtsh::ff_data {
 lassign $key n p
 set net [[[$b findInst $n] findITerm $p] getNet]
 set got [expr {$net eq "NULL" || $net eq "" ? "" : [$net getName]}]
 if {$got ne $expected} {error "projection changed FF data/control $n/$p"}
}
set f [open /work/project_site.tsv w]
puts $f "kind\tname\tx\ty\tw\th"
foreach i [$b getInsts] {
 if {[$i getName] ne "ot_ms_proj_S1" && [$i getName] ne "ot_ms_S1_tap" && ![[$i getMaster] isBlock]} continue
 set bb [$i getBBox]
 puts $f "[expr {[[$i getMaster] isBlock]?"macro":"clock"}]\t[$i getName]\t[expr {[$bb xMin]/double($u)}]\t[expr {[$bb yMin]/double($u)}]\t[expr {([$bb xMax]-[$bb xMin])/double($u)}]\t[expr {([$bb yMax]-[$bb yMin])/double($u)}]"
}
close $f
write_db /work/projected.odb
puts "PROJECT_GEOM_AUDIT_PASS cells[dict size $::ot_dtsh::original] FFdata[dict size $::ot_dtsh::ff_data] BUF4at[expr {$xx/double($u)}],[expr {$yy/double($u)}], zero data cycles"
