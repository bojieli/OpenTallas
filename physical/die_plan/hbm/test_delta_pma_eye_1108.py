"""PMA-EYE-1108: the R3 eye assumption lands in pad_clock and reaches the kit SDC."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[2] / 'tools' / 'die_plan'
sys.path.insert(0, str(TOOLS)); sys.path.insert(0, str(HERE))
import gen_phys as GP
import pad_clock as PC
import schema
import delta_pma_eye_1108 as D


def raw():
    r = json.loads((TOOLS / 'examples' / 'tiny_plan.json').read_text())
    t = r['partition_types']['mid']
    t['pads'] = [dict(name='io_lk_N2_pma_rck', width=1, dir='in', clock=True),
                 dict(name='io_lk_N2_pma_tck', width=1, dir='out', clock=True),
                 dict(name='io_lk_N2_pma_rx', width=8, dir='in'),
                 dict(name='io_lk_N2_pma_tx', width=8, dir='out')]
    per = r['die']['period_ps']
    t.setdefault('clock', {})['pad_clock'] = dict(pins=[
        dict(name='io_lk_N2_pma_rck', dir='in', period_ps=per, source='test recovered PMA clock',
             layer='M7', xy_um=[10.016, 10.0], sink_pins=[dict(module='native_mem', pin='clk')]),
        dict(name='io_lk_N2_pma_tck', dir='out', period_ps=per, source='test forwarded clock from clk',
             source_clock_port='clk', layer='M7', xy_um=[20.0, 10.0])])
    return r


def test_rows_values_validate_and_reach_sdc():
    r = raw(); per = r['die']['period_ps']
    new, ch = D.apply(r)
    assert len(ch) == 2
    p = schema.Plan(new)
    pins = {x['name']: x for x in PC.pins(p, 'mid')}
    rx = pins['io_lk_N2_pma_rck']['data_inputs'][0]; tx = pins['io_lk_N2_pma_tck']['data_outputs'][0]
    assert (rx['port'], rx['max_ps'], rx['min_ps']) == ('io_lk_N2_pma_rx', 0.75 * per, 0.25 * per)
    assert (tx['port'], tx['max_ps'], tx['min_ps']) == ('io_lk_N2_pma_tx', 0.0, 0.0)
    assert 'ASSUMPTION, not a measurement' in rx['evidence'] and 'ASSUMPTION' in tx['evidence']
    text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    assert f'set_input_delay -max {GP.t_lib(0.75 * per):.4f} -clock io_lk_N2_pma_rck [get_ports {{io_lk_N2_pma_rx[*]}}]' in text
    assert f'set_input_delay -min {GP.t_lib(0.25 * per):.4f} -clock io_lk_N2_pma_rck [get_ports {{io_lk_N2_pma_rx[*]}}]' in text
    assert f'set_output_delay -max {GP.t_lib(0):.4f} -clock io_lk_N2_pma_tck [get_ports {{io_lk_N2_pma_tx[*]}}]' in text


def test_idempotent_and_untouched_without_pad_clock():
    new, _ = D.apply(raw())
    again, ch = D.apply(new)
    assert again == new and ch == []
    r = raw(); r['partition_types']['mid']['clock'].pop('pad_clock')
    assert D.apply(r) == (r, [])


@pytest.mark.parametrize('mut', ['no_data_pad', 'wrong_dir', 'conflict'])
def test_fails_closed(mut):
    r = raw(); t = r['partition_types']['mid']
    if mut == 'no_data_pad':
        t['pads'] = [x for x in t['pads'] if x['name'] != 'io_lk_N2_pma_rx']
    elif mut == 'wrong_dir':
        next(x for x in t['pads'] if x['name'] == 'io_lk_N2_pma_tx')['dir'] = 'in'
    else:
        t['clock']['pad_clock']['pins'][0]['data_inputs'] = [dict(port='io_lk_N2_pma_rx', max_ps=1, min_ps=0, evidence='x')]
    with pytest.raises(ValueError):
        D.apply(r)
