"""Check report attribution when multiple sources drive slices of one port."""
import gzip
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/s81/sta_path_classes.py'


def run_case(tmp_path, hops):
    plan = {'insts': [('a', 'real_a'), ('b', 'dsfd_rly_4_EW'),
                      ('p', 'placeholder_p'), ('d', 'real_d')], 'hops': hops}
    with gzip.open(tmp_path / 'plan.gz', 'wt') as f:
        json.dump(plan, f)
    (tmp_path / 'clock.json').write_text(json.dumps({'tiles': {
        m: {'view': 'placeholder_lib' if m == 'placeholder_p' else 'real'}
        for _, m in plan['insts']}}))
    (tmp_path / 'end.rpt').write_text('max_delay ck_col_0\n'
        'd/input[6] (real_d) 100 110 -10\n'
        'd/input[2] (real_d) 100 105 -5\n'
        'd/input[8] (real_d) 100 120 -20\n')
    result = subprocess.run([sys.executable, str(SCRIPT),
        str(tmp_path / 'plan.gz'), str(tmp_path / 'end.rpt'),
        str(tmp_path / 'clock.json'), str(tmp_path / 'out.json')],
        capture_output=True, text=True)
    return result, tmp_path / 'out.json'


def test_descending_slice_and_index_select_exact_master(tmp_path):
    result, output = run_case(tmp_path, [
        ['a', 'data', 4, 'a', 'out', 'd', 'input[7:4]', 50],
        ['b', 'data', 4, 'b', 'out', 'd', 'input[0:3]', 60],
        ['p', 'data', 1, 'p', 'out', 'd', 'input[8]', 70]])
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text())
    assert record['endpoints'] == record['violators'] == 3
    assert {r['launch']: (r['category'], r['wns_ps']) for r in record['classes']} == {
        'real_a.out': ('real_master_pair', -10),
        'dsfd_rly_4_EW.out': ('relay', -5),
        'placeholder_p.out': ('placeholder', -20)}


def test_overlapping_driver_slices_are_rejected(tmp_path):
    result, _ = run_case(tmp_path, [
        ['a', 'data', 8, 'a', 'out', 'd', 'input[7:0]', 50],
        ['b', 'data', 4, 'b', 'out', 'd', 'input[7:4]', 60]])
    assert result.returncode != 0
    assert 'ambiguous plan drivers' in result.stderr
