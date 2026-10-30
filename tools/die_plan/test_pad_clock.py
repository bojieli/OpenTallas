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
    return FG.guard(net, clocks=['pma_rck'], exports=[('pma_tck', 'clk')], pad_clocks=ps)


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
