import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('join',ROOT/'tools/w10_clock_provider_join.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def requirements():
    return json.loads(subprocess.check_output(['git','show',m.PROVIDER_PIN+':'+m.PROVIDER_PATH],cwd=ROOT))


def test_host_skip_quiet_and_component_PASS_cannot_supply_power_stop_credit():
    r=m.eligibility(requirements(),host_quiet=True,runtime_skip=True,standalone_pg_pass=True)
    assert not r['physical_root_stop_qualified'] and r['credited_root_stop_cycles']==0
    assert len(r['unqualified_events'])==6
    assert 'outputcredit' in r['unqualified_events'] and 'prewake' in r['unqualified_events']


def test_ready_label_without_actual_providers_rejected():
    p=requirements();p['root_stop_ready']=True;p['actual_root_stop_waveform']={'claimed':'PASS'}
    assert not m.eligibility(p)['physical_root_stop_qualified']


def test_source_identity_does_not_equal_connected_hardware():
    p=requirements()
    for e in p['event_providers']:e['binding']='signal identities only'
    assert len(m.eligibility(p)['unqualified_events'])==6


def test_missing_credit_or_prewake_is_decisive_even_with_other_labels_bound():
    for missing in ('outputcredit','prewake'):
        p=requirements();p['root_stop_ready']=True;p['actual_root_stop_waveform']={'synthetic_fixture':True}
        p['model_required']={k:1 for k in p['model_required']}
        for e in p['event_providers']:e['binding']='QUALIFIED_CONNECTED_HARDWARE'
        p['event_providers']=[e for e in p['event_providers'] if e['event']!=missing]
        assert not m.eligibility(p)['physical_root_stop_qualified']


def test_actual_source_cones_and_no_unbound_power_adoption():
    r=m.build()
    assert len(r['source_pins'])==10
    assert not any(r['current_top_PG_controller_instantiations'].values())
    assert r['clock_accounting']['root_buffers']==107
    assert r['clock_accounting']['gated_buffers']==3766
    assert r['clock_accounting']['wire_delta_fF'] is None
    assert not r['clock_accounting']['stop_duty_credit']
    assert len(r['eligibility']['unpriced_model_fields'])==9
    assert any('persistent KV/state' in s for s in r['stop_condition_requirements'])
    assert all(v is None for v in r['remaining'].values())
    assert not r['physical_admission'] and not r['adopt']
