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


def simulate_start(tmp_path, S=6, mutant=False):
    """OWNER DECISION 13c START broadcast through the RAW binder: rst_n released at cycle 0, die start at cycle S;
    every soft consumer tap releases at S + release[p], rst_o at release[p].  mutant: one start_i tied to the die pin."""
    if not shutil.which('iverilog'):
        pytest.skip('iverilog missing')
    raw = plan()
    raw['reset']['start'] = 'broadcast'
    b = emitter(raw)
    files = b.emit(tmp_path)
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    top = files[-1]
    text = top.read_text()
    assert 'input  wire start' in text
    if mutant:
        text, n = re.subn(r'\.start_i\(stw_\w+\)', '.start_i(start)', text, count=1)
        assert n == 1
        top.write_text(text)
    checks = []
    for p, row in W['parts'].items():
        if row['type'] not in W['types']:
            continue
        T = RT.for_type(P, row['type'])
        nck = T['n_clock_taps']
        for k in range(nck):
            n = f"u.{bind.sv_id(p)}.rst_n_t{k}"
            checks.append(f"if (cyc >= 0 && {n} !== (cyc + 1 >= {S + row['release']})) bad = bad + 1;")
        for k in range(len(T['outs'])):
            n = f"u.{bind.sv_id(p)}.rst_o_{k}"
            checks.append(f"if (cyc >= 0 && {n} !== (cyc + 1 >= {row['release']})) bad = bad + 1;")
    mx = W['max_release'] + S
    tb = tmp_path/'tb.sv'
    tb.write_text(f'''`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, start=0; always #0.5 clk=~clk;
tiny_bound_top u(.clk_core(clk), .rst_n(rst_n), .start(start));
integer cyc=-{mx+20}, bad=0;
always @(posedge clk) begin
 #0.1;
 {' '.join(checks)}
 if(cyc == -1) rst_n=1;
 if(cyc == {S - 1}) start=1;
 cyc=cyc+1;
end
initial begin repeat({2*mx+40}) @(posedge clk); #0.2; $display("BAD %0d", bad); $finish; end
endmodule
''')
    exe = tmp_path/'a.out'
    subprocess.run(['iverilog','-g2012','-o',str(exe),str(tb),*[str(f) for f in files]], check=True)
    out = subprocess.run(['vvp',str(exe)], capture_output=True,text=True,check=True).stdout
    return int(re.search(r'BAD (\d+)',out).group(1))


def test_raw_bound_start_broadcast_lockstep_and_mutant(tmp_path):
    assert simulate_start(tmp_path/'good') == 0
    assert simulate_start(tmp_path/'mutant', mutant=True) > 0


def _start_sink_fixture(role):
    raw = plan()
    raw['reset']['start'] = 'broadcast'
    raw['reset']['start_port'] = 'start'
    if role:
        raw['partition_types']['src']['reset']['start_role'] = role
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type'] == 'src')
    c = SimpleNamespace(path='hub.u_host', ports={'mission_start': [1], 'rst_n': [2]}, module='host', params={})
    b.F.cells = [c]
    b.F.top_ports = {'start': ('input', [1])}
    b.G.dirs = {0: {'mission_start': 'input', 'rst_n': 'input'}}
    b.G.kind = ['leaf']
    b.members[part] = [0]
    b.sinks = {(0, 'mission_start', 0): ('start',), (0, 'rst_n', 0): ('rst', 'low')}
    b.rel_of = lambda ci: 'u_host'
    return b, part


def test_start_consumer_binds_local_start_tap_only_in_bootstrap_type():
    """reset.start_port: the functional START level binds to the bootstrap partition's local registered START tap;
    its rst_n is the raw delivered wavefront tap; a mission type with a START consumer fails closed."""
    b, part = _start_sink_fixture('bootstrap')
    text, _ = b.emit_type('src', part)
    T = RT.for_type(b.wavefront_plan(), 'src')
    k = T['start_tap']
    assert f'.mission_start(start_t{k})' in text and f'ot_dp_rgate u_rrl_' in text and f'.q(start_t{k})' in text
    assert f'.rst_n(rst_n)' in text and 'io_start' not in text
    b, part = _start_sink_fixture(None)
    with pytest.raises(bind.BindError, match='only a reset.start_role'):
        b.emit_type('src', part)


def test_start_port_source_classified_not_die_io():
    raw = plan()
    raw['reset']['start_port'] = 'start'
    b = emitter(raw)
    from collections import Counter
    cnt = Counter()
    assert b._src_desc('pa', ('top', 'start', 0), cnt, 0, 'x', 0) == ('start',) and cnt['start'] == 1
    assert b._src_desc('pa', ('top', 'din', 3), cnt, 0, 'x', 0) == ('top', 'din', 3)


def test_raw_bound_bootstrap_type_lockstep(tmp_path):
    """bound die with type src bootstrap: src taps at release[p] (raw), every other soft tap at S + release[p];
    mutant = the bootstrap declaration dropped (src taps at S + release) is caught by the same checks."""
    if not shutil.which('iverilog'):
        pytest.skip('iverilog missing')

    def run(d, role):
        raw = plan()
        raw['reset']['start'] = 'broadcast'
        if role:
            raw['partition_types']['src']['reset']['start_role'] = role
        b = emitter(raw)
        files = b.emit(d)
        ref = plan()
        ref['reset']['start'] = 'broadcast'
        ref['partition_types']['src']['reset']['start_role'] = 'bootstrap'
        P = schema.Plan(ref)
        W = RT.wf_plan(P)
        S = 6
        checks = []
        for p, row in W['parts'].items():
            if row['type'] not in W['types']:
                continue
            T = RT.for_type(P, row['type'])
            boot = T.get('start_role') == 'bootstrap'
            for k in range(T['n_clock_taps']):
                rel = row['release'] if boot else S + row['release']
                checks.append(f"if (cyc >= 0 && u.{bind.sv_id(p)}.rst_n_t{k} !== (cyc + 1 >= {rel})) bad = bad + 1;")
            if boot and role == 'bootstrap':
                checks.append(f"if (cyc >= 0 && u.{bind.sv_id(p)}.start_t{T['start_tap']} !== "
                              f"(cyc + 1 >= {S + row['release']})) bad = bad + 1;")
        mx = W['max_release'] + S
        tb = d/'tb.sv'
        tb.write_text(f'''`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, start=0; always #0.5 clk=~clk;
tiny_bound_top u(.clk_core(clk), .rst_n(rst_n), .start(start));
integer cyc=-{mx+20}, bad=0;
always @(posedge clk) begin
 #0.1;
 {' '.join(checks)}
 if(cyc == -1) rst_n=1;
 if(cyc == {S - 1}) start=1;
 cyc=cyc+1;
end
initial begin repeat({2*mx+40}) @(posedge clk); #0.2; $display("BAD %0d", bad); $finish; end
endmodule
''')
        exe = d/'a.out'
        subprocess.run(['iverilog','-g2012','-o',str(exe),str(tb),*[str(f) for f in files]], check=True)
        out = subprocess.run(['vvp',str(exe)], capture_output=True,text=True,check=True).stdout
        return int(re.search(r'BAD (\d+)',out).group(1))
    assert run(tmp_path/'good', 'bootstrap') == 0
    assert run(tmp_path/'mutant', 'mission') > 0
