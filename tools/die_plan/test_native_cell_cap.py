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


# WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 D): over the one limit (400000) the run stops unless a ruling id waives it
@pytest.mark.parametrize('std,macros,fail', [(0, 1, False), (400000, 3, False), (400001, 0, True)])
def test_actual_top_cell_cap_excludes_blocks(tmp_path, std, macros, fail):
    result, count = run_cap(tmp_path, std, macros)
    assert bool(result.returncode) == fail, result.stderr
    if fail:
        assert 'SPLIT-NEEDED' in result.stderr and 'run cap' in result.stderr
    else:
        assert count['stdcells'] == std and count['macros'] == macros and count['limit'] == 400000


@pytest.mark.parametrize('std,limit,waiver,fail', [(473289, 517000, None, True), (517001, 900000, None, True), (420000, 450000, None, True),
                                                   (420000, 450000, 'r590', False), (517001, 900000, 'r590', False), (473289, 517000, 'nope', True)])
def test_a_declared_native_limit_needs_a_ruling_waiver(tmp_path, std, limit, waiver, fail):
    result, count = run_cap(tmp_path, std, 0, limit, waiver)
    assert bool(result.returncode) == fail, result.stderr
    if not fail:
        assert 'WAIVED by r590' in result.stdout
