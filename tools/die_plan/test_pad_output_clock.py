"""Real exported PHY clock owns only its explicitly declared data-output delays."""
import copy
import json

import pytest

import gen_phys as GP
import landing_contract as LC
import pad_clock as PC
import schema
import sdc_lint as SL
from test_pad_clock import plan


def output_plan():
    p = plan()
    p.types['mid']['pads'].append(dict(name='pma_tx', width=4, dir='out'))
    p.types['mid']['clock']['pad_clock']['pins'][1]['data_outputs'] = [
        dict(port='pma_tx', max_ps=166.6, min_ps=0,
             evidence='actual clk capture and dedicated native buffer export to pma_tck')]
    return p


def test_native_output_uses_export_clock_without_changing_load_or_budgets():
    p = output_plan()
    text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    assert not SL.lint(text, **SL.kit_context(p, 'mid'))
    assert 'set_output_delay -max 166.6000 -clock pma_tck [get_ports {pma_tx[*]}]' in text
    assert 'set_output_delay -min 0.0000 -clock pma_tck [get_ports {pma_tx[*]}]' in text
    seam = next(line for line in text.splitlines() if line.startswith('set pad_seam_outputs '))
    all_data = next(line for line in text.splitlines() if line.startswith('set pad_data_outputs '))
    assert 'pma_tx' not in seam and 'pma_tx[*]' in all_data
    assert any(line.startswith('set_load ') and '$pad_data_outputs' in line for line in text.splitlines())
    assert 'remove_from_collection' not in text
    for bad in [text.replace('-clock pma_tck [get_ports {pma_tx[*]}]', '-clock vclk [get_ports {pma_tx[*]}]'),
                text.replace('166.6000 -clock pma_tck', '160.0000 -clock pma_tck')]:
        assert any('actual pma_tck' in e or 'declared 166.6' in e
                   for e in SL.lint(bad, **SL.kit_context(p, 'mid')))


def test_landing_collection_is_filtered_only_for_output_delays():
    p = output_plan()
    text = PC.sdc(p, 'mid', 'set cland_data_outputs [get_ports {e_out[*] pma_tx[*]}]\n'
                  'set_output_delay -max 166.6 -clock vclk $cland_data_outputs\n'
                  'set_output_delay -min 0 -clock vclk $cland_data_outputs\n'
                  'set_load 1 $cland_data_outputs\n')
    assert 'set_load 1 $cland_data_outputs' in text
    assert 'set_output_delay -max 166.6 -clock vclk $pad_seam_outputs' in text
    assert 'set_output_delay -min 0 -clock vclk $pad_seam_outputs' in text
    assert 'pma_tx' not in text.split('set pad_seam_outputs ', 1)[1].split('\n', 1)[0]


def test_all_native_outputs_keep_the_load_and_drop_empty_generic_delay(monkeypatch):
    p = output_plan()
    monkeypatch.setattr(LC, 'data_output_selectors', lambda _p, _tn: ['pma_tx[*]'])
    text = PC.sdc(p, 'mid', 'set_output_delay -max 166.6 -clock vclk [all_outputs]\n'
                  'set_load 1 [all_outputs]\n')
    assert 'set pad_seam_outputs {}' in text
    assert 'set_output_delay -max 166.6 -clock vclk' not in text
    assert 'set_load 1 $pad_data_outputs' in text
    assert 'set_output_delay -max 166.6000 -clock pma_tck' in text


@pytest.mark.parametrize('fault', ['input-clock', 'unknown', 'input-pad', 'clock-pad', 'duplicate',
                                   'budget', 'nan', 'boolean', 'evidence', 'nonliteral', 'empty'])
def test_bad_output_binding_is_refused(fault):
    p = output_plan(); clocks = p.types['mid']['clock']['pad_clock']['pins']
    row = clocks[1]['data_outputs'][0]
    if fault == 'input-clock': clocks[0]['data_outputs'] = clocks[1].pop('data_outputs')
    if fault == 'unknown': row['port'] = 'missing'
    if fault == 'input-pad': p.types['mid']['pads'][-1]['dir'] = 'in'
    if fault == 'clock-pad': row['port'] = 'pma_tck'
    if fault == 'duplicate': clocks[1]['data_outputs'].append(copy.deepcopy(row))
    if fault == 'budget': row['min_ps'] = 200
    if fault == 'nan': row['max_ps'] = float('nan')
    if fault == 'boolean': row['max_ps'] = True
    if fault == 'evidence': row['evidence'] = ''
    if fault == 'nonliteral': row['port'] = ['pma_tx']
    if fault == 'empty': clocks[1]['data_outputs'] = []
    with pytest.raises(ValueError): PC.pins(p, 'mid')


def test_output_binding_is_retained_in_sidecar_and_schema(tmp_path):
    p = output_plan(); PC.write_contract(p, 'mid', tmp_path)
    pin = json.loads((tmp_path / 'pad_clock.json').read_text())['pins'][1]
    assert pin['data_outputs'][0]['port'] == 'pma_tx'
    props = schema.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['clock']['properties']['pad_clock']['properties']['pins']['items']['properties']
    assert props['data_outputs']['items']['required'] == ['port', 'max_ps', 'min_ps', 'evidence']


def test_export_clock_cannot_time_unrelated_ports_or_lose_hold_uncertainty():
    p = output_plan(); text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid')); ctx = SL.kit_context(p, 'mid')
    bad = text.replace('-clock vclk $pad_seam_outputs', '-clock pma_tck $pad_seam_outputs')
    assert any('only its declared output' in e for e in SL.lint(bad, **ctx))
    bad = text.replace('set_clock_uncertainty 25.0000 -hold [get_clocks pma_tck]\n', '')
    assert any('hold uncertainty on clock pma_tck' in e for e in SL.lint(bad, **ctx))
