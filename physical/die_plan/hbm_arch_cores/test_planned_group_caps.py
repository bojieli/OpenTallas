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
