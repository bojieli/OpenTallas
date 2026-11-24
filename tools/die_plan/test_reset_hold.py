"""QC-RSTCNT 11-24: host-independent root stable counter reset.source.hold (dies without a PLL lock: QC, S81, HEAD).

The die root entry u_rst_root (2-flop sync on rst_n) is followed by the SAME ot_dp_lockq u_rst_lockq the KV PLL lock form
uses, with its qualifier tied high: the root releases stable_cycles + LOCKQ_EXTRA running clocks after the synchronised
rst_n release, whatever the host does.  Checks: schema + G0, one uniform release shift on every partition, only the
root type's tree changes, the bind emits no lock net, and an iverilog bench of the bound fixture releases every tap
exactly at its published (shifted) offset; after a 2-cycle host rst_n pulse every tap is still held >= 256 clocks."""
import copy
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
from test_bind_wavefront import emitter, plan as base_plan  # noqa: E402

STABLE = 5


def unique_root_plan():
    """the fixture with a unique reset-root type (QC: slw_sc_v1__cl63e5a7a2 has ONE part, sl_W0_sc; KV: hub_C)."""
    raw = base_plan()
    raw['partition_types']['root'] = copy.deepcopy(raw['partition_types']['mid'])
    raw['partition_types']['root']['module'] = 'tiny_root_part'
    next(p for p in raw['partitions'] if p['name'] == 'pm2')['type'] = 'root'
    return raw


def hold_plan(stable=STABLE):
    raw = unique_root_plan()
    raw['reset'].setdefault('source', {'part': '@die', 'bus': 'rst_n'})
    raw['reset']['source']['hold'] = {'stable_cycles': stable, 'note': 'test'}
    return raw


def test_schema_and_g0():
    raw = hold_plan()
    assert schema.validate(raw) == []
    P = schema.Plan(raw)
    assert RT.check_hold(P) == [] and RT.lock_stages(P) == STABLE + RT.LOCKQ_EXTRA
    assert RT.root_qualifier(P) == dict(inst=None, pin=None, tied=True, stable=STABLE)
    errs, _w, _i = RT.check(P)
    assert not [e for e in errs if 'hold' in e]
    bad = hold_plan()
    bad['reset']['source']['hold']['stable_cycles'] = 0
    assert schema.validate(bad) != []
    assert any('stable_cycles' in e for e in RT.check_hold(schema.Plan(bad)))
    both = hold_plan()
    both['reset']['source']['lock'] = {'inst': 'u_pll', 'pin': 'locked', 'stable_cycles': 4}
    both['reset']['source']['pad'] = 'io_x'
    assert any('ONE root qualifier' in e for e in RT.check_hold(schema.Plan(both)))
    nowf = hold_plan()
    nowf['reset']['release'] = 'region'
    assert any('wavefront' in e for e in RT.check_hold(schema.Plan(nowf)))


def test_no_hold_unchanged():
    P = schema.Plan(unique_root_plan())
    assert RT.hold_spec(P) is None and RT.root_qualifier(P) is None and RT.lock_stages(P) == 0


def test_uniform_release_shift_and_only_root_tree_changes():
    P0, P1 = schema.Plan(unique_root_plan()), schema.Plan(hold_plan())
    W0, W1 = RT.wf_plan(P0), RT.wf_plan(P1)
    sh = STABLE + RT.LOCKQ_EXTRA
    assert set(W0['parts']) == set(W1['parts'])
    assert {W1['parts'][p]['release'] - W0['parts'][p]['release'] for p in W0['parts']} == {sh}
    assert W1['max_release'] - W0['max_release'] == sh
    rtype = RT.wf_solve(P1)['root_type']
    assert rtype == 'root' and RT.wf_solve(P0)['root'] == RT.wf_solve(P1)['root'] == 'pm2'
    for tn in {r['type'] for r in W0['parts'].values()}:
        T0, T1 = RT.for_type(P0, tn), RT.for_type(P1, tn)
        if tn == rtype:
            assert T1['lock'] == dict(inst=None, pin=None, stable=STABLE, stages=sh, tied=True)
            assert RT.release_clocks(T1) - RT.release_clocks(T0) == sh
            txt = '\n'.join(RT.rtl_lines(T1))
            want = (f"ot_dp_lockq #(.STABLE({STABLE})) u_rst_lockq (.clk(clk), .d(rst_por_n), .locked(1'b1), "
                    ".q(rst_root_n))")
            assert want in txt
            assert RT.LOCK_SRC not in txt and 'sync_rst_n(rst_por_n)' in txt
        else:
            assert T1 == T0, tn


def simulate(tmp_path, stable=STABLE, pulse=None, published_shift=True, window=None):
    """clocks always run; the host drives rst_n low for `pulse` cycles (default: long) and releases it before cycle 0;
    every tap of every partition must be low from cycle 0 and release exactly at its published wavefront offset.
    stable=None: the plan without a counter.  window=W: check each tap only from W cycles before its release (a short
    host pulse reaches far taps late: they must still be held low for the W cycles before release)."""
    if not shutil.which('iverilog'):
        pytest.skip('iverilog missing')
    raw = hold_plan(stable) if stable else unique_root_plan()
    b = emitter(raw)
    files = b.emit(tmp_path)
    for f in files:
        assert RT.LOCK_SRC not in f.read_text()
    P = schema.Plan(raw)
    W = RT.wf_plan(P) if published_shift else RT.wf_plan(schema.Plan(unique_root_plan()))
    checks = []
    for p, row in W['parts'].items():
        T = RT.for_type(P, row['type'])
        for k in range(len(T['taps'])):
            n = f"u.{bind.sv_id(p)}.rst_n_t{k}"
            c0 = 0 if window is None else row['release'] - window
            checks.append(f"if (cyc >= {c0} && {n} !== (cyc + 1 >= {row['release']})) bad = bad + 1;")
    mx = W['max_release'] + (stable or 0) + RT.LOCKQ_EXTRA
    pulse = pulse or mx + 10
    tb = tmp_path / 'tb.sv'
    tb.write_text(f'''`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=1; always #0.5 clk=~clk;
tiny_bound_top u(.clk_core(clk), .rst_n(rst_n));
integer cyc=-{mx + 20}, bad=0;
always @(posedge clk) begin
 #0.1;
 {' '.join(checks)}
 if(cyc == -1 - {pulse}) rst_n=0;
 if(cyc == -1) rst_n=1;
 cyc=cyc+1;
end
initial begin repeat({2 * mx + 40}) @(posedge clk); #0.2; $display("BAD %0d", bad); $finish; end
endmodule
''')
    exe = tmp_path / 'a.out'
    subprocess.run(['iverilog', '-g2012', '-o', str(exe), str(tb), *[str(f) for f in files]], check=True)
    out = subprocess.run(['vvp', str(exe)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r'BAD (\d+)', out).group(1))


def test_bound_hold_releases_at_published_offsets(tmp_path):
    assert simulate(tmp_path / 'good') == 0


def test_bound_hold_offsets_without_shift_fail(tmp_path):
    # negative control: the un-shifted (no-counter) offsets are wrong for the counter RTL
    assert simulate(tmp_path / 'noshift', published_shift=False) > 0


def test_bound_hold_wide_counter(tmp_path):
    # 256 = the QC row value (9-bit counter)
    assert simulate(tmp_path / 'w256', stable=256) == 0


def test_short_host_pulse_is_held_by_the_counter(tmp_path):
    # host-independence: after a 2-cycle rst_n pulse every tap is still held low for >= 256 clocks (QC need 78) right
    # up to its published release (256-cycle counter)
    assert simulate(tmp_path / 'short256', stable=256, pulse=2, window=256) == 0
    # negative control: without the counter the same 2-cycle pulse holds the taps for ~2 clocks only
    assert simulate(tmp_path / 'short_none', stable=None, pulse=2, window=78) > 0


# bound native (gen_phys.install_bound_native_reset): the tied counter is verified exactly like the KV PLL lock form
HOLD = dict(inst=None, pin=None, stable=256, stages=256 + RT.LOCKQ_EXTRA, tied=True)


def _hold_fixture(tmp_path, mutate=lambda s: s):
    import gen_rtl
    from types import SimpleNamespace
    from test_bound_native_reset import tree
    t = tree('sync')
    t['lock'] = dict(HOLD)
    text = ('module top(input clk, arst_n);\n bound u_bound(.clk(clk), .arst_n(arst_n));\nendmodule\n'
            'module bound(input clk, arst_n);\n' + '\n'.join(RT.rtl_lines(t)) + '\nendmodule\n' + gen_rtl.CELLS)
    f = tmp_path / 'native.sv'
    f.write_text(mutate(text))
    p = SimpleNamespace(types={'t': dict(module='top', outline_um=[100, 100],
                                         clock=dict(landing_contract=dict(collector_tree=t)))})
    return p, f


def test_bound_native_tied_hold_verified(tmp_path):
    import gen_phys
    p, f = _hold_fixture(tmp_path)
    c = gen_phys.install_bound_native_reset(p, 't', [f])
    assert c['lock_qualifier']['path'] == 'u_bound.u_rst_lockq' and c['lock_qualifier']['tied'] is True
    assert c['lock_qualifier']['stable'] == 256 and c['lock_qualifier']['source'] == RT.HOLD_TIED


@pytest.mark.parametrize('mutation,match', [
    (lambda s: s.replace('#(.STABLE(256)) u_rst_lockq', '#(.STABLE(16)) u_rst_lockq'), 'STABLE differs'),
    (lambda s: s.replace(".locked(1'b1)", '.locked(rst_por_n)'), 'topology differs'),
    (lambda s: s.replace('module bound(input clk, arst_n);\n', 'module bound(input clk, arst_n);\n wire '
                         + RT.LOCK_SRC + ';\n assign ' + RT.LOCK_SRC + " = 1'b1;\n"), 'carries a lock source'),
    (lambda s: s.replace('.d(rst_por_n)', '.d(arst_n)'), 'topology differs'),
])
def test_bound_native_tied_hold_mutants_fail_closed(tmp_path, mutation, match):
    import gen_phys
    import gen_rtl
    p, f = _hold_fixture(tmp_path, mutation)
    with pytest.raises(gen_rtl.GenError, match=match):
        gen_phys.install_bound_native_reset(p, 't', [f])


# reset_hold_row: the plan row writer the composers call (QC C1i, S81 c9, HEAD)
def test_row_writer_uniform_and_refusals(tmp_path):
    import reset_hold_row as RHR
    import json as _j
    p = tmp_path / 'plan.json'
    p.write_text(_j.dumps(unique_root_plan()))
    new, rep = RHR.apply(_j.loads(p.read_text()), str(p), 256)
    assert new['reset']['source']['hold']['stable_cycles'] == 256
    assert rep['uniform'] and rep['release_shift'] == [256 + RT.LOCKQ_EXTRA] and rep['root'] == 'pm2'
    q = tmp_path / 'shared.json'
    q.write_text(_j.dumps(base_plan()))            # root type shared by two parts: non-uniform -> refused
    with pytest.raises(SystemExit, match='non-uniform'):
        RHR.apply(_j.loads(q.read_text()), str(q), 256)
    lk = unique_root_plan()
    lk['reset'].setdefault('source', {'part': '@die', 'bus': 'rst_n'})['lock'] = {'inst': 'u', 'pin': 'l'}
    with pytest.raises(SystemExit, match='PLL lock'):
        RHR.apply(lk, str(p), 256)
    assert RHR.cycles_from_need(78) == 128 and RHR.cycles_from_need(292) == 352 and RHR.cycles_from_need(113) == 160
    assert RHR.main([str(p), str(tmp_path / 'o.json'), '--cycles', '64']) == 0
    assert _j.loads((tmp_path / 'o.json').read_text())['reset']['source']['hold']['stable_cycles'] == 64
