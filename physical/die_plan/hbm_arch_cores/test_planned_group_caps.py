from pathlib import Path
import subprocess

SOURCE=Path(__file__).with_name('core_density_taps.tcl').read_text()

def tcl(body):
 p=subprocess.run(['tclsh'],input=body,text=True,capture_output=True)
 assert p.returncode==0 and not p.stderr,p.stderr

def test_planned_split_groups_survive_distant_coincident_anchors():
 block=SOURCE[SOURCE.index('set dt_moved 0'):SOURCE.index('# F4 (QC')]
 setup='set dt_sets [list [lrepeat 1250 {1000 1000 it}] [lrepeat 50 {1000 1000 it}]]\nset dt_med {{0 0} {0 0}}\nset dt_dmax 80\n'
 for planned,counts in [(1,(1250,50)),(0,(1300,0))]:
  tcl(setup+f'set dt_planned_active {planned}\n'+block+f'\nif {{[llength $dt_asg(0)] != {counts[0]} || [llength $dt_asg(1)] != {counts[1]}}} {{error "split load collapsed"}}\n')

def test_pre_cts_f4_respects_planned_cap_without_changing_legacy_moves():
 start=SOURCE.index('proc dt_f4_group_move ');end=SOURCE.index('\ndict for {nm p} $dt_pt',start);proc=SOURCE[start:end]
 tcl(proc+r'''
set mapping [dict create a 0 b 1]
array set count {0 1250 1 50}
if {[dt_f4_group_move mapping count b 0 1250 1]} {error "planned cap exceeded"}
if {[dict get $mapping b] != 1 || $count(0) !=1250} {error "denied move changed state"}
if {![dt_f4_group_move mapping count a 1 1250 1] || $count(0)!=1249 || $count(1)!=51} {error "valid move rejected"}
if {![dt_f4_group_move mapping count a 0 10 0]} {error "legacy behavior changed"}
''')


def test_bounded_stray_reassignment_preserves_unplanned_capacity():
 block=SOURCE[SOURCE.index('set dt_moved 0'):SOURCE.index('# F4 (QC')]
 setup='set dt_sets [list [lrepeat 1250 {1000 1000 it}] [lrepeat 50 {1000 1000 it}]]\nset dt_med {{0 0} {0 0}}\nset dt_dmax 80\nset dt_target 1250\nset dt_planned_active 0\n'
 tcl('set ::env(OT_DTAP_BOUNDED_F4) 1\n'+setup+block+\
     '\nif {[llength $dt_asg(0)] !=1250 || [llength $dt_asg(1)] !=50} {error "bounded stray exceeded cap"}\n')


def test_bounded_f4_caps_load_and_prevents_transitive_spatial_drift():
 start=SOURCE.index('proc dt_f4_group_move ');end=SOURCE.index('\ndict for {nm p} $dt_pt',start)
 tcl(SOURCE[start:end]+r'''
set mapping [dict create a 0 b 1 c 2]
array set count {0 1250 1 50 2 20}
# Full target rejects even a local capture, without any partial mutation.
if {[dt_f4_group_move mapping count b 0 1250 0 1 {10 0} {0 0} 80]} {error "unplanned F4 cap exceeded"}
if {[dict get $mapping b] !=1 || $count(0)!=1250 || $count(1)!=50} {error "denied cap move changed state"}
# A nearby launch in group1 must not drag this capture beyond the tap radius.
if {[dt_f4_group_move mapping count c 1 1250 0 1 {81 0} {0 0} 80]} {error "transitive drift allowed"}
if {[dict get $mapping c] !=2 || $count(2)!=20 || $count(1)!=50} {error "denied radius move changed state"}
# Exact radius and available capacity remain usable and conserve sink count.
if {![dt_f4_group_move mapping count c 1 1250 0 1 {50 30} {0 0} 80]} {error "valid bounded move rejected"}
if {$count(1)!=51 || $count(2)!=19 || [dict get $mapping c]!=1} {error "move did not conserve counts"}
''')
