"""Exercise planned-site assignment on actual Tcl, without an OpenROAD build."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G


def test_recipe_sites_are_pg_lattice_input_to_existing_hook():
    assert G.planned_clock_sites_text([], (939.6, 760.32)) == ''
    assert G.planned_clock_sites_text([[146.88, 699.84]], (939.6, 760.32)) == '{146.88 699.84}\n'
    for point in [[146.1,699.84],[4.32,699.84]]:
        try:G.planned_clock_sites_text([point],(939.6,760.32))
        except ValueError:pass
        else:raise AssertionError('illegal island accepted')


def test_actual_tcl_prunes_empty_sites_preserves_sinks_and_splits_load():
    source=Path(G.__file__).with_name('core_density_taps.tcl').read_text()
    start=source.index('proc dt_planned_groups ')
    end=source.index('\nset dt_taps {}',start)
    code=source[start:end]+'''
set pts {}
for {set k 0} {$k < 1300} {incr k} {lappend pts [list 5 5 "a$k"]}
for {set k 0} {$k < 20} {incr k} {lappend pts [list 995 5 "b$k"]}
lassign [dt_planned_groups $pts {{0 0} {1000 0} {5000 0}} 1250] groups sites
set counts [lmap g $groups {llength $g}]
puts "GROUPS:$counts SITES:$sites"
if {$counts ne {1250 50 20}} {error "lost sinks or target overflow"}
if {$sites ne {{0 0} {0 0} {1000 0}}} {error "nearest anchor or empty pruning failed"}
'''
    p=subprocess.run(['tclsh'],input=code,text=True,capture_output=True)
    assert p.returncode==0 and 'GROUPS:1250 50 20' in p.stdout, p.stdout+p.stderr
