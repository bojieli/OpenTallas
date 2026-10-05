import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qualification',ROOT/'tools/w10_clock_provider_qualification.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def requirements():
    return json.loads(subprocess.check_output(['git','show',m.PROVIDER_PIN+':'+m.PROVIDER_PATH],cwd=ROOT))


def counterfeit_complete():
    p=requirements()
    for e in p['event_providers']:e['binding']='QUALIFIED_CONNECTED_HARDWARE'
    p['model_required']={k:1 for k in p['model_required']}
    p['root_stop_ready']=True
    p['actual_root_stop_waveform']={'synthetic_fixture':True}
    return p


def test_exact_parent_counterexample_cannot_physically_qualify():
    r=m.eligibility(counterfeit_complete())
    assert r['candidate_metadata_complete']
    assert not r['missing_candidate_event_labels'] and not r['missing_candidate_model_values']
    assert len(r['unqualified_events'])==6 and len(r['unvalidated_model_fields'])==9
    assert not r['physical_root_stop_qualified']
    assert r['waveform_evidence_status']=='REJECTED_MISSING_EVIDENCE_SCHEMA'
    assert r['credited_root_stop_cycles']==0 and r['credited_power_reduction_W'] is None


def test_forged_evidence_schema_and_hash_do_not_supply_validator():
    p=counterfeit_complete()
    p['provider_evidence']={'schema':'claimed.actual-provider.v1','source_sha256':'0'*64,'verdict':'PASS'}
    p['actual_root_stop_waveform']={'schema':'claimed.measured-waveform.v1','sha256':'0'*64,'verdict':'PASS'}
    r=m.eligibility(p,host_quiet=True,runtime_skip=True,standalone_pg_pass=True)
    assert r['candidate_metadata_complete']
    assert not r['source_bound_measured_validator_available'] and not r['physical_root_stop_qualified']
    assert r['provider_evidence_status']==r['waveform_evidence_status']=='REJECTED_UNSUPPORTED_UNVALIDATED_EVIDENCE_SCHEMA'
    assert not r['supported_measured_waveform_schemas'] and r['credited_root_stop_cycles']==0


def test_current_missing_providers_stay_incomplete():
    r=m.eligibility(requirements())
    assert not r['candidate_metadata_complete']
    assert len(r['unqualified_events'])==6 and len(r['missing_candidate_model_values'])==9
    assert not r['physical_root_stop_qualified']


def test_missing_or_duplicate_fields_cannot_be_complete():
    p=counterfeit_complete();p['model_required']={}
    assert not m.eligibility(p)['candidate_metadata_complete']
    p=counterfeit_complete();p['event_providers'].append(dict(p['event_providers'][0]))
    r=m.eligibility(p);assert r['duplicate_events'] and not r['candidate_metadata_complete']


def test_malformed_inputs_and_waveforms_fail_closed():
    for bad in (None,[],True,{'event_providers':1,'model_required':1}):
        assert not m.eligibility(bad)['physical_root_stop_qualified']
    p=counterfeit_complete();p['actual_root_stop_waveform']='PASS'
    r=m.eligibility(p)
    assert r['waveform_evidence_status']=='REJECTED_INVALID_EVIDENCE_TYPE'
    assert not r['physical_root_stop_qualified']


def test_companion_preserves_pinned_join_and_no_hardware_credit():
    r=m.build()
    assert r['preserved_join']['unchanged']
    assert r['preserved_join']['commit']==m.JOIN_PIN
    assert not r['physical_root_stop_qualified'] and not r['physical_admission'] and not r['adopt']
    assert r['credited_root_stop_cycles']==0 and r['power_reduction_W'] is None
    assert r['hardware_jobs_launched']==0 and not r['new_latency_assumptions']
