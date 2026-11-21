import json
from pathlib import Path
import subprocess
import pytest

MOCK = '''namespace eval ord {proc get_db_block {} {return block}}
proc block {m} {return [concat [lrepeat STD stdinst] [lrepeat MAC macros]]}
proc stdinst {m} {return stdmaster}
proc macros {m} {return macromaster}
proc stdmaster {m} {return 0}
proc macromaster {m} {return 1}
'''


def run_cap(tmp_path, std, macros, limit=None, waiver=None):
    out = tmp_path / 'count.json'
    script = Path(__file__).with_name('native_cell_cap.tcl').read_text().replace('/work/native_cell_count.json', str(out)).replace('/work/CELL_WAIVER', str(tmp_path / 'CELL_WAIVER'))
    pre = '' if limit is None else f'set ::ot_native_cell_limit {limit}\n'
    if waiver:
        pre += f'set ::env(OT_CELL_WAIVER) {waiver}\n'
    p = tmp_path / 'run.tcl'
    p.write_text(MOCK.replace('STD', str(std)).replace('MAC', str(macros)) + pre + script)
    return subprocess.run(['tclsh', str(p)], capture_output=True, text=True), (json.loads(out.read_text()) if out.exists() else {})


# FLOW-OPS-0900 11-21 (CELL-CAP): over the one limit (400000 measured std cells, macros excluded) the kit STOPS at floorplan; the r703 waiver does not opt out
@pytest.mark.parametrize('std,macros,over', [(0, 1, False), (400000, 3, False), (400001, 0, True)])
def test_actual_top_cell_cap_excludes_blocks(tmp_path, std, macros, over):
    result, count = run_cap(tmp_path, std, macros)
    assert (result.returncode != 0) == over, result.stderr
    assert count['stdcells'] == std and count['macros'] == macros and count['limit'] == 400000
    assert ('OT_CELL_CAP STOP stage=floorplan' in result.stdout + result.stderr) == over


def test_cell_cap_stop_ignores_r703_and_honours_the_opt_out(tmp_path):
    result, _ = run_cap(tmp_path, 456000, 0, waiver='r703')
    assert result.returncode != 0 and 'OT_CELL_CAP STOP' in result.stdout
    out = tmp_path / 'count.json'
    script = Path(__file__).with_name('native_cell_cap.tcl').read_text().replace('/work/native_cell_count.json', str(out)).replace('/work/CELL_WAIVER', str(tmp_path / 'CELL_WAIVER'))
    script = script.replace('/work/CELL_CAP_STOP.json', str(tmp_path / 'stop.json')).replace('/work/cap_projection.json', str(tmp_path / 'proj.json'))
    p = tmp_path / 'off.tcl'
    p.write_text(MOCK.replace('STD', '456000').replace('MAC', '0') + 'set ::env(OT_CELL_CAP_STOP) 0\n' + script)
    r = subprocess.run(['tclsh', str(p)], capture_output=True, text=True)
    assert r.returncode == 0 and 'cell cap removed' in r.stdout


@pytest.mark.parametrize('std,limit,waiver', [(473289, 517000, None), (517001, 900000, None), (420000, 450000, 'r590'), (473289, 517000, 'nope')])
def test_a_declared_native_limit_stops_only_above_itself(tmp_path, std, limit, waiver):
    result, count = run_cap(tmp_path, std, 0, limit, waiver)
    assert result.returncode == 0, result.stderr
    assert count['stdcells'] == std
