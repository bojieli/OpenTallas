from pathlib import Path
import sys
corner=sys.argv[1] if len(sys.argv)>1 else "tt"
p=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones')
s=(p/'d2d_boundary_clock.tcl').read_text().split('set out [open /data/boundary_tt.tsv w]')[0]
if corner == "ff":
 s=s.replace('foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*]', 'foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_FF*]')
 s=s.replace('if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }', 'if {[string match *.lib $w]} {set w [string map {_tt.lib _ff.lib} $w];if {![file exists $w]} {error "missingactualFFlib $w"};read_liberty $w}')
 s=s.replace('set ::ot_ce_corner tt','set ::ot_ce_corner ff')
 s=s.replace('(TT placement RC; diagnostic)','(FF placement RC; diagnostic)')
s+=r''' 
proc ep_connect {term net} {
 set inst [$term getInst];set istouch [$inst isDoNotTouch]
 set old [$term getNet];set oldtouch 0;set newtouch [$net isDoNotTouch]
 if {$old ne "NULL"} {set oldtouch [$old isDoNotTouch]}
 if {$istouch} {$inst setDoNotTouch false}
 if {$oldtouch} {$old setDoNotTouch false}
 if {$newtouch} {$net setDoNotTouch false}
 try {
  if {$old ne "NULL"} {odb::dbITerm_disconnect $term}
  odb::dbITerm_connect $term $net
 } finally {
  if {$oldtouch} {$old setDoNotTouch true}
  if {$newtouch} {$net setDoNotTouch true}
  if {$istouch} {$inst setDoNotTouch true}
 }
}
proc ep_snapshot {label} {
 global bnd regs
 foreach kind {min max} {find_timing_paths -path_delay $kind -group_path_count 1}
 set lo 1e20;set hi -1e20;set count 0
 foreach name [dict keys $bnd] {
  set cell [dict get $regs $name]
  set pin [lindex [get_pins -of_objects $cell -filter "direction==input && is_clock"] 0]
  set a [get_property $pin arrival_max_rise]
  if {[regexp -nocase {inf|nan} $a]} {error "E_CLOCK nonfinite $name"}
  if {$a<$lo} {set lo $a;set lname $name}
  if {$a>$hi} {set hi $a;set hname $name}
  incr count
 }
 puts "E_CLOCK_SNAPSHOT $label boundary=$count min=$lo mincell=$lname max=$hi maxcell=$hname spread=[expr {$hi-$lo}] setup_s=[sta::worst_slack_cmd max] hold_s=[sta::worst_slack_cmd min]"
}
proc ep_driver {net} {
 set drivers {}
 foreach t [$net getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend drivers $t}}
 if {[llength $drivers]==0 && [llength [$net getBTerms]]>0} {return ""}
 if {[llength $drivers]!=1} {error "E_CLOCK multidriver/open [$net getName]"}
 return [lindex $drivers 0]
}
proc ep_input {inst} {
 set inputs {}
 foreach t [$inst getITerms] {if {[$t getIoType] eq "INPUT" && [$t getSigType] ni {POWER GROUND}} {lappend inputs $t}}
 if {[llength $inputs]!=1} {error "E_CLOCK nonbuffer input [$inst getName]"}
 return [lindex $inputs 0]
}
proc ep_path {net} {
 global ep_cache
 set n [$net getName]
 if {[dict exists $ep_cache $n]} {return [dict get $ep_cache $n]}
 set d [ep_driver $net]
 if {$d eq ""} {set answer {}} else {
  set inst [$d getInst];set master [[$inst getMaster] getName]
  if {![string match BUF* $master] && ![string match *INV* $master]} {error "E_CLOCK nonbufferclock $master"}
  set answer [linsert [ep_path [[ep_input $inst] getNet]] 0 [$inst getName]]
 }
 dict set ep_cache $n $answer
 return $answer
}
ep_snapshot before
set ep_cache {};set paths {};set allnodes {};set targets {};set common {};set first 1
foreach name [dict keys $bnd] {
 set inst [sta::sta_to_db_inst [dict get $regs $name]]
 set term [$inst findITerm CLK]
 if {$term eq "NULL"} {error "E_CLOCK missingCLK $name"}
 set path [ep_path [$term getNet]]
 if {$first} {set common $path;set first 0} else {
  set next {};foreach c $common {if {$c in $path} {lappend next $c}};set common $next
 }
 foreach c $path {dict set allnodes $c 1}
 set box [$inst getBBox];set x [expr {([$box xMin]+[$box xMax])/2.0/$units}];set y [expr {([$box yMin]+[$box yMax])/2.0/$units}]
 if {475.2-$x<15 && 475.2-$x<$y && 475.2-$x<280.8-$y} {dict set targets $name [list $inst $path]}
}
if {[dict size $targets]!=64 || ![llength $common]} {error "E_CLOCK unexpectedtarget/common population"}
set anchor [lindex $common 0]
set amap {};foreach i [$b getInsts] {dict set amap [$i getName] $i}
set nodes {};set depthmap {};set maxdepth 0
foreach info [dict values $targets] {
 lassign $info inst path
 set stop [lsearch -exact $path $anchor]
 if {$stop<1} {error "E_CLOCK missinganchor"}
 for {set j 0} {$j<$stop} {incr j} {
  set c [lindex $path $j];set depth [expr {$stop-$j}]
  if {[dict exists $depthmap $c] && [dict get $depthmap $c]!=$depth} {error "E_CLOCK ambiguouslevel"}
  dict set nodes $c 1;dict set depthmap $c $depth
  set maxdepth [expr {max($maxdepth,$depth)}]
 }
}
set copies {};set nets {};set levels {};set idx 0
foreach c [lsort [dict keys $nodes]] {
 incr idx;set old [dict get $amap $c];set master [$old getMaster]
 set copy [odb::dbInst_create $b $master [format ot_eclk_copy_%04d $idx]]
 set net [odb::dbNet_create $b [format ot_eclk_net_%04d $idx]];$net setSigType CLOCK
 foreach t [$old getITerms] {
  set nt [$copy findITerm [[$t getMTerm] getName]]
  if {[$t getIoType] eq "OUTPUT"} {ep_connect $nt $net} elseif {[$t getSigType] in {POWER GROUND} && [$t getNet] ne "NULL"} {ep_connect $nt [$t getNet]}
 }
 dict set copies $c $copy;dict set nets $c $net;dict lappend levels [dict get $depthmap $c] $c
}
foreach c [dict keys $copies] {
 set old [dict get $amap $c];set copy [dict get $copies $c];set input [ep_input $old];set inputnet [$input getNet];set driver [ep_driver $inputnet]
 if {$driver eq ""} {error "E_CLOCK copiedpastanchor"}
 set parent [[$driver getInst] getName]
 if {[dict exists $nets $parent]} {set inputnet [dict get $nets $parent]} elseif {$parent ne $anchor} {error "E_CLOCK parentnotinclonegraph"}
 ep_connect [ep_input $copy] $inputnet
}
set anchorbox [[dict get $amap $anchor] getBBox];set ax [expr {([$anchorbox xMin]+[$anchorbox xMax])/2.0/$units}]
dict for {depth list} $levels {
 set n [llength $list];set j 0
 foreach c [lsort $list] {
  set copy [dict get $copies $c];set master [$copy getMaster]
  set cx [expr {$ax+(467.0-$ax)*$depth/double($maxdepth)}]
  set x [expr {round(($cx-[$master getWidth]/2.0/$units)/0.054)*0.054}]
  set y [expr {129.6+($n>1?10.8*$j/($n-1):5.4)}];set y [expr {round($y/0.27)*0.27}]
  $copy setOrient R0;$copy setLocation [expr {int(round($x*$units))}] [expr {int(round($y*$units))}];$copy setPlacementStatus FIRM
  puts "E_CLOCK_PLACE clone=[$copy getName] original=$c level=$depth x=$x y=$y"
  incr j
 }
}
foreach info [dict values $targets] {
 lassign $info inst path;set c [lindex $path 0];set term [$inst findITerm CLK]
 ep_connect $term [dict get $nets $c]
}
# Freeze original clock-path cells: prototype isolates this new owned branch.
foreach c [dict keys $allnodes] {[dict get $amap $c] setPlacementStatus FIRM}
detailed_placement
check_placement -verbose
estimate_parasitics -placement
set_propagated_clock [all_clocks]
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {read_sdc $::env(OT_GATE_SIGNOFF_SDC)}
ep_snapshot after
set ep_Emin 1e20;set ep_Emax -1e20;set ep_Omin 1e20;set ep_Omax -1e20
set Ecp {};set Edp {};set Ocp {};set Odp {};set async {}
foreach pin [all_registers -async_pins] {dict set async [get_full_name $pin] 1}
foreach pin [all_registers -clock_pins] {
 set cell [get_full_name [get_cells -of_objects $pin]]
 if {[dict exists $targets $cell]} {lappend Ecp $pin} else {lappend Ocp $pin}
}
foreach pin [all_registers -data_pins] {
 if {[dict exists $async [get_full_name $pin]]} continue
 set cell [get_full_name [get_cells -of_objects $pin]]
 if {[dict exists $targets $cell]} {lappend Edp $pin} else {lappend Odp $pin}
}
foreach name [dict keys $bnd] {
 set pin [lindex [get_pins -of_objects [dict get $regs $name] -filter "direction==input && is_clock"] 0]
 set a [get_property $pin arrival_max_rise]
 if {[dict exists $targets $name]} {
  set ep_Emin [expr {min($ep_Emin,$a)}];set ep_Emax [expr {max($ep_Emax,$a)}]
 } else {
  set ep_Omin [expr {min($ep_Omin,$a)}];set ep_Omax [expr {max($ep_Omax,$a)}]
 }
}
set bounds {}
foreach label {E_to_other other_to_E} from [list $Ecp [concat $Ocp [all_inputs -no_clocks]]] to [list [concat $Odp [all_outputs]] $Edp] {
 foreach kind {min max} {
  set worst 1e20;set witness {}
  foreach path [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1] {
   set slack [get_property $path slack]
   if {$slack<$worst} {set worst $slack;set witness "[get_full_name [get_property $path startpoint]] -> [get_full_name [get_property $path endpoint]]"}
  }
  if {$worst>1e19} {error "E_CLOCK intervalmissingactualpath $label $kind"}
  dict set bounds $label $kind $worst
  puts "E_CLOCK_PATH_CLASS $label $kind slack_ps=$worst witness=$witness"
  report_checks -from $from -to $to -path_delay $kind -group_path_count 1 -format full_clock_expanded -digits 4
 }
}
set lo_spread [expr {$ep_Omax-80-$ep_Emin}]
set hi_spread [expr {$ep_Omin+80-$ep_Emax}]
set lo_data [expr {max(30-[dict get $bounds E_to_other min],-[dict get $bounds other_to_E max])}]
set hi_data [expr {min([dict get $bounds E_to_other max],[dict get $bounds other_to_E min]-30)}]
puts "E_CLOCK_INTERVAL actual_E=$ep_Emin..$ep_Emax actual_other=$ep_Omin..$ep_Omax uniform_delta_spread_ps=$lo_spread..$hi_spread uniform_delta_data_setup0_hold30_ps=$lo_data..$hi_data admissible_delta_ps=[expr {max($lo_spread,$lo_data)}]..[expr {min($hi_spread,$hi_data)}] phase/reserve_policy=UNCHANGED"

# Verify every target's structural buffer levels and polarity/master sequence.
set ep_cache {};set checked 0
foreach info [dict values $targets] {
 lassign $info inst before
 set after [ep_path [[$inst findITerm CLK] getNet]]
 if {[llength $after]!=[llength $before]} {error "E_CLOCK levelcountchanged [$inst getName]"}
 foreach x $before y $after {
  set old [dict get $amap $x];set new [$b findInst $y]
  if {[[$old getMaster] getName] ne [[$new getMaster] getName]} {error "E_CLOCK master/polaritychanged"}
 }
 incr checked
}
puts "E_CLOCK_PROTOTYPE source=b30f8454c6db1309ee4ec7a154943f6c737b43f2 E_targets=$checked clones=[dict size $copies] anchor=$anchor maximum_clone_depth=$maxdepth levels/polarities=UNCHANGED ports/cycles=UNCHANGED diagnostic_only=1"
write_db /data/eclock_proto_CORNER.odb
'''
s=s.replace('CORNER',corner)
(p/('d2d_eclock_proto_interval_'+corner+'.tcl')).write_text(s)
