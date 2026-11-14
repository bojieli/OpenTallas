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


def run_cap(tmp_path, std, macros, limit=None):
    out = tmp_path / 'count.json'
    script = Path(__file__).with_name('native_cell_cap.tcl').read_text().replace('/work/native_cell_count.json', str(out))
    pre = '' if limit is None else f'set ::ot_native_cell_limit {limit}\n'
    p = tmp_path / 'run.tcl'
    p.write_text(MOCK.replace('STD', str(std)).replace('MAC', str(macros)) + pre + script)
    return subprocess.run(['tclsh', str(p)], capture_output=True, text=True), json.loads(out.read_text())


@pytest.mark.parametrize('std,macros,fail', [(0, 1, False), (400000, 3, False), (400001, 0, False)])   # LIMIT-BIND-1: R-CAP removed, never fails
def test_actual_top_cell_cap_excludes_blocks(tmp_path, std, macros, fail):
    result, count = run_cap(tmp_path, std, macros)
    assert bool(result.returncode) == fail, result.stderr
    assert count['stdcells'] == std and count['macros'] == macros and count['limit'] == 400000
    if std > 400000:
        assert 'R-CAP removed' not in result.stderr and 'ADVISORY' in result.stdout


@pytest.mark.parametrize('std,limit,fail,seen', [(473289, 517000, False, 517000), (517000, 517000, False, 517000),
                                                 (517001, 517000, False, 517000), (517001, 900000, False, 517000),
                                                 (420000, 450000, False, 450000), (450001, 450000, False, 450000)])
def test_kit_limit_is_clamped_at_largest_closed_run(tmp_path, std, limit, fail, seen):
    result, count = run_cap(tmp_path, std, 0, limit)
    assert bool(result.returncode) == fail, result.stderr
    assert count['limit'] == seen
    if std > seen:
        assert f'above {seen}' in result.stdout and 'R-CAP removed' in result.stdout
    elif std > 400000:
        assert 'ADVISORY' in result.stdout
