"""Tests of the shared die-net repeater step (tools/die_repeaters).

Unit: config / Tcl generation / report judgement.  Integration (docker openroad/orfs:asap7lock, ~10 s; skipped when
docker or the image is missing): a 3-register die with 890-um register-to-register wires and a long clock net --
repeaters go in (BUFx4..8 only, <= 160 um apart), the clock net and the registers are untouched (PASS), and a mutant
repair that resizes a register and inserts a flop is caught (FAIL, non-zero exit).
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from die_repeaters import step  # noqa: E402

IMAGE = 'openroad/orfs:asap7lock'


def test_config_defaults_and_env(monkeypatch):
    for k in ('OT_DIE_REPAIR_MAX_WIRE', 'OT_DIE_REPAIR_SLEW', 'OT_DIE_REPAIR_SKIP', 'OT_DIE_REPAIR_OVER_REACH'):
        monkeypatch.delenv(k, raising=False)
    c = step.config('s81', '/work/r.json')
    assert c['max_wire_um'] == 160.0 and c['slew_ps'] == 260.0 and c['legalize'] == 'snap'
    assert 'n_clk_*' in c['skip_nets'] and c['over_reach'] == 'report'
    monkeypatch.setenv('OT_DIE_REPAIR_MAX_WIRE', '175')
    monkeypatch.setenv('OT_DIE_REPAIR_SKIP', 'foo_* bar')
    c = step.config('s81', '/work/r.json')
    assert c['max_wire_um'] == 175.0 and c['skip_nets'][-2:] == ['foo_*', 'bar']
    with pytest.raises(SystemExit):
        step.config('nope', 'x')
    with pytest.raises(SystemExit):
        step.config('hbm', 'x', over_reach='maybe')


def test_tcl_call_shape():
    t = step.tcl_call('hbm', '/work/out/die_repeaters.json', tcl_dir='/work', receiver_slew={'m_a': 240})
    assert 'source /work/die_repeaters.tcl' in t
    assert 'ot_die_repeaters [dict create' in t and 'max_wire_um 160' in t and 'slew_ps 260' in t
    assert 'receiver_slew {{m_a} 240}' in t and 'bounds_tcl {/work/cluster_bounds.tcl}' in t
    assert 'exit 3' in t and '{dk?_*}' in t


def test_cli_libs_file(capsys):
    assert step.main(['tcl', '--design', 's81', '--report', '/work/r.json', '--libs-file', '/kit/libs_tt.txt',
                      '--std-corner', 'TT']) == 0
    out = capsys.readouterr().out
    assert out.startswith('set ot_die_rep_libs {}')
    assert '[dict create libs [concat $ot_die_rep_libs {}] ' in out and 'std_corner {TT}' in out


def test_check(tmp_path):
    p = tmp_path / 'r.json'
    p.write_text(json.dumps(dict(schema='opentallas.die_repeaters.v1', verdict='PASS', violations=0, repeaters=3)))
    assert step.check(p)[0]
    p.write_text(json.dumps(dict(schema='opentallas.die_repeaters.v1', verdict='FAIL', violations=2)))
    assert not step.check(p)[0]
    assert not step.check(tmp_path / 'missing.json')[0]


DESIGN_V = '''module top(input clk, input d, output q);
  wire a, b, c;
  DFFHQNx1_ASAP7_75t_R r0 (.CLK(clk), .D(d), .QN(a));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(clk), .D(a), .QN(b));
  INVx1_ASAP7_75t_R g0 (.A(b), .Y(c));
  DFFHQNx1_ASAP7_75t_R r2 (.CLK(clk), .D(c), .QN(q));
endmodule
'''
SETUP_TCL = '''set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /work/t.v
foreach l [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] { read_liberty $l }
link_design top
initialize_floorplan -die_area {0 0 1200 200} -core_area {1.08 1.08 1198.8 198.72} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
foreach {i x} {r0 10 r1 900 g0 905 r2 60} { set inst [[ord::get_db_block] findInst $i]; $inst setLocation [expr {int($x*1000)}] 10800; $inst setPlacementStatus FIRM }
'''
MUTANT = '''rename repair_design ot_orig_repair_design
proc repair_design {args} { ot_orig_repair_design {*}$args
  replace_cell [get_cells r1] DFFHQNx2_ASAP7_75t_R
  set i [odb::dbInst_create [ord::get_db_block] [[ord::get_db] findMaster DFFHQNx1_ASAP7_75t_R] mut_flop]
  $i setLocation 500000 10800; $i setPlacementStatus PLACED }
'''
CHECK_TCL = '''foreach c [get_cells *] { puts "OT_CELL [get_full_name $c] [get_property $c ref_name]" }
puts "OT_CLKNET [llength [[[ord::get_db_block] findNet clk] getITerms]]"
'''


def _docker_ok():
    if not shutil.which('docker'):
        return False
    r = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True)
    return r.returncode == 0


def _run(tmp_path, mutant):
    w = tmp_path / ('mut' if mutant else 'base')
    w.mkdir()
    (w / 't.v').write_text(DESIGN_V)
    step.copy(w)
    call = step.tcl_call('cluster', '/work/die_repeaters.json', legalize='dpl', reach_um=400.0)
    (w / 'run.tcl').write_text(SETUP_TCL + (MUTANT if mutant else '') + call + CHECK_TCL)
    r = subprocess.run(['docker', 'run', '--rm', '--memory=2g', '-v', f'{w}:/work', IMAGE, 'bash', '-lc',
                        'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -no_splash -exit '
                        '/work/run.tcl; rc=$?; chmod -R a+rwX /work; exit $rc'], capture_output=True, text=True)
    return r, w


@pytest.mark.skipif(os.environ.get('OT_SKIP_DOCKER') == '1' or not _docker_ok(), reason='no docker / ORFS image')
def test_integration_pass_and_mutant(tmp_path):
    r, w = _run(tmp_path, False)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert rep['verdict'] == 'PASS' and rep['violations'] == 0
    assert rep['repeaters'] >= 10           # two ~890-um nets + the 600-um input -> >= 4-5 each at <= 160 um
    assert set(rep['repeaters_by_master']) <= set(step.BUFFERS)
    assert rep['skip_by']['clock_pin'] == 1 and rep['skip_nets_modified'] == 0
    assert rep['over_reach_nets'] >= 2 and rep['longest_um'] > 800    # reported (policy report), not failed
    cells = dict(l.split()[1:3] for l in r.stdout.splitlines() if l.startswith('OT_CELL'))
    assert cells['r0'] == cells['r1'] == cells['r2'] == 'DFFHQNx1_ASAP7_75t_R' and cells['g0'] == 'INVx1_ASAP7_75t_R'
    assert sum(1 for m in cells.values() if m.startswith('DFF')) == 3
    assert 'OT_CLKNET 3' in r.stdout          # clock net still drives exactly the 3 register clock pins
    ok, line = step.check(w / 'die_repeaters.json')
    assert ok, line
    r, w = _run(tmp_path, True)
    assert r.returncode == 3, r.stdout[-3000:]
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert rep['verdict'] == 'FAIL' and rep['resized'] == 1 and rep['non_buffer_inserted'] == 1
    assert not step.check(w / 'die_repeaters.json')[0]
