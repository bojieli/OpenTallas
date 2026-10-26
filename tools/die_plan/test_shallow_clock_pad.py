"""Sub-tap padding sizer + Tcl chain mechanics (PATH-QC-N59-PAD 10-25)."""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import pytest

FLOW = Path(__file__).resolve().parents[2] / 'physical/common_flow'
SPEC = importlib.util.spec_from_file_location('shallow_pad', FLOW/'shallow_clock_pad.py')
PAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAD)


def row(tap, target, nat, mean, n, kind='reg'):
    return dict(tap=tap, kind=kind, target_ps=target, natural_ps=nat, mean_ps=mean, n_now=n)


def test_first_pass_sizes_from_natural_with_default_stage():
    out, s = PAD.size([row('a', 250, 167.3, 167.3, 0), row('m', 232.5, 169, 169, 0, 'mac')], default_stage=15)
    assert [o['n_new'] for o in out] == [6, 4]   # 82.7/15 -> 6, 63.5/15 -> 4
    assert s['changed'] == 2 and s['stages'] == 10


def test_second_pass_uses_measured_per_tap_stage_delay():
    out, _ = PAD.size([row('a', 250, 170, 230, 4)], default_stage=15)   # 15 ps/stage measured -> 80/15 = 5
    assert out[0]['n_new'] == 5 and out[0]['stage_ps'] == 15.0


def test_converged_tap_keeps_its_chain_and_over_target_tap_gets_none():
    out, s = PAD.size([row('a', 250, 200, 247, 3), row('b', 250, 270, 270, 0)], tol=6)
    assert out[0]['n_new'] == 3 and out[1]['n_new'] == 0
    assert s['natural_over_target'] == 1 and s['changed'] == 0


def test_stage_cap_and_non_finite_measurement():
    out, _ = PAD.size([row('a', 900, 100, 100, 0)], default_stage=10, max_stages=16)
    assert out[0]['n_new'] == 16
    with pytest.raises(ValueError):
        PAD.size([row('a', 250, 'nan', 100, 0)])


def test_cli_roundtrip(tmp_path):
    m = tmp_path/'m.tsv'
    m.write_text('tap\tkind\ttarget_ps\tnatural_ps\tmean_ps\tn_now\nx\treg\t250\t190\t190\t0\n')
    p = subprocess.run(['python3', str(FLOW/'shallow_clock_pad.py'), str(m), '--out', str(tmp_path/'o.tsv')],
                       capture_output=True, text=True, check=True)
    assert '"stages": 4' in p.stdout
    assert (tmp_path/'o.tsv').read_text().splitlines()[1].split('\t')[:2] == ['x', '4']


def test_tcl_loads_without_side_effects():
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    p = subprocess.run(['tclsh'], input=f'source {{{FLOW/"shallow_clock_pad.tcl"}}}\n'
                       'puts "CH [dict size $::ot_dtsh_pad::chains] CTS=[info commands ::clock_tree_synthesis]"\n'
                       'puts [::ot_dtsh_pad::json_int {{"taps": 3, "changed": 0}} changed]\n',
                       text=True, capture_output=True)
    assert not p.stderr, p.stderr
    assert 'CH 0 CTS=\n0\n' in p.stdout
