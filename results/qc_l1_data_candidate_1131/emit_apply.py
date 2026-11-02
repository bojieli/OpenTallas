import json
from pathlib import Path
r=Path(__file__).resolve().parent;m=json.loads((r/'candidate_manifest.json').read_text())
def q(s):
 assert '{' not in s and '}' not in s
 return '{'+s+'}'
s='''# PREPARED, UNEXECUTED. Source only after exact retained5_1 and joint MM context load.
set b [ord::get_db_block]
proc require {ok msg} {if {!$ok} {error $msg}}
proc terms {n} {
 set rows {};foreach t [$n getITerms] {lappend rows [list [[$t getInst] getName] [[[$t getInst] getMaster] getName] [[$t getMTerm] getName] [[$t getMTerm] getIoType]]};return [lsort $rows]
}
proc bterm_ids {b} {
 set out {};foreach t [$b getBTerms] {set n [$t getNet];set nn {};if {$n ne "NULL"} {set nn [$n getName]};lappend out [list [$t getName] [$t getIoType] [$t getSigType] $nn]};return [lsort $out]
}
source /work/connectivity_guard.tcl
set original_bterms [bterm_ids $b]
set original_cells {};foreach i [$b getInsts] {dict set original_cells [$i getName] [[$i getMaster] getName]}
set locked {};set clock_before {}
foreach n [$b getNets] {
 if {[$n getSigType] ne "CLOCK"} continue
 foreach t [$n getITerms] {
  set i [$t getInst];set nm [$i getName]
  set storig [$i getPlacementStatus];if {[dict exists $locked $nm]} {set storig [dict get $locked $nm]}
  lappend clock_before [list [$n getName] [$n isSpecial] $nm [[$i getMaster] getName] [[$t getMTerm] getName] [$t isSpecial] [$i getLocation] [$i getOrient] $storig]
  if {![dict exists $locked $nm]} {dict set locked $nm [$i getPlacementStatus];if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
 }
}
set clock_before [lsort $clock_before]
'''
for x in m['swaps']:
 s+=f'set i [$b findInst {q(x["inst"])}]\nrequire [expr {{$i ne "NULL" && [[$i getMaster] getName] eq {q(x["old_master"])}}}] {{old DATA master mismatch}}\nrequire [expr {{![dict exists $locked {q(x["inst"])}]}}] {{candidate is clock-connected}}\n'
 for pin,v in x['exact_old_connections'].items():
  # Build each expected row as a Tcl list, preserving exact native escapes.
  rows=' '.join('[list '+' '.join(q(t[k])for k in ['inst','master','pin','direction'])+']' for t in v['terms'])
  s+=f'set n [[$i findITerm {q(pin)}] getNet]\nrequire [expr {{[$n getName] eq {q(v["net"])}}}] {{DATA net mismatch}}\nrequire [expr {{[terms $n] eq [lsort [list {rows}]]}}] {{DATA fanout mismatch}}\n'
h=m['insert_buffer']
s+=f'''set sink [$b findInst {q(h['sink_inst'])}]
set sink_t [$sink findITerm D]
set old_net [$sink_t getNet]
require [expr {{[$old_net getName] eq {q(h['old_net'])}}}] {{hold net mismatch}}
require [expr {{[llength [$old_net getITerms]] == 2}}] {{hold branch no longer single sink}}
require [expr {{[$b findInst {q(h['inst'])}] eq "NULL" && [$b findNet {q(h['new_net'])}] eq "NULL"}}] {{candidate names already exist}}
global_route -start_incremental
'''
for x in m['swaps']:
 s+=f'replace_cell [get_cells {q(x["inst"])}] [lindex [get_lib_cells */{x["new_master"]}] 0]\n'
s+=f'''set bi [odb::dbInst_create $b [[ord::get_db] findMaster {q(h['master'])}] {q(h['inst'])}]
set nn [odb::dbNet_create $b {q(h['new_net'])}]
$nn setSigType SIGNAL
[$bi findITerm A] connect $old_net
[$bi findITerm Y] connect $nn
$sink_t disconnect
$sink_t connect $nn
lassign [$sink getLocation] hx hy
$bi setLocation $hx $hy
$bi setOrient [$sink getOrient]
$bi setPlacementStatus PLACED
source /work/pg_connect.tcl
ot_pg_connect_all l1_three_data_edits
ot_pg_require_bound l1_three_data_edits
detailed_placement
check_placement -verbose
set pf [open /work/candidate_placement.tsv w]
set prows {{}};foreach pi [$b getInsts] {{lappend prows [list [$pi getName] [[$pi getMaster] getName] [$pi getLocation] [$pi getOrient]]}}
foreach row [lsort $prows] {{puts $pf $row}};close $pf
set pdigest [lindex [exec sha256sum /work/candidate_placement.tsv] 0]
if {{$::env(CANDIDATE_PHASE) eq "place"}} {{
 write_db /work/candidate_place.odb
 source /work/geom_dump.tcl
 puts CANDIDATE_PLACE_COUPON_COMPLETE
 exit
}}
require [expr {{$::env(CANDIDATE_PHASE) eq "route" && $pdigest eq $::env(REVIEWED_PLACEMENT_SHA256)}}] {{unreviewed or nondeterministic actual placement; no route}}
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
# Final joint policy consumer runs AFTER this last physical/RC change. No broad repair.
ot_mm_sync
puts [format "CANDIDATE_FINAL TT %.6f FF %.6f" [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
ot_mm_unsync
dict for {{nm st}} $locked {{[$b findInst $nm] setPlacementStatus $st}}
set clock_after {{}}
foreach n [$b getNets] {{
 if {{[$n getSigType] ne "CLOCK"}} continue
 foreach t [$n getITerms] {{set i [$t getInst];lappend clock_after [list [$n getName] [$n isSpecial] [$i getName] [[$i getMaster] getName] [[$t getMTerm] getName] [$t isSpecial] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}}
}}
require [expr {{$clock_before eq [lsort $clock_after]}}] {{CLOCK identity/geometry/flags changed}}
dict for {{nm st}} $locked {{[$b findInst $nm] setPlacementStatus $st}}
set expected $original_cells
'''
for x in m['swaps']:s+=f'dict set expected {q(x["inst"])} {q(x["new_master"])}\n'
s+=f'''dict set expected {q(h['inst'])} {q(h['master'])}
set actual {{}};foreach i [$b getInsts] {{dict set actual [$i getName] [[$i getMaster] getName]}}
require [expr {{[lsort [dict keys $expected]] eq [lsort [dict keys $actual]]}}] {{extra/missing cell beyond three edits}}
dict for {{nm master}} $expected {{require [expr {{[dict get $actual $nm] eq $master}}] {{extra master mutation}}}}
write_guides $::env(RESULTS_DIR)/route.guide
write_db $::env(RESULTS_DIR)/5_1_grt.odb
set_mode ss
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
puts CANDIDATE_THREE_DATA_EDITS_COMPLETE
'''
s=s.replace('set clock_after {}','require [expr {$original_bterms eq [bterm_ids $b]}] {BTerm/source identity changed}\nset clock_after {}')
diff='''
set incidence_after [incidence $b]
set incidence_expected $incidence_before
set sink_key [list IT {SINK} D]
dict set incidence_expected $sink_key [list {NEWNET} SIGNAL 0 0]
dict set incidence_expected [list IT {NEWBUF} A] [list {OLDNET} SIGNAL 0 0]
dict set incidence_expected [list IT {NEWBUF} Y] [list {NEWNET} SIGNAL 0 0]
foreach p {VDD VSS} {
 set ref [dict get $incidence_before [list IT _145581_ $p]]
 set got [dict get $incidence_after [list IT {NEWBUF} $p]]
 require [expr {[lrange $got 0 2] eq [lrange $ref 0 2]}] {new BUF PG net differs from existing native supply}
 dict set incidence_expected [list IT {NEWBUF} $p] $got
}
require_same_dict $incidence_expected $incidence_after {undeclared existing signal/PG connectivity mutation}
set nets_expected $nets_before
dict set nets_expected {NEWNET} {SIGNAL 0}
require_same_dict $nets_expected [net_ids $b] {undeclared net creation/deletion/class mutation}
'''
for token,value in [('SINK',h['sink_inst']),('NEWNET',h['new_net']),('NEWBUF',h['inst']),('OLDNET',h['old_net'])]:diff=diff.replace('{'+token+'}',q(value))
s=s.replace('write_guides $::env(RESULTS_DIR)',diff+'write_guides $::env(RESULTS_DIR)')
guard='dict for {nm st} $locked {[$b findInst $nm] setPlacementStatus $st}\n'+s[s.index('require [expr {$original_bterms'):s.index('write_guides $::env(RESULTS_DIR)')]
s=s.replace('set pf [open /work/candidate_placement.tsv w]',guard+'set pf [open /work/candidate_placement.tsv w]')
s=s.replace('global_route -start_incremental','\nforeach master {BUFx2_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx6f_ASAP7_75t_R} {\n set found {};foreach lib [[ord::get_db] getLibs] {set mm [$lib findMaster $master];if {$mm ne "NULL"} {lappend found $mm}}\n require [expr {[llength $found]==1}] {target physical master does not uniquely resolve}\n set mm [lindex $found 0];set pins {}\n foreach p [$mm getMTerms] {lappend pins [list [$p getName] [$p getIoType] [$p getSigType]]}\n require [expr {[lsort $pins] eq [lsort {{A INPUT SIGNAL} {Y OUTPUT SIGNAL} {VDD INOUT POWER} {VSS INOUT GROUND}}]}] {target physical pin ABI mismatch}\n foreach lib {asap7sc7p5t_INVBUF_RVT_TT_nldm_211120 asap7sc7p5t_INVBUF_RVT_FF_nldm_211120} {\n  require [expr {[llength [get_lib_cells $lib/$master]]==1}] {selected target Libmaster missing or ambiguous}\n }\n}\n'+'global_route -start_incremental')
(r/'apply_candidate.tcl').write_text(s)
