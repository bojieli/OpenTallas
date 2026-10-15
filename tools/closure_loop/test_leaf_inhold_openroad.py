"""Actual OpenDB regression: one uniform input pad before multiple D captures."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / 'testdata/io_flop_at_pins'


@pytest.mark.parametrize('driver', ['', 'BUF_TEST'])
def test_multi_capture_input_pad(tmp_path, driver):
    if not shutil.which('openroad'):
        pytest.skip('OpenROAD required for actual OpenDB fixture')
    # The input-hold hook precedes netlist buffering. Use the direct two-D
    # version of the branched anchor fixture; arbitrary logic remains skipped.
    definition = (FIXTURE / 'test.def').read_text().replace('NETS 4 ;', 'NETS 3 ;')
    definition = definition.replace('( branch_buffer A )', '( dup_a D )')
    definition = definition.replace('- dup_branch ( branch_buffer Y ) ( dup_a D ) ;\n', '')
    (tmp_path / 'test.def').write_text(definition)
    script = f'''read_lef {FIXTURE / 'test.lef'}
read_def {tmp_path / 'test.def'}
set ::env(RESULTS_DIR) {tmp_path}
set ::env(OT_INHOLD_MASTER) BUF_TEST
set ::env(OT_INHOLD_DRV) {{{driver}}}
source {ROOT / 'physical/dsrom_window_source/leaf_inhold.tcl'}
set b [ord::get_db_block]
set f [open {tmp_path / 'connections.txt'} w]
foreach name {{single dup_a dup_b rr reset_load}} {{
  set i [$b findInst $name]
  foreach pin {{D RESETN}} {{
    set n [[$i findITerm $pin] getNet]
    if {{$n ne "NULL"}} {{ puts $f "$name/$pin [$n getName]" }}
  }}
}}
puts $f "PADS $ot_ih_n"
puts $f "FLOPS [llength [lsearch -all -inline -glob [lmap i [$b getInsts] {{ [$i getMaster] getName }}] *DFF*]]"
foreach pn $ot_ih_pnets {{ puts $f "PADNET [$pn getName] [$pn isDoNotTouch]" }}
close $f
exit
'''
    (tmp_path / 'run.tcl').write_text(script)
    result = subprocess.run(['openroad', '-exit', '-no_init', str(tmp_path / 'run.tcl')],
                            text=True, capture_output=True, check=True)
    assert 'Error' not in result.stdout, result.stdout
    lines = (tmp_path / 'connections.txt').read_text().splitlines()
    assert 'PADS 3' in lines and 'FLOPS 6' in lines
    connections = dict(line.split() for line in lines if '/' in line)
    prefix = 'ot_ihdrv_n' if driver else 'ot_inhold_n'
    assert connections['single/D'] == prefix + '00000'
    assert connections['dup_a/D'] == connections['dup_b/D'] == prefix + '00001'
    assert connections['rr/D'] == prefix + '00002'
    assert connections['reset_load/RESETN'] == 'rst_in'
    assert sorted(line for line in lines if line.startswith('PADNET')) == [
        'PADNET dup_in 1', 'PADNET rst_in 1', 'PADNET single_in 1']
    assert len((tmp_path / 'ot_inhold_firm.txt').read_text().split()) == (6 if driver else 0)
