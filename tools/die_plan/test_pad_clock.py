"""PHY pad clocks carry explicit timing/geometry and prove actual clock roles."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_guard as FG
import gen_phys as GP
import pad_clock as PC
import schema
import sdc_lint as SL


def plan():
    raw = json.loads(Path(__file__).with_name('examples').joinpath('tiny_plan.json').read_text())
    p = schema.Plan(raw)
    t = p.types['mid']
    t['pads'] = [dict(name='pma_rck', width=1, dir='in', clock=True),
                 dict(name='pma_tck', width=1, dir='out', clock=True)]
    t.setdefault('clock', {})['pad_clock'] = dict(pins=[
        dict(name='pma_rck', dir='in', period_ps=1250, source='test external PHY row: 1250 ps',
             layer='M7', xy_um=[10.016, 10.0], sink_pins=[dict(module='native_mem', pin='clk')]),
        dict(name='pma_tck', dir='out', period_ps=p.die['period_ps'], source='test native buffer from clk',
             source_clock_port='clk', layer='M7', xy_um=[20.0, 10.0])])
    return p


def test_explicit_phy_period_and_export_pass_without_landing_or_exceptions():
    p = plan()
    pins = GP.type_pins(p, 'mid')
    text = GP.sdc(p, 'mid', pins)
    ctx = SL.kit_context(p, 'mid')
    assert not SL.lint(text, **ctx)
    assert ctx['pad_clock_inputs'] == {'pma_rck': 1250}
    assert 'forwarded_clock_outputs' not in ctx and 'landed_clock_inputs' not in ctx
    assert 'set_clock_groups' not in text and 'set_false_path' not in text
    assert '[all_outputs]' not in text and 'pma_tck' not in text.split('set pad_data_outputs ', 1)[1].split('\n', 1)[0]
    assert FG.sdc_clock_ports(text)[0] == 'pma_rck'
    assert ('pma_tck', 'clk') in FG.sdc_clock_exports(text)
    io = GP.io_tcl(p, 'mid', pins)
    assert 'place_pin -pin_name {pma_rck[0]}' in io and '-pin_size {0.1920 0.1920}' in io
    recs = GP.plan_pin_records(p, 'mid', pins)
    assert {r['name'] for r in recs} >= {'pma_rck[0]', 'pma_tck[0]'}


@pytest.mark.parametrize('mutation', ['missing-period', 'nan-period', 'missing-source', 'wrong-period', 'off-track', 'data-pad'])
def test_bad_or_unreviewed_clock_contract_fails_closed(mutation):
    p = plan(); a, b = p.types['mid']['clock']['pad_clock']['pins']
    if mutation == 'missing-period': a.pop('period_ps')
    if mutation == 'nan-period': a['period_ps'] = float('nan')
    if mutation == 'missing-source': a['source'] = ''
    if mutation == 'wrong-period': b['period_ps'] += 1
    if mutation == 'off-track': a['xy_um'][0] += .001
    if mutation == 'data-pad': p.types['mid']['pads'][0]['clock'] = False
    with pytest.raises(ValueError): PC.io_tcl(p, 'mid')


def test_lint_rejects_export_io_budget_wrong_source_or_clock_period():
    p = plan(); text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid')); ctx = SL.kit_context(p, 'mid')
    for bad in [text + '\nset_output_delay -min 0 -clock vclk [get_ports {pma_tck[0]}]\n',
                text.replace('-period 1250.0000', '-period 833.0000'),
                text.replace('-source [get_ports {clk}]', '-source [get_ports {pma_rck[0]}]'),
                text + '\nset_load 1 [get_ports {pma_tck[0]}]\n',
                text + '\nset_clock_groups -asynchronous -group [get_clocks pma_rck] -group [get_clocks clk]\n']:
        assert SL.lint(bad, **ctx)


NET = '''module top(clk,pma_rck,pma_tck,a);
input clk; input a; input [0:0] pma_rck; output [0:0] pma_tck;
wire q; wire m; wire aq;
DFFHQNx1_ASAP7_75t_R u_bin_a(.CLK(clk),.D(a),.QN(aq));
DFFHQNx1_ASAP7_75t_R ff(.CLK(pma_rck[0]),.D(1'b0),.QN(q));
native_mem mem(.clk(pma_rck[0]),.q(m));
BUFx2_ASAP7_75t_R outbuf(.A(clk),.Y(pma_tck[0]));
endmodule'''


def guard(net=NET, typed=True):
    ps = copy.deepcopy(PC.pins(plan(), 'mid'))
    if not typed: ps[0].pop('sink_pins')
    return FG.guard(net, clocks=['pma_rck'], exports=[('pma_tck', 'clk')], pad_clocks=ps, native_clock_pins={('native_mem', 'clk')})


def test_clock_roles_are_structural_and_native_endpoints_are_typed():
    r = guard()
    assert r['verdict'] == 'PASS', r
    assert r['pad_clock_inputs']['pma_rck']['clock_loads'] == 2
    assert guard(typed=False)['fail_counts'].get('pad_clock')
    assert guard(NET.replace(".D(1'b0)", '.D(pma_rck[0])'))['fail_counts'].get('pad_clock')
    assert guard(NET.replace('BUFx2_ASAP7_75t_R outbuf', 'NAND2x1_ASAP7_75t_R outbuf'))['fail_counts'].get('clock_export')


def test_absent_contract_keeps_original_sdc_bytes():
    p = plan(); p.types['mid']['clock'].pop('pad_clock')
    assert PC.sdc(p, 'mid', 'unchanged\n') == 'unchanged\n'
    assert PC.io_tcl(p, 'mid') == '' and PC.pins(p, 'mid') == []


def test_regeneration_removes_only_owned_pad_clock_sidecar(tmp_path):
    p = plan()
    keep = tmp_path / 'unrelated.json'; keep.write_text('untouched')
    PC.write_contract(p, 'mid', tmp_path)
    assert json.loads((tmp_path / 'pad_clock.json').read_text())['pins'][0]['period_ps'] == 1250
    p.types['mid']['clock'].pop('pad_clock')
    PC.write_contract(p, 'mid', tmp_path)
    assert not (tmp_path / 'pad_clock.json').exists() and keep.read_text() == 'untouched'


def test_native_clock_whitelist_is_subset_of_actual_selected_liberty(tmp_path):
    from types import SimpleNamespace
    lib = tmp_path / 'native.lib'
    lib.write_text('library(test) { cell(native_mem) { pin(clk) { direction: input; clock: true; } '
                   'pin(D) { direction: input; clock: false; /* clock: true; */ } } }')
    p = plan(); PC.write_contract(p, 'mid', tmp_path)
    def selected(cmd, **kwargs):
        assert cmd[-1] == 'print-LIB_FILES' and f'DESIGN_CONFIG={tmp_path / "config.mk"}' in cmd
        return SimpleNamespace(returncode=0, stdout=f'LIB_FILES = {lib}\n')
    ps, actual = FG.kit_pad_clocks(tmp_path, execute=selected)
    assert actual == {('native_mem', 'clk')}
    good = FG.guard(NET, clocks=['pma_rck'], exports=[('pma_tck', 'clk')], pad_clocks=ps, native_clock_pins=actual)
    assert good['verdict'] == 'PASS'
    ps[0]['sink_pins'] = [dict(module='native_mem', pin='D')]
    bad = FG.guard(NET.replace('mem(.clk(', 'mem(.D('), clocks=['pma_rck'],
                   exports=[('pma_tck', 'clk')], pad_clocks=ps, native_clock_pins=actual)
    assert bad['fail_counts'].get('pad_clock')
    assert 'lack actual Liberty clock:true' in str(bad['fails'])


def test_routed_guard_uses_consumed_native_roles_and_rejects_stale_liberty(tmp_path):
    import hashlib
    import signoff as SO
    lib = tmp_path / 'native.lib'
    lib.write_text('library(test) { cell(native_mem) { pin(clk) { direction: input; clock: true; } pin(D) { direction: input; } } }')
    PC.write_contract(plan(), 'mid', tmp_path)
    receipt = tmp_path / 'libraries.json'
    receipt.write_text(json.dumps(dict(status='LOADED', libraries=[dict(path='/work/native.lib', sha256=hashlib.sha256(lib.read_bytes()).hexdigest())])))
    net = tmp_path / 'net.v'; net.write_text(NET)
    sdc = tmp_path / 'constraint.sdc'
    sdc.write_text('create_generated_clock -name pma_tck -master_clock clk -source [get_ports clk] -divide_by 1 [get_ports {pma_tck[0]}]\n')
    disc = dict(kit=str(tmp_path), synth=str(net), sdc=str(sdc))
    result = SO.run_face_guard(disc, ['clk', 'pma_rck[0]'], receipt)
    assert result['verdict'] == 'PASS', result
    lib.write_text(lib.read_text().replace('clock: true', 'clock: false'))
    result = SO.run_face_guard(disc, ['clk', 'pma_rck[0]'], receipt)
    assert result['verdict'] == 'NOT RUN' and 'changed' in result['reason']


def cdc_plan(**kw):
    p = plan()
    a = p.types['mid']['clock']['pad_clock']['pins'][0]
    a.update(dict(cdc='synchronized', cdc_evidence='test RTL census: 2-flop syncs + gray async FIFO'), **kw)
    return p


def test_cdc_absent_is_byte_identical_and_declared_only_appends_the_crossing_form():
    base = plan(); text = GP.sdc(base, 'mid', GP.type_pins(base, 'mid'))
    assert PC.cdc_sdc(PC.pins(base, 'mid'), text, GP.t_lib) == ''
    assert 'set_max_delay' not in text and 'set_false_path' not in text
    p = cdc_plan(); decl = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    assert decl.startswith(text)
    others = [n for n in PC.sdc_clock_names(decl) if n != 'pma_rck']
    assert {'clk', 'vclk', 'pma_tck'} <= set(others)
    for b in others:
        for ln in (f'set_max_delay -ignore_clock_latency 1250.0000 -from [get_clocks pma_rck] -to [get_clocks {b}]',
                   f'set_max_delay -ignore_clock_latency 1250.0000 -from [get_clocks {b}] -to [get_clocks pma_rck]',
                   f'set_false_path -hold -from [get_clocks pma_rck] -to [get_clocks {b}]',
                   f'set_false_path -hold -from [get_clocks {b}] -to [get_clocks pma_rck]'):
            assert decl.count(ln + '\n') == 1, ln
    assert len(decl[len(text):].strip().splitlines()) == 1 + 4 * len(others)
    assert 'set_clock_groups' not in decl and 'COORD 10-31 ruling (3)' in decl
    ctx = SL.kit_context(p, 'mid')
    assert ctx['pad_clock_cdc'] == {'pma_rck': 1250}
    assert 'pad_clock_cdc' not in SL.kit_context(base, 'mid')
    assert not SL.lint(decl, **ctx)
    assert FG.sdc_clock_ports(decl)[0] == 'pma_rck' and ('pma_tck', 'clk') in FG.sdc_clock_exports(decl)


def test_cdc_lint_rejects_groups_partial_or_undeclared_exceptions():
    p = cdc_plan(); decl = GP.sdc(p, 'mid', GP.type_pins(p, 'mid')); ctx = SL.kit_context(p, 'mid')
    hold = 'set_false_path -hold -from [get_clocks vclk] -to [get_clocks pma_rck]\n'
    for bad in [decl + 'set_clock_groups -asynchronous -group [get_clocks pma_rck] -group [get_clocks clk]\n',
                decl.replace(hold, ''),                                   # missing one direction
                decl + hold,                                              # duplicate
                decl.replace('-ignore_clock_latency 1250.0000 -from [get_clocks pma_rck] -to [get_clocks clk]',
                             '-ignore_clock_latency 2500.0000 -from [get_clocks pma_rck] -to [get_clocks clk]'),
                decl + 'set_false_path -from [get_clocks pma_rck] -to [get_clocks clk]\n',   # setup waived too
                decl + 'set_max_delay -ignore_clock_latency 833.0000 -from [get_clocks clk] -to [get_clocks vclk]\n']:
        assert SL.lint(bad, **ctx), bad[len(decl):]
    # the same lines on an undeclared pad clock stay forbidden
    base = plan(); bctx = SL.kit_context(base, 'mid')
    assert SL.lint(decl, **bctx)
    assert SL.lint(decl, **dict(bctx, pad_clock_cdc={'pma_rck': 999}))


@pytest.mark.parametrize('mutation', ['output-pin', 'no-evidence', 'blank-evidence', 'bad-value', 'evidence-only'])
def test_cdc_declaration_fails_closed(mutation):
    p = plan(); a, b = p.types['mid']['clock']['pad_clock']['pins']
    if mutation == 'output-pin': b.update(cdc='synchronized', cdc_evidence='x')
    if mutation == 'no-evidence': a.update(cdc='synchronized')
    if mutation == 'blank-evidence': a.update(cdc='synchronized', cdc_evidence='  ')
    if mutation == 'bad-value': a.update(cdc='async', cdc_evidence='x')
    if mutation == 'evidence-only': a.update(cdc_evidence='x')
    with pytest.raises(ValueError): PC.pins(p, 'mid')
    with pytest.raises(ValueError): GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))


def test_cdc_fields_reach_contract_sidecar_and_schema(tmp_path):
    p = cdc_plan(); PC.write_contract(p, 'mid', tmp_path)
    a = json.loads((tmp_path / 'pad_clock.json').read_text())['pins'][0]
    assert a['cdc'] == 'synchronized' and a['cdc_evidence'].startswith('test RTL census')
    from types import SimpleNamespace
    lib = tmp_path / 'native.lib'
    lib.write_text('library(test) { cell(native_mem) { pin(clk) { direction: input; clock: true; } } }')
    ps, actual = FG.kit_pad_clocks(tmp_path, execute=lambda cmd, **k: SimpleNamespace(returncode=0, stdout=f'LIB_FILES = {lib}\n'))
    assert ps[0]['cdc'] == 'synchronized'
    decl = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    r = FG.guard(NET, clocks=FG.sdc_clock_ports(decl)[:1], exports=FG.sdc_clock_exports(decl), pad_clocks=ps, native_clock_pins=actual)
    assert r['verdict'] == 'PASS', r
    pc = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]["pad_clock"]
    item = pc["properties"]["pins"]["items"]["properties"]
    assert item["cdc"] == {"enum": ["synchronized"]} and item["cdc_evidence"]["minLength"] == 1


def test_native_pad_data_keeps_budget_and_uses_recovered_clock():
    p = plan(); p.types['mid']['pads'].append(dict(name='pma_rx', width=544, dir='in'))
    p.types['mid']['clock']['pad_clock']['pins'][0]['data_inputs'] = [
        dict(port='pma_rx', max_ps=166.6, min_ps=-90, evidence='actual peer TX and RX use recovered clock')]
    text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    ctx = SL.kit_context(p, 'mid')
    assert not SL.lint(text, **ctx)
    assert 'lsearch -exact $pad_native_inputs $pad_input' in text
    assert '# OT_NATIVE_PAD_INPUT pma_rck ' in text
    assert 'remove_from_collection' not in text
    broken_filter = text.replace('lsearch -exact $pad_native_inputs $pad_input', 'lsearch -exact $non_clk_in $pad_input')
    assert SL.lint(broken_filter, **ctx)
    assert 'set_input_delay -max 166.6000 -clock pma_rck [get_ports {pma_rx[*]}]' in text
    wrong = text.replace('-clock pma_rck [get_ports {pma_rx[*]}]', '-clock vclk [get_ports {pma_rx[*]}]')
    assert any('actual pma_rck' in e for e in SL.lint(wrong, **ctx))


@pytest.mark.parametrize('fault', ['unknown', 'output', 'duplicate', 'budget', 'evidence'])
def test_native_pad_data_refuses_untyped_or_ambiguous_association(fault):
    p = plan(); p.types['mid']['pads'].append(dict(name='pma_rx', width=544, dir='in'))
    row = dict(port='pma_rx', max_ps=166.6, min_ps=-90, evidence='actual source')
    p.types['mid']['clock']['pad_clock']['pins'][0]['data_inputs'] = [row]
    if fault == 'unknown': row['port'] = 'missing'
    if fault == 'output': p.types['mid']['pads'][-1]['dir'] = 'out'
    if fault == 'duplicate': p.types['mid']['clock']['pad_clock']['pins'][0]['data_inputs'].append(dict(row))
    if fault == 'budget': row['min_ps'] = 200
    if fault == 'evidence': row['evidence'] = ''
    with pytest.raises(ValueError): PC.pins(p, 'mid')


def _same_edge_plan(**extra):
    p = plan(); p.types['mid']['pads'].append(dict(name='pma_rx', width=544, dir='in'))
    row = dict(port='pma_rx', max_ps=166.6, min_ps=-90, evidence='actual peer TX and RX use recovered clock')
    row.update(extra)
    p.types['mid']['clock']['pad_clock']['pins'][0]['data_inputs'] = [row]
    return p


def test_same_edge_capture_emits_exact_relation_and_lowered_min():
    p = _same_edge_plan(capture='same_edge', eye_hold_extra_ps=175)
    text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    ctx = SL.kit_context(p, 'mid')
    assert not SL.lint(text, **ctx)
    assert 'set_multicycle_path 0 -setup -from [get_ports {pma_rx[*]}]' in text
    assert 'set_input_delay -max 166.6000 -clock pma_rck [get_ports {pma_rx[*]}]' in text
    assert 'set_input_delay -min -265.0000 -clock pma_rck [get_ports {pma_rx[*]}]' in text
    # the relation is required, exact and only on the declared port
    assert any('no set_multicycle_path' in e for e in SL.lint(text.replace(
        'set_multicycle_path 0 -setup -from [get_ports {pma_rx[*]}]\n', ''), **ctx))
    assert SL.lint(text.replace('set_multicycle_path 0 -setup', 'set_multicycle_path 1 -setup'), **ctx)
    assert SL.lint(text + 'set_multicycle_path 0 -setup -from [get_ports {pma_rck}]\n', **ctx)
    # the declared min budget cannot be restored (the TT eye edge stays covered by the FF hold check)
    assert any('declared -265' in e for e in SL.lint(text.replace(
        'set_input_delay -min -265.0000', 'set_input_delay -min -90.0000'), **ctx))


def test_same_edge_absent_keeps_bytes_and_other_rows_refuse_multicycle():
    a = _same_edge_plan()
    text = GP.sdc(a, 'mid', GP.type_pins(a, 'mid'))
    assert 'set_multicycle_path' not in text and 'set_input_delay -min -90.0000 -clock pma_rck' in text
    ctx = SL.kit_context(a, 'mid')
    assert SL.lint(text + 'set_multicycle_path 0 -setup -from [get_ports {pma_rx[*]}]\n', **ctx)


@pytest.mark.parametrize('extra', [dict(capture='same_edge'), dict(eye_hold_extra_ps=100),
                                   dict(capture='next_edge', eye_hold_extra_ps=100),
                                   dict(capture='same_edge', eye_hold_extra_ps=0),
                                   dict(capture='same_edge', eye_hold_extra_ps=5000),
                                   dict(capture='same_edge', eye_hold_extra_ps=True)])
def test_same_edge_declaration_fails_closed(extra):
    with pytest.raises(ValueError):
        PC.pins(_same_edge_plan(**extra), 'mid')
