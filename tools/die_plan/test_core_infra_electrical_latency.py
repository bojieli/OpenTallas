"""Electrical balancing vehicle uses actual ASAP7 TT/FF NLDM tables and a real macro insertion receipt.

This is a tool mechanism estimate, not an A0 physical result. The 13-stage FF branch and one-stage macro branch
share one input and predict <80ps effective endpoint range at both corners. Stage equality would reject it.
"""
import copy
import json
from pathlib import Path

import pytest
import core_infra as CI
import die_clock_128 as C
from test_core_infra import sample

FIXTURE = Path(__file__).with_name('fixtures') / 'electrical_latency_nldm.json'


def vehicle():
    f = json.loads(FIXTURE.read_text())
    s = sample()
    s['pg_obstructions_um'] = {}
    nodes = [dict(name='R', master='BUFx24_ASAP7_75t_R', parent='port:clk', xy_um=[200,200]),
             dict(name='M', master='BUFx8_ASAP7_75t_R', parent='R', xy_um=[200,210])]
    for i in range(13):
        nodes.append(dict(name=f'F{i}', master='BUFx8_ASAP7_75t_R', parent='R' if i == 0 else f'F{i-1}',
                          xy_um=[210 + 10*i,200]))
    leaves = [dict(node='M', sinks=['macro/clk'], load_class='macro',
                   early_tap_ps={c:d['macro_insertion_ps'] for c,d in f['corners'].items()},
                   early_tap_view=';'.join(d['macro_view']+' sha256:'+d['macro_view_sha256'] for d in f['corners'].values()),
                   pin_latency_ps={}),
              dict(node='F12', sinks=['ff/CLK'], pin_latency_ps={})]
    corners = {}
    for corner,d in f['corners'].items():
        b = d['cells']['BUFx8_ASAP7_75t_R']
        root = d['cells']['BUFx24_ASAP7_75t_R']
        # Root fanout is two identical BUF pins at 10um each; MST=20um. Branch Elmore includes its own input cap.
        delay, slew = C.stage(root,20,0,20*.154233,2*b['cap'])
        elmore = 10*.014812*(10*.154233/2+b['cap'])
        delay += elmore
        slew = (slew*slew+(2.2*elmore)**2)**.5
        mp,ms = C.stage(b,slew,10*.014812,10*.154233,d['macro_pin_cap_ff'])
        mp += delay
        fp,fs = delay,slew
        for i in range(13):
            delta,fs = C.stage(b,fs,10*.014812,10*.154233,b['cap'] if i<12 else d['ff_pin_cap_ff'])
            fp += delta
        leaves[0]['pin_latency_ps'][corner] = dict(min=mp,max=mp)
        leaves[1]['pin_latency_ps'][corner] = dict(min=fp,max=fp)
        lo = min(fp,mp+d['macro_insertion_ps']['min'])
        hi = max(fp,mp+d['macro_insertion_ps']['max'])
        corners[corner] = dict(leaf_min=lo,leaf_max=hi,leaf_window=hi-lo,slew_max=max(ms,fs))
    s['core_tree'] = dict(clock_port='clk',stage_basis='electrical_latency',nodes=nodes,leaves=leaves,
                          equal_load=False,load_balance='joint_nldm_plan',
                          latency_target_ps={c:(r['leaf_min']+r['leaf_max'])/2 for c,r in corners.items()},
                          model_qualification=dict(source=FIXTURE.name,model=f['basis'],measured_timing_used=False,
                                                   electrical_latency_qualified=True,band_policy='info',window_policy='info',
                                                   corners=corners))
    return s


def test_actual_both_corner_nldm_vehicle_qualifies_unequal_depths(tmp_path):
    s=vehicle()
    for c,r in s['core_tree']['model_qualification']['corners'].items():
        assert 0 < r['leaf_window'] < 80, c
        assert 0 < r['slew_max'] < 80, c
    p=CI.compile_slice(s)['core_tree']
    assert p['depth_info']['min']==2 and p['depth_info']['max']==14
    assert 'stages' not in p['early_taps'][0]  # never convert the view's insertion to a scalar stage surrogate
    assert CI.install(tmp_path,s)
    assert 'ot_ci_tree_sink {M} {macro/clk}' in (tmp_path/'master_core_infra.tcl').read_text()
    s['core_tree']['stage_basis']='total'
    with pytest.raises(CI.InfraError,match='early_tap_stage_ps'):
        CI.compile_slice(s)


@pytest.mark.parametrize('mut,frag',[
    (lambda t:t.pop('latency_target_ps'),'latency_target_ps'),
    (lambda t:t['latency_target_ps'].update(FF=float('nan')),'latency_target_ps'),
    (lambda t:t.update(early_tap_stage_ps={'TT':20,'FF':15,'source':'scalar'}),'scalar'),
    (lambda t:t['model_qualification'].pop('electrical_latency_qualified'),'qualification'),
    (lambda t:t['model_qualification'].update(measured_timing_used=True),'qualification'),
    (lambda t:t.update(equal_load=True),'qualification'),
    (lambda t:t['leaves'][0].pop('early_tap_view'),'early_tap_view'),
    (lambda t:t['leaves'][0].pop('early_tap_ps'),'signed/real'),
    (lambda t:t['leaves'][1]['pin_latency_ps'].pop('FF'),'TT and FF'),
    (lambda t:t['model_qualification']['corners']['FF'].update(leaf_window=0),'disagrees'),
    (lambda t:t['model_qualification']['corners']['FF'].update(slew_max=float('nan')),'slew_max'),
    (lambda t:t['leaves'][0]['early_tap_ps']['TT'].update(max=1000),'disagrees'),
])
def test_unqualified_or_inconsistent_electrical_models_refused(mut,frag):
    s=vehicle();mut(s['core_tree'])
    with pytest.raises(CI.InfraError,match=frag):
        CI.emit_tcl(s)


def test_existing_window_and_slew_policies_remain_gates():
    s=vehicle();s['core_tree']['model_qualification']['window_policy']='gate'
    with pytest.raises(CI.InfraError,match='target FAIL'):
        CI.emit_tcl(s)
    s=vehicle();s['core_tree']['model_qualification']['corners']['FF']['slew_max']=81
    with pytest.raises(CI.InfraError,match='target FAIL'):
        CI.emit_tcl(s)


def test_analysis_can_compile_before_qualification_but_cannot_emit_or_install(tmp_path):
    s=vehicle()
    del s['core_tree']['model_qualification']
    for leaf in s['core_tree']['leaves']:
        del leaf['pin_latency_ps']
    assert CI.compile_slice(s)['core_tree']['depth_info']['max']==14
    with pytest.raises(CI.InfraError,match='qualification'):
        CI.install(tmp_path,s)
    assert not list(tmp_path.iterdir())
