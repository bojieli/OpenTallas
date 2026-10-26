"""TOKc-YOSYS 2026-10-22: Yosys < 0.68 dfflibmap swaps set/clear on ASAP7 DFFASRHQNx1; tools/yosys_pin.py guards it."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import yosys_pin as Y  # noqa: E402

HAVE_PINNED = Y.PINNED.exists()
HAVE_SIM = bool(shutil.which('iverilog') and shutil.which('vvp'))
try:
    LIB = Y.find_liberty()
except Y.YosysPinError:
    LIB = None
need_repro = pytest.mark.skipif(not (HAVE_SIM and LIB), reason='needs iverilog + the ASAP7 SEQ liberty')


def fake_yosys(tmp_path, text, name='yosys'):
    p = tmp_path / name
    p.write_text('#!/bin/sh\necho "%s"\n' % text)
    p.chmod(0o755)
    return str(p)


def test_parse_version():
    assert Y.parse_version('Yosys 0.52 (git sha1 fee39a3)') == (0, 52)
    assert Y.parse_version('Yosys 0.68+post (git sha1 UNKNOWN)') == (0, 68)
    assert Y.parse_version('Yosys 0.9 (git sha1 1979e0b)') == (0, 9)
    assert Y.parse_version('Yosys 1.2') == (1, 2)
    assert Y.parse_version('nonsense') is None


def test_guard_refuses_old_and_missing(tmp_path):
    old = fake_yosys(tmp_path, 'Yosys 0.52 (git sha1 fee39a3)')
    with pytest.raises(Y.YosysPinError, match=r'need >= 0\.68.*yosys-0\.68/bin/yosys'):
        Y.check(old)
    with pytest.raises(Y.YosysPinError, match='not found'):
        Y.check(str(tmp_path / 'absent'))
    with pytest.raises(Y.YosysPinError, match='need >= 0.68'):
        Y.pinned_yosys({'OT_YOSYS': old})          # an override is checked too, never trusted
    with pytest.raises(Y.YosysPinError):
        Y.pinned_yosys({'YOSYS': fake_yosys(tmp_path, 'garbage', 'y2')})


def test_guard_accepts_new(tmp_path):
    new = fake_yosys(tmp_path, 'Yosys 0.68+post (git sha1 UNKNOWN)')
    assert Y.check(new) == new
    assert Y.pinned_yosys({'OT_YOSYS': new}) == new
    assert Y.pinned_yosys({'YOSYS': fake_yosys(tmp_path, 'Yosys 1.0', 'y1')}).endswith('y1')


def test_cli_and_shell_guard(tmp_path):
    old = fake_yosys(tmp_path, 'Yosys 0.52 (git sha1 fee39a3)')
    r = subprocess.run([sys.executable, str(ROOT / 'tools/yosys_pin.py'), '--check', old], capture_output=True, text=True)
    assert r.returncode == 2 and 'need >= 0.68' in r.stderr
    env = dict(os.environ, OT_YOSYS=old)
    r = subprocess.run(['bash', '-c', 'source %s || exit 2; echo REACHED' % (ROOT / 'tools/yosys_pin.sh')],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 2 and 'REACHED' not in r.stdout and 'need Yosys >= 0.68' in r.stderr
    env['OT_YOSYS'] = fake_yosys(tmp_path, 'Yosys 0.68 (git sha1 38e001a6f)', 'y68')
    r = subprocess.run(['bash', '-c', 'source %s; echo "Y=$YOSYS"' % (ROOT / 'tools/yosys_pin.sh')],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout.strip() == 'Y=' + env['OT_YOSYS']


@need_repro
def test_liberty_ff_matches_model():
    assert Y.liberty_ff_ok(LIB)


@need_repro
def test_model_swap_detection():
    """The bench itself: a correct netlist passes, a set/clear-swapped one is flagged SWAPPED."""
    good = ('module ot_async_flop_repro(input clk, input rst_n, input d, output q0, output q1);\n'
            '  wire n0, n1;\n'
            '  DFFASRHQNx1_ASAP7_75t_R f0(.CLK(clk), .D(d), .RESETN(rst_n), .SETN(1\'b1), .QN(n0));\n'
            '  DFFASRHQNx1_ASAP7_75t_R f1(.CLK(clk), .D(d), .RESETN(1\'b1), .SETN(rst_n), .QN(n1));\n'
            '  assign q0 = ~n0, q1 = ~n1;\nendmodule\n')
    r = Y.simulate(good)
    assert r['ok'] and not r['swapped'] and r['async_cells'] == 2
    bad = good.replace('.RESETN(rst_n), .SETN(1\'b1)', '.RESETN(1\'b1), .SETN(rst_n)', 1) \
              .replace('.RESETN(1\'b1), .SETN(rst_n), .QN(n1)', '.RESETN(rst_n), .SETN(1\'b1), .QN(n1)', 1)
    r = Y.simulate(bad)
    assert not r['ok'] and r['swapped']


@need_repro
@pytest.mark.skipif(not HAVE_PINNED, reason='pinned Yosys 0.68 not installed')
def test_pinned_068_maps_async_flops_correctly():
    r = Y.repro(Y.PINNED)
    assert r['async_cells'] == 2 and r['ok'], r


@need_repro
@pytest.mark.skipif(not Path('/usr/bin/yosys').exists(), reason='no /usr/bin/yosys')
def test_system_yosys_status_is_what_the_guard_assumes():
    """Measured 10-22: /usr/bin/yosys 0.52 (fleet) and 0.9 (localhost) SWAP; 0.67/0.68+post (ORFS docker) and 0.68 OK.
    If a host's /usr/bin/yosys is < 0.68 it must show the swap (else the guard's premise changed: re-measure)."""
    v = Y.version('/usr/bin/yosys')
    r = Y.repro('/usr/bin/yosys')
    if v < Y.MIN_VERSION:
        assert r['swapped'], r
    else:
        assert r['ok'], r
