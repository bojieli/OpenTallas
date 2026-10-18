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
    assert c['max_wire_um'] == 160.0 and c['slew_ps'] == 260.0 and c['legalize'] == 'spread'
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


def test_check_warning_does_not_fail(tmp_path):
    p = tmp_path / 'r.json'
    p.write_text(json.dumps(dict(schema='opentallas.die_repeaters.v1', verdict='PASS', violations=0, repeaters=3,
                                 spread_max_disp_um=322.0, warnings=['repeater displaced 322.0 um > max_wire/2 = 80.0 um'])))
    ok, s = step.check(p)
    assert ok and 'WARN(1)' in s and 'max_disp=322.0' in s
    p.write_text(json.dumps(dict(schema='opentallas.die_repeaters.v1', verdict='PASS', violations=0, repeaters=3,
                                 spread_max_disp_um=51.15, warnings=[])))
    ok, s = step.check(p)
    assert ok and 'WARN' not in s


@pytest.mark.skipif(not shutil.which('tclsh'), reason='no tclsh')
def test_disp_warning_threshold(tmp_path):
    """the displacement rule alone (pure Tcl): warn only above max_wire/2; p4i 322 um warns, p4h/p4j 51 um does not"""
    tcl = Path(__file__).with_name('die_repeaters.tcl').read_text()
    body = tcl[tcl.index('proc ot_die_rep_disp_warning'):]
    body = body[:body.index('\nproc ', 1)]
    f = tmp_path / 't.tcl'
    f.write_text(body + '\nforeach {d m} {322.0 160 51.15 160 80.0 160 80.01 160 500 0} '
                 '{ puts "[expr {[ot_die_rep_disp_warning $d $m] ne {}}]" }\n')
    r = subprocess.run(['tclsh', str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ['1', '0', '0', '1', '0']


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
CHECK_TCL = '''set_routing_layers -signal M2-M7
global_route -allow_congestion
estimate_parasitics -global_routing
puts "OT_POSTGRT [ot_die_rep_post_grt_audit /work/post_grt.json]"
foreach c [get_cells *] { puts "OT_CELL [get_full_name $c] [get_property $c ref_name]" }
puts "OT_CLKNET [llength [[[ord::get_db_block] findNet clk] getITerms]]"
'''


def _docker_ok():
    if not shutil.which('docker'):
        return False
    r = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True)
    return r.returncode == 0


def _run(tmp_path, mutant, tag=None, check=True, design_v=DESIGN_V, setup=SETUP_TCL, legalize='dpl', extra='', **kw):
    w = tmp_path / (tag or ('mut' if mutant else 'base'))
    w.mkdir()
    (w / 't.v').write_text(design_v)
    step.copy(w)
    call = step.tcl_call('cluster', '/work/die_repeaters.json', legalize=legalize, reach_um=400.0, **kw)
    (w / 'run.tcl').write_text(setup + (MUTANT if mutant else '') + call + (CHECK_TCL if check else '') + extra)
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
    assert rep['post_slew_violators'] == 0 and rep['post_cap_violators'] == 0
    assert rep['post_violators_on_skip_nets'] == 3          # the 3 register clock pins on the untouched clock net
    assert rep['over_reach_nets'] >= 2 and rep['longest_um'] > 800    # reported (policy report), not failed
    cells = dict(l.split()[1:3] for l in r.stdout.splitlines() if l.startswith('OT_CELL'))
    assert cells['r0'] == cells['r1'] == cells['r2'] == 'DFFHQNx1_ASAP7_75t_R' and cells['g0'] == 'INVx1_ASAP7_75t_R'
    assert sum(1 for m in cells.values() if m.startswith('DFF')) == 3
    assert 'OT_CLKNET 3' in r.stdout          # clock net still drives exactly the 3 register clock pins
    pg = json.loads((w / 'post_grt.json').read_text())
    assert pg['schema'] == 'opentallas.die_repeaters.post_grt.v1' and pg['on_skip_nets'] == 3
    assert 'OT_POSTGRT %d' % (pg['slew_violators'] + pg['cap_violators']) in r.stdout
    ok, line = step.check(w / 'die_repeaters.json')
    assert ok, line
    r, w = _run(tmp_path, True)
    assert r.returncode == 3, r.stdout[-3000:]
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert rep['verdict'] == 'FAIL' and rep['resized'] == 1 and rep['non_buffer_inserted'] == 1
    assert not step.check(w / 'die_repeaters.json')[0]


@pytest.mark.skipif(os.environ.get('OT_SKIP_DOCKER') == '1' or not _docker_ok(), reason='no docker / ORFS image')
def test_repeat_nets_odb_match(tmp_path):
    # a clock-pin net named by repeat_nets is repeated (odb string match, bracket globs included); a glob that matches
    # nothing fails the step (S81-DV p4e: forwarded clocks silently left unrepeated)
    r, w = _run(tmp_path, False, tag='rep', check=False, repeat_nets=['cl[k]'])
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert r.returncode == 0 and rep['repeated_clock_nets'] == 1 and rep['skip_nets'] == 0, r.stdout[-2000:]
    r, w = _run(tmp_path, False, tag='none', check=False, repeat_nets=['n*_fck*'])
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert r.returncode == 3 and rep['verdict'] == 'FAIL' and rep['repeated_clock_nets'] == 0


# spread (DIE-FLOW2): a 24-bit bus of register pairs 890 um apart in one row band -- repair_design puts the 24 bits'
# repeaters at the same ideal points; spread must give each its own legal slot (no overlap, on the site grid, clear
# of the macro sitting across the bus), and the post-GRT audit re-buffers before judging.
NB = 24
BUS_V = ('module top(input clk, input [%d:0] d, output [%d:0] q);\n' % (NB - 1, NB - 1) + ''.join(
    f'  wire a{i};\n  DFFHQNx1_ASAP7_75t_R s{i} (.CLK(clk), .D(d[{i}]), .QN(a{i}));\n'
    f'  DFFHQNx1_ASAP7_75t_R e{i} (.CLK(clk), .D(a{i}), .QN(q[{i}]));\n' for i in range(NB)) + 'endmodule\n')
BUS_SETUP = SETUP_TCL.split('foreach {i x}')[0] + (
    'for {set i 0} {$i < %d} {incr i} { foreach {n x} [list s$i 10 e$i 900] { set inst [[ord::get_db_block] findInst $n]; '
    '$inst setLocation [expr {int($x*1000)}] [expr {10800 + 270*$i}]; $inst setPlacementStatus FIRM } }\n' % NB)
OVERLAP_TCL = '''set bad 0; set off 0; set boxes {}
foreach i [[ord::get_db_block] getInsts] { if {[string match s* [$i getName]] || [string match e* [$i getName]]} { continue }
  set b [$i getBBox]; lappend boxes [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  if {([$b xMin] % 54) != 0 || (([$b yMin] - 0) % 270) != 0} { incr off } }
set boxes [lsort -integer -index 0 $boxes]; set n [llength $boxes]
for {set a 0} {$a < $n} {incr a} { lassign [lindex $boxes $a] x0 y0 x1 y1
  for {set b [expr {$a + 1}]} {$b < $n} {incr b} { lassign [lindex $boxes $b] u0 v0 u1 v1; if {$u0 >= $x1} { break }
    if {$v0 < $y1 && $v1 > $y0} { incr bad } } }
puts "OT_OVERLAP $bad OT_OFFGRID $off OT_NEW $n"
'''


@pytest.mark.skipif(os.environ.get('OT_SKIP_DOCKER') == '1' or not _docker_ok(), reason='no docker / ORFS image')
def test_spread_no_stacking(tmp_path):
    r, w = _run(tmp_path, False, tag='spread', design_v=BUS_V, setup=BUS_SETUP, legalize='spread', extra=OVERLAP_TCL)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert rep['verdict'] == 'PASS' and rep['repeaters'] >= 4 * NB and rep['legalize'].startswith('spread')
    sp = json.loads((w / 'die_repeaters.spread1.json').read_text())
    assert sp['placed'] >= 4 * NB and sp['unplaced'] == 0
    line = [l for l in r.stdout.splitlines() if l.startswith('OT_OVERLAP')][0].split()
    assert line[1] == '0' and line[3] == '0', line      # no two repeaters overlap, all on the site / row grid
    assert int(line[5]) >= rep['repeaters']
    print('\n'.join(l for l in r.stdout.splitlines() if l.startswith('OT_')))
    assert rep['post_slew_violators'] == 0
    assert rep['warnings'] == [] and rep['spread_max_disp_um'] <= rep['max_wire_um'] / 2
    pg = json.loads((w / 'post_grt.json').read_text())
    assert 'rebuffer_rounds' in pg and pg['pre_existing_changed'] == 0 and pg['slew_violators'] == 0


# Q-DIE9 (f8e1095d0): a bus-bit clock net ('n_clk_r0[0]') skipped by clock pin must stay untouched.  The escaped STA
# lookup missed such names, so repair_design buffered 44 dv2f11 clock nets; the fix also marks the odb net do-not-touch.
BUSCK_V = DESIGN_V.replace('module top(input clk,', 'module top(input [1:0] n_clk_r0,').replace(
    '.CLK(clk)', '.CLK(n_clk_r0[0])')


@pytest.mark.skipif(os.environ.get('OT_SKIP_DOCKER') == '1' or not _docker_ok(), reason='no docker / ORFS image')
def test_bus_bit_clock_net_untouched(tmp_path):
    chk = CHECK_TCL.replace('findNet clk]', 'findNet {n_clk_r0[0]}]')
    r, w = _run(tmp_path, False, tag='busck', design_v=BUSCK_V, check=False, extra=chk)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rep = json.loads((w / 'die_repeaters.json').read_text())
    assert rep['verdict'] == 'PASS' and rep['skip_nets_modified'] == 0 and rep['repeaters'] >= 10
    assert 'n_clk_r0[0]' in (w / 'die_repeaters.skip_nets.txt').read_text().split()
    assert 'OT_CLKNET 3' in r.stdout, [l for l in r.stdout.splitlines() if l.startswith('OT_')]
    assert not any(l.split()[1].startswith('n_clk') or 'clk' in l.split()[1] for l in r.stdout.splitlines()
                   if l.startswith('OT_CELL') and l.split()[2].startswith('BUF')), r.stdout[-2000:]
