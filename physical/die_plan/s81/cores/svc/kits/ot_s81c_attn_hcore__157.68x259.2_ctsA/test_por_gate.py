"""PATH-KV-POR 10-25: the die reset PAD seam (PATH-KV DECISION 14:19 + CLOCK-RESET amendments A/B).

Raw binder fixture (tiny plan, unique root type): pad_por_n = the die reset root pin; its loads are only the root
synchroniser u_rst_root and the PLL analog por_n; the PLL lock qualifies the root release through ot_dp_lockq; the
sys_c-like D2D por_n and a lock-driven kvs_ctl por_n are rebound to their partition's raw wavefront reset (bootstrap).
Mutants (raw pad into the D2D partition, combinational por_n & locked at the root synchroniser, mission-role D2D type)
must FAIL the gate; a simulation proves the published offsets (lock stages included) and the sticky lock release."""
import copy
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import por_gate  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
from test_bind_wavefront import emitter, plan as base_plan  # noqa: E402

STABLE = 4


def pad_plan(role='bootstrap', lock=True):
    raw = base_plan()
    raw['reset']['start'] = 'broadcast'
    # unique root type (KV: hub_C): pm2 sits at the die rst_n pin
    raw['partition_types']['root'] = copy.deepcopy(raw['partition_types']['mid'])
    raw['partition_types']['root']['module'] = 'tiny_root_part'
    next(p for p in raw['partitions'] if p['name'] == 'pm2')['type'] = 'root'
    P0 = schema.Plan(copy.deepcopy(raw))
    x, y = RT.die_root_um(P0)
    raw['die']['io'] = [dict(name='io_pad_por_n', kind='die_root_pad', iface='reset', part='pm2', sites=1,
                             rect_um=[x - 4.32, y - 4.32, x + 4.32, y + 4.32], pad_port='pad_por_n')]
    src = dict(part='@die', bus='rst_n', pad='io_pad_por_n', analog_loads=[dict(inst='u_pll', pin='por_n')],
               por_pins='por_n')
    if lock:
        src['lock'] = dict(inst='u_pll', pin='locked', stable_cycles=STABLE)
    raw['reset']['source'] = src
    for tn in ('src', 'root'):
        if role:
            raw['partition_types'][tn].setdefault('reset', {})['start_role'] = role
    return raw


CELLS = [('pll', 'qkd_pll_analog_model', {'por_n': 'input', 'locked': 'output'}, 'pm2'),
         ('kvs_ctl', 'qkd_kvs_ctl_m', {'por_n': 'input', 'q': 'output'}, 'pm2'),
         ('d2d_kv', 'qkd_d2d_m', {'por_n': 'input', 'q': 'output'}, 'pa')]


def binder(raw):
    b = emitter(raw)
    b.F.cells = [SimpleNamespace(path=p, ports={k: [100 + 10 * i + j] for j, k in enumerate(d)}, module=m, params={})
                 for i, (p, m, d, _pt) in enumerate(CELLS)]
    b.F.top_ports = {'pad_por_n': ('input', [1])}
    b.G.dirs = {i: dict(d) for i, (_p, _m, d, _pt) in enumerate(CELLS)}
    b.G.kind = ['leaf'] * len(CELLS)
    b.rel_of = lambda ci: CELLS[ci][0]
    for i, (_p, _m, _d, pt) in enumerate(CELLS):
        b.members[pt].append(i)
    cnt = Counter()
    b.sinks = {(0, 'por_n', 0): b._classify('pm2', 0, 'por_n', 0, ('top', 'pad_por_n', 0, 0), cnt),
               (1, 'por_n', 0): b._classify('pm2', 1, 'por_n', 0, ('pin', 0, 'locked', 0, 0), cnt),
               (2, 'por_n', 0): b._classify('pa', 2, 'por_n', 0, ('top', 'pad_por_n', 0, 0), cnt)}
    b.counts_por = cnt
    return b


LEAVES = '''`timescale 1ns/1ps
module qkd_pll_analog_model (input wire por_n, output reg locked);
  // behavioural PLL: lock after LOCK_NS of por_n release, lock drops on demand from the bench (tb.drop)
  initial locked = 0;
  always @(por_n or tb.drop) if (!por_n || tb.drop) locked = 0; else locked = #(tb.LOCK_NS) 1;
endmodule
module qkd_kvs_ctl_m (input wire por_n, output wire q); assign q = por_n; endmodule
module qkd_d2d_m (input wire por_n, output wire q); assign q = por_n; endmodule
'''


def test_classify_rebinds_and_analog():
    b = binder(pad_plan())
    assert b.sinks[(0, 'por_n', 0)] == ('rootpad',)
    assert b.sinks[(1, 'por_n', 0)] == ('rst', 'low') and b.sinks[(2, 'por_n', 0)] == ('rst', 'low')
    assert {r['pin'] for r in b.por_rebinds} == {'kvs_ctl.por_n', 'd2d_kv.por_n'}
    assert b.counts_por['por_rebind'] == 2 and b.counts_por['por_pad_analog'] == 1


def test_plan_pad_rules():
    P = schema.Plan(pad_plan())
    assert RT.check_pad(P) == [] and RT.die_reset_port(P) == 'pad_por_n' and RT.lock_stages(P) == STABLE + 3
    assert RT.pad_false_path_pins(P, 'root') == ['u_rst_root/async_rst_n', 'u_pll/por_n']
    assert RT.pad_false_path_pins(P, 'src') == []
    raw = pad_plan()
    raw['die']['io'][0]['part'] = 'pa'
    assert any('not the reset root partition' in e for e in RT.check_pad(schema.Plan(raw)))
    raw = pad_plan(lock=False)
    assert any('lock' in e for e in RT.check_pad(schema.Plan(raw)))
    raw = pad_plan()
    raw['die']['io'].append(dict(raw['die']['io'][0], name='io_rst2'))
    assert any('exactly ONE' in e for e in RT.check_pad(schema.Plan(raw)))
    assert schema.validate(pad_plan()) == []


def test_bind_emits_one_pad_and_gate_passes(tmp_path):
    b = binder(pad_plan())
    files = b.emit(tmp_path)
    g = json.loads((tmp_path / 'bind_por_gate.json').read_text())
    assert g['verdict'] == 'PASS', g['errors']
    top = files[-1].read_text()
    assert 'input  wire pad_por_n' in top and 'input  wire rst_n' not in top
    assert len(re.findall(r'\(pad_por_n\)', top)) == 1 and '.arst_n(pad_por_n)' in top
    root = (tmp_path / 'rtl/tiny_root_part.sv').read_text()
    assert '.async_rst_n(arst_n)' in root and '.por_n(arst_n)' in root and 'u_rst_lockq' in root
    src = (tmp_path / 'rtl/tiny_src_part.sv').read_text()
    assert 'io_pad_por_n' not in src and '.por_n(rst_n)' in src
    assert g['rebind_types']['src'] == {'role': 'bootstrap', 'raw_leaf_tap': True}


def _mutate(tmp_path, fn):
    b = binder(pad_plan())
    b.emit(tmp_path)
    fn(tmp_path / 'rtl')
    P = b.wavefront_plan()
    return por_gate.check(P, tmp_path / 'rtl', json.loads((tmp_path / 'bind_por.json').read_text()))


def test_mutant_raw_pad_into_d2d_partition_fails(tmp_path):
    def fn(d):
        top = d / 'tiny_bound_top.sv'
        t = top.read_text()
        t, n = re.subn(r'(    tiny_src_part (?:#\(.*?\) )?pa \(\n)', r'\1        .io_pad_por_n(pad_por_n),\n', t, flags=re.S)
        assert n == 1
        top.write_text(t)
        s = d / 'tiny_src_part.sv'
        t = s.read_text().replace('    input  wire clk,', '    input  wire clk,\n    input  wire [0:0] io_pad_por_n,', 1)
        t = t.replace('.por_n(rst_n)', '.por_n(io_pad_por_n[0])', 1)
        s.write_text(t)
    g = _mutate(tmp_path, fn)
    assert g['verdict'] == 'FAIL'
    assert any(e.startswith('G1') for e in g['errors']) and any('io_pad_por_n' in e for e in g['errors'])


def test_mutant_combinational_lock_and_fails(tmp_path):
    def fn(d):
        f = d / 'tiny_root_part.sv'
        t = f.read_text()
        assert '.async_rst_n(arst_n)' in t
        f.write_text(t.replace('.async_rst_n(arst_n)', '.async_rst_n(arst_n & pll_locked_i)', 1))
    g = _mutate(tmp_path, fn)
    assert g['verdict'] == 'FAIL' and any(e.startswith('G2') for e in g['errors'])


def test_mutant_mission_role_fails_closed():
    raw = pad_plan(role=None)
    b = binder(raw)
    with pytest.raises(bind.BindError, match='G4'):
        b.emit(Path('/tmp') / f'por_gate_mission_{id(b)}')


def simulate(tmp_path, lock_ns=0.3, drop_at=None, late_lock_cycles=0):
    """bench: pad released at cycle 0, START never asserted.  Checks every soft tap release against the published
    offsets (+ late_lock_cycles when the PLL locks after the root synchroniser releases), the rebound POR leaves at
    their partition's release (bootstrap: no START), and the lock drop after release (sticky: no reset)."""
    if not shutil.which('iverilog'):
        pytest.skip('iverilog missing')
    b = binder(pad_plan())
    files = b.emit(tmp_path)
    P = b.wavefront_plan()
    W = RT.wf_plan(P)
    checks = []
    for p, row in W['parts'].items():
        T = RT.for_type(P, row['type'])
        rel = row['release'] + late_lock_cycles
        if T.get('start_role') == 'bootstrap':
            for k in range(T['n_clock_taps']):
                checks.append(f"if (cyc >= 0 && u.{bind.sv_id(p)}.rst_n_t{k} !== (cyc + 1 >= {rel})) bad = bad + 1;")
        else:   # mission: START never comes -> never released
            for k in range(T['n_clock_taps']):
                checks.append(f"if (cyc >= 0 && u.{bind.sv_id(p)}.rst_n_t{k} !== 1'b0) bad = bad + 1;")
    for p, leaf in (('pa', 'u_d2d_kv'), ('pm2', 'u_kvs_ctl')):
        rel = W['parts'][p]['release'] + late_lock_cycles
        checks.append(f"if (cyc >= 0 && u.{p}.{leaf}.por_n !== (cyc + 1 >= {rel})) bad = bad + 1;")
    mx = W['max_release'] + late_lock_cycles
    tb = tmp_path / 'tb.sv'
    tb.write_text(f'''`timescale 1ns/1ps
module tb;
real LOCK_NS = {lock_ns};
reg clk=0, pad=0, start=0, drop=0; always #0.5 clk=~clk;
tiny_bound_top u(.clk_core(clk), .pad_por_n(pad), .start(start));
integer cyc=-{mx + 20}, bad=0;
always @(posedge clk) begin
 #0.1;
 {' '.join(checks)}
 if(cyc == -1) pad=1;
 if(cyc == {drop_at if drop_at is not None else -10**6}) drop=1;
 cyc=cyc+1;
end
initial begin repeat({2 * mx + 60}) @(posedge clk); #0.2; $display("BAD %0d", bad); $finish; end
endmodule
''')
    (tmp_path / 'leaves.sv').write_text(LEAVES)
    exe = tmp_path / 'a.out'
    subprocess.run(['iverilog', '-g2012', '-o', str(exe), str(tb), str(tmp_path / 'leaves.sv'),
                    *[str(f) for f in files]], check=True)
    out = subprocess.run(['vvp', str(exe)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r'BAD (\d+)', out).group(1))


def test_published_offsets_with_lock_stages(tmp_path):
    assert simulate(tmp_path / 'good') == 0


def test_lock_loss_after_release_is_not_a_die_reset(tmp_path):
    P = schema.Plan(pad_plan())
    assert simulate(tmp_path / 'drop', drop_at=RT.wf_plan(P)['max_release'] + 5) == 0


def test_late_lock_shifts_release_and_offsets_catch_it(tmp_path):
    # PLL locks 10 cycles late: the published (lock-already-stable) offsets are then off by exactly 10 ...
    assert simulate(tmp_path / 'late_bad', lock_ns=12.3) > 0
    # ... and every release is exactly the static offset after the lock-qualified root release
    assert simulate(tmp_path / 'late', lock_ns=12.3, late_lock_cycles=10) == 0


def test_root_kit_sdc_pad_false_path_only(tmp_path):
    """root kit SDC: exactly one raw-pad false path to {u_rst_root async, PLL analog}; anything wider FAILs lint."""
    import gen_phys
    import sdc_lint
    P = schema.Plan(pad_plan())
    fp = RT.pad_false_path_pins(P, 'root')
    assert sorted(fp) == ['u_pll/por_n', 'u_rst_root/async_rst_n']
    assert RT.pad_false_path_pins(P, 'src') == []
    txt = gen_phys.sdc(P, 'root', gen_phys.type_pins(P, 'root'))
    ctx = sdc_lint.kit_context(P, 'root')
    assert txt.count('set_false_path') == 1
    assert sdc_lint.lint(txt, **ctx) == []
    line = next(x for x in txt.splitlines() if x.startswith('set_false_path'))
    wide = txt.replace(line, 'set_false_path -from [get_ports arst_n]')
    assert any('reset pad' in e for e in sdc_lint.lint(wide, **ctx))
    extra = txt.replace(line, line.replace('u_pll/por_n', 'u_pll/por_n u_rst_lockq/d'))
    assert any('reset pad' in e for e in sdc_lint.lint(extra, **ctx))
    assert any('reset pad' in e for e in sdc_lint.lint(txt.replace(line, ''), **ctx))
    # a non-root type carries no raw pad: the same false path there is refused
    ts = gen_phys.sdc(P, 'src', gen_phys.type_pins(P, 'src'))
    assert 'set_false_path' not in ts
    assert sdc_lint.lint(ts + line + '\n', **sdc_lint.kit_context(P, 'src'))
