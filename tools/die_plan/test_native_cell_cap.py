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


# KV-HUBPV-1118 (OWNER 11-14 remove cell caps): the in-kit stop is deleted; over the one limit (400000) the count is only REPORTED, with or without a ruling id
@pytest.mark.parametrize('std,macros,over', [(0, 1, False), (400000, 3, False), (400001, 0, True)])
def test_actual_top_cell_cap_excludes_blocks(tmp_path, std, macros, over):
    result, count = run_cap(tmp_path, std, macros)
    assert result.returncode == 0, result.stderr
    assert count['stdcells'] == std and count['macros'] == macros and count['limit'] == 400000
    assert ('cell cap removed' in result.stdout) == over


@pytest.mark.parametrize('std,limit,waiver', [(473289, 517000, None), (517001, 900000, None), (420000, 450000, 'r590'), (473289, 517000, 'nope')])
def test_a_declared_native_limit_never_stops_the_run(tmp_path, std, limit, waiver):
    result, count = run_cap(tmp_path, std, 0, limit, waiver)
    assert result.returncode == 0, result.stderr
    assert count['stdcells'] == std
