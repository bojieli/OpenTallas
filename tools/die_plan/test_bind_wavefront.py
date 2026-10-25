"""Raw binder reset emission: lockstep published release offsets and wrong-parent mutant."""
import copy
import json
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import reset_tree as RT
import schema

HERE = Path(__file__).resolve().parent


def emitter(raw):
    """Smallest Binder vehicle: real raw emitters, reset-only physical partitions."""
    b = bind.Binder.__new__(bind.Binder)
    b.plan = raw
    b.plan_dir = HERE / "examples"
    b.ab = {'top': 'reset_fixture', 'default_clock': 'core'}
    b.types = raw['partition_types']
    b.parts = {p['name']: p for p in raw['partitions']}
    b.members = {p: [] for p in b.parts}
    b.by_type = defaultdict(list)
    for p in b.parts:
        b.by_type[b.parts[p]['type']].append(p)
    b.tparams = {t: {} for t in b.types}
    b.tvals = {t: {p: {} for p in ps} for t, ps in b.by_type.items()}
    b.F = SimpleNamespace(cells=[], top_ports={})
    b.G = SimpleNamespace(dirs={})
    b.clk_dom = defaultdict(lambda: {'core'})
    b.in_bus, b.out_bus, b.ft_bus, b.intra_dly = [defaultdict(list) for _ in range(4)]
    b.pc = None
    b.links = []
    b.io_used = {}
    return b


def plan():
    raw = json.loads((HERE/'examples/tiny_plan.json').read_text())
    raw.setdefault('reset', {})['release'] = 'wavefront'
    # Raw emitter fixture has no datapath; geometry and reset topology are unchanged.
    for ty in raw['partition_types'].values():
        ty.pop('contents', None)
    return raw


def test_raw_bind_emits_wavefront_and_prices_boot(tmp_path):
    raw = plan()
    b = emitter(raw)
    b.emit(tmp_path)
    W = json.loads((tmp_path/'bind_reset.json').read_text())
    top = (tmp_path/'rtl/tiny_bound_top.sv').read_text()
    for p, row in W['parts'].items():
        name = bind.sv_id(p)
        inst = re.search(rf'^    \w+ {name} \((.*?)\n    \);', top, re.S | re.M).group(1)
        if row['parent'] is None:
            assert '.arst_n(rst_n)' in inst
        else:
            net = 'rstw_' + re.sub(r'\W', '_', row['source'])
            assert f'.arst_n({net})' in inst
    for ty in raw['partition_types'].values():
        text = (tmp_path/'rtl'/f"{ty['module']}.sv").read_text()
        assert 'u_rst_sync' not in text
        assert 'u_rst_root' in text or 'u_rst_in' in text
    assert W == RT.wf_plan(schema.Plan(raw))
    assert W['max_release'] > 2  # publish added boot cycles; data latency unchanged


def simulate(tmp_path, mutant=False):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog missing')
    raw = plan()
    b = emitter(raw)
    files = b.emit(tmp_path)
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    if mutant:
        top = files[-1]
        text = top.read_text()
        text, n = re.subn(r'\.arst_n\(rstw_\w+\)', '.arst_n(rst_n)', text, count=1)
        assert n == 1
        top.write_text(text)
    checks = []
    for p, row in W['parts'].items():
        T = RT.for_type(P, row['type'])
        for k in range(len(T['taps'])):
            n = f"u.{bind.sv_id(p)}.rst_n_t{k}"
            checks.append(f"if (cyc >= 0 && {n} !== (cyc + 1 >= {row['release']})) bad = bad + 1;")
    mx = W['max_release']
    tb = tmp_path/'tb.sv'
    tb.write_text(f'''`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0; always #0.5 clk=~clk;
tiny_bound_top u(.clk_core(clk), .rst_n(rst_n));
integer cyc=-{mx+20}, bad=0;
always @(posedge clk) begin
 #0.1;
 {' '.join(checks)}
 if(cyc == -1) rst_n=1;
 cyc=cyc+1;
end
initial begin repeat({2*mx+40}) @(posedge clk); #0.2; $display("BAD %0d", bad); $finish; end
endmodule
''')
    exe = tmp_path/'a.out'
    subprocess.run(['iverilog','-g2012','-o',str(exe),str(tb),*[str(f) for f in files]], check=True)
    out = subprocess.run(['vvp',str(exe)], capture_output=True,text=True,check=True).stdout
    return int(re.search(r'BAD (\d+)',out).group(1))


def test_raw_bound_reset_lockstep_and_mutant(tmp_path):
    assert simulate(tmp_path/'good') == 0
    assert simulate(tmp_path/'mutant', mutant=True) > 0


def test_plan_relative_core_pin_table_without_lef_or_module_metadata(tmp_path):
    # Real QC tables identify their "core", not "module"; logical binds may
    # precede LEF generation. Only the declared plan directory is needed.
    raw = plan()
    table = tmp_path/'cores/a0_nk_pins.json'
    table.parent.mkdir()
    table.write_text(json.dumps({'core': 'actual_qc_core', 'pins': [
        {'name': 'rst_n', 'layer': 'M4', 'x': 0, 'y': 150}]}))
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_hc', module='actual_qc_core',
        lef='absent.lef', origin_um=[50, 50], outline_um=[200, 300],
        pins_file='cores/a0_nk_pins.json')]
    P = schema.Plan(raw, tmp_path/'die_plan.json')
    target, = RT.core_reset_targets(P, 'src')
    assert target['inst'] == 'u_hc' and target['pin'] == 'rst_n'
    assert target['pin_um'] == [50, 200]


def test_real_qc_coordinate_spelling_maps_local_reset_and_rejects_ambiguity(tmp_path):
    raw = plan()
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_t00', module='closed_a0',
        origin_um=[50, 50], outline_um=[200, 300],
        pins=[dict(name='rst_n', layer='M4', xy=[0, 150])])]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type'] == 'src')
    # Current QC physical name u_t00 is RTL u_t_0_0, and the hard abstract
    # module name differs from the unchanged original leaf module.
    c = SimpleNamespace(path='c16.u_t_0_0', ports={'rst_n': [1]}, module='original_a0', params={})
    b.F.cells = [c]
    b.G.dirs = {0: {'rst_n': 'input'}}
    b.G.kind = ['leaf']
    b.members[part] = [0]
    b.sinks = {(0, 'rst_n', 0): ('rst', 'low')}
    b.rel_of = lambda ci: 'u_t_0_0'
    text, _ = b.emit_type('src', part)
    target, = RT.for_type(b.wavefront_plan(), 'src')['core_resets']
    assert f'.rst_n(rst_n_t{target["tap"]})' in text
    b.F.cells.append(c)
    b.G.dirs[1] = {'rst_n': 'input'}
    b.sinks[(1, "rst_n", 0)] = ("rst", "low")
    b.members[part].append(1)
    with pytest.raises(bind.BindError, match='expected one bound leaf, found 2'):
        b.emit_type('src', part)


def test_contextless_pin_table_fallback_accepts_explicit_core_metadata(tmp_path, monkeypatch):
    raw = plan()
    repo = tmp_path/'repo'
    table = repo/'physical/die_plan/qc/cores/pins.json'
    table.parent.mkdir(parents=True)
    table.write_text(json.dumps({'core': 'actual_qc_core', 'pins': [
        {'name': 'rst_n', 'layer': 'M4', 'x': 0, 'y': 150}]}))
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_hc', module='actual_qc_core',
        lef='absent.lef', origin_um=[50, 50], outline_um=[200, 300], pins_file='cores/pins.json')]
    monkeypatch.setattr(RT, 'HERE', repo/'tools/die_plan')
    target, = RT.core_reset_targets(schema.Plan(raw), 'src')
    assert target['inst'] == 'u_hc' and target['pin_um'] == [50, 200]


def test_hbm_native_clock_source_is_excised_before_raw_wavefront_emit(tmp_path):
    # Actual hfd_ckgen_nolink interface/rule retained by the native B2 recipe.
    # The source rule removes its internal u_rs/u_rel rather than cascading a
    # native POR conditioner in front of the generated wavefront synchronizer.
    outputs = {f'pll_{d}': {'kind': 'clock', 'value': d} for d in ('stream', 'serial', 'hbm')}
    outputs.update({f'por_{d}': {'kind': 'reset', 'value': 'low'} for d in ('stream', 'serial', 'hbm')})
    source = dict(module='hfd_ckgen_nolink', outputs=outputs, drop_in=['refclk', 'por_n'])
    ports = {name: [k+3] for k, name in enumerate(outputs)}
    ports.update(refclk=[1], por_n=[2])
    cell = SimpleNamespace(path='hb_ckgen', module='hfd_ckgen_nolink', ytype='hfd_ckgen_nolink',
        kind='leaf', ports=ports, dirs={n: 'output' if n in outputs else 'input' for n in ports})
    F = SimpleNamespace(cells=[cell], const_drivers={},
        top_ports={'hb_ckgen__refclk': ('input', [1]), 'hb_ckgen__por_n': ('input', [2])})
    rules = dict(sources=[source], map=dict(parts={'hb_ckgen': 'pa'}))
    errors = []
    G = bind.Graph(F, bind.Rules(rules), errors)
    assert not errors and G.kind == ['source']
    assert G.source(ports['por_stream'][0]) == ('reset', 'low', 0)
    assert G.source(ports['pll_stream'][0]) == ('clock', 'stream')
    b = emitter(plan())
    b.F, b.G, b.R, b.errors = F, G, bind.Rules(rules), []
    b.map_cells()
    assert not b.cpart and not b.errors  # hb_ckgen is not a retained leaf
    for p in b.parts:
        b.members.setdefault(p, [])
    files = b.emit(tmp_path)
    assert all('hfd_ckgen_nolink hb_ckgen' not in f.read_text() for f in files)
    top = files[-1].read_text()
    assert 'input  wire rst_n' in top and '.arst_n(rst_n)' in top
    # Negative control: accidentally retaining the source turns the old native
    # conditioner back into a leaf, which this topology assertion must reject.
    bad = copy.deepcopy(rules)
    bad['sources'][0]['keep_leaf'] = True
    mutant = bind.Graph(F, bind.Rules(bad), [])
    b.G, b.R = mutant, bind.Rules(bad)
    b.map_cells()
    assert mutant.kind == ['leaf'] and b.cpart == {0: 'pa'}
