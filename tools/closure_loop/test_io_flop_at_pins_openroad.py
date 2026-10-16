"""Real OpenDB regression for branched data captures (no timing/netlist changes)."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / 'testdata/io_flop_at_pins'


def run_fixture(tmp_path, *, output_clone=False):
    if not shutil.which('openroad'):
        pytest.skip('OpenROAD required for actual OpenDB fixture')
    definition = (FIXTURE / 'test.def').read_text()
    if output_clone:
        definition = definition.replace('PINS 3 ;', 'PINS 4 ;').replace(
            'END PINS', '- clone_out + NET clone_out + DIRECTION OUTPUT + USE SIGNAL '
            '+ LAYER M1 ( -20 -20 ) ( 0 20 ) + FIXED ( 100000 10000 ) N ;\nEND PINS')
        definition = definition.replace('NETS 4 ;', 'NETS 5 ;').replace(
            'END NETS', '- clone_out ( PIN clone_out ) ( dup_a Q ) ;\nEND NETS')
    (tmp_path / 'test.def').write_text(definition)
    script = f'''read_lef {FIXTURE / 'test.lef'}
read_def {tmp_path / 'test.def'}
proc topology {{}} {{
  set result {{}}
  foreach net [[ord::get_db_block] getNets] {{
    set terms {{}}
    foreach it [$net getITerms] {{ lappend terms "[[$it getInst] getName]/[[$it getMTerm] getName]" }}
    foreach bt [$net getBTerms] {{ lappend terms "PORT/[$bt getName]" }}
    lappend result [list [$net getName] [lsort $terms]]
  }}
  return [lsort $result]
}}
set before [topology]
set ::env(RESULTS_DIR) {tmp_path}
sta::builtin_source {ROOT / 'physical/qwen_die_masters/io_flop_at_pins.tcl'}
if {{$before ne [topology]}} {{ error "placement changed connectivity" }}
set f [open {tmp_path / 'locations.txt'} w]
foreach inst [[ord::get_db_block] getInsts] {{ puts $f "[$inst getName] [$inst getLocation] [$inst getPlacementStatus]" }}
close $f
exit
'''
    (tmp_path / 'run.tcl').write_text(script)
    result = subprocess.run(['openroad', '-exit', '-no_init', str(tmp_path / 'run.tcl')],
                            capture_output=True, text=True, check=True)
    assert 'Error' not in result.stdout, result.stdout
    locations = {}
    for line in (tmp_path / 'locations.txt').read_text().splitlines():
        name, x, y, status = line.split()
        locations[name] = (int(x), int(y), status)
    return locations


@pytest.mark.parametrize('output_clone', [False, True])
def test_capture_anchors(tmp_path, output_clone):
    first = run_fixture(tmp_path, output_clone=output_clone)
    assert run_fixture(tmp_path, output_clone=output_clone) == first
    # Historical single-D placement is unchanged; old gap=1um and pin y=5um.
    assert first['single'] == (1000, 5000, 'FIRM')
    assert first['dup_a'][2] == first['dup_b'][2] == first['rr'][2] == 'FIRM'
    assert first['reset_load'] == (10000, 10000, 'PLACED')
    if output_clone:
        assert first['dup_a'] == (96800, 10000, 'FIRM')
        captures = ['dup_b', 'rr']
    else:
        captures = ['dup_a', 'dup_b', 'rr']
    # New captures are on the actual 1um site/row grid, inside core and disjoint
    # from one another and every existing FIRM footprint.
    for name in captures:
        x, y, _ = first[name]
        assert x % 1000 == y % 1000 == 0
        assert 0 <= x <= 98000 and 0 <= y <= 19000
        for other, (ox, oy, status) in first.items():
            if name == other or status != 'FIRM':
                continue
            assert x + 2000 <= ox or ox + 2000 <= x or y + 1000 <= oy or oy + 1000 <= y
