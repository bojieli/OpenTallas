#!/usr/bin/env python3
"""Fail-closed companion to the pinned provider join; no physical validator exists."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
JOIN_PIN='bf097e43e1b01902c21af0e71b6e0b1ae337961e'
JOIN_PATH='results/quality/w10_clock_provider_join_r1/join.json'
PROVIDER_PIN='4ad1baf66d6411bf01ebd14ad97b4abecbd9ecf9'
PROVIDER_PATH='results/rtl/w17_connected_token_preparation_20261001/rootstop_provider_requirements.json'
EVENTS=('configuration','go','beat','drain','outputcredit','prewake')
MODEL_FIELDS=('cfg_load_cycles','go_delivery_cycles','beat_and_return_drain_cycles',
    'consumer_accept_and_reverse_credit_cycles','CDC_cycles','prewake_cycles',
    'root_clock_RC_energy','SSFF_in_context','physical_stage_profile')


def evidence_status(value):
    if value is None:return 'MISSING'
    if not isinstance(value,dict):return 'REJECTED_INVALID_EVIDENCE_TYPE'
    if not isinstance(value.get('schema'),str) or not value['schema']:
        return 'REJECTED_MISSING_EVIDENCE_SCHEMA'
    # No implemented source-bound measured validator accepts any schema yet.
    # A declared schema, hash, PASS label or fixture is not validated evidence.
    return 'REJECTED_UNSUPPORTED_UNVALIDATED_EVIDENCE_SCHEMA'


def eligibility(requirements, *, host_quiet=False, runtime_skip=False, standalone_pg_pass=False):
    r=requirements if isinstance(requirements,dict) else {}
    events=r.get('event_providers')
    events=events if isinstance(events,list) else []
    providers={}
    duplicates=[]
    for event in events:
        if not isinstance(event,dict):continue
        name=event.get('event')
        if not isinstance(name,str):continue
        if name in providers:duplicates.append(name)
        providers[name]=event
    missing=[event for event in EVENTS if event not in providers or
        providers[event].get('binding')!='QUALIFIED_CONNECTED_HARDWARE']
    model=r.get('model_required')
    model=model if isinstance(model,dict) else {}
    unpriced=[name for name in MODEL_FIELDS if model.get(name) is None]
    waveform=r.get('actual_root_stop_waveform')
    complete=(not missing and not unpriced and not duplicates and
        r.get('root_stop_ready') is True and waveform is not None)
    return dict(candidate_metadata_complete=bool(complete),
        candidate_completeness_scope='Required labels/fields present only; does not validate values, hardware sources, waveform, timing, power or physical fit.',
        missing_candidate_event_labels=missing,missing_candidate_model_values=unpriced,
        unqualified_events=list(EVENTS),unvalidated_model_fields=list(MODEL_FIELDS),duplicate_events=duplicates,
        provider_evidence_status=evidence_status(r.get('provider_evidence')),
        waveform_evidence_status=evidence_status(waveform),
        supported_provider_evidence_schemas=[],supported_measured_waveform_schemas=[],
        source_bound_measured_validator_available=False,
        physical_root_stop_qualified=False,credited_root_stop_cycles=0,
        credited_power_reduction_W=None,
        runtime_skip_used_as_provider=False,host_quiet_used_as_provider=False,
        standalone_pg_used_as_connected_provider=False,
        rejection_reason='No source-bound actual provider/measured waveform validator is implemented; physical qualification is always false regardless of caller labels or metadata.',
        credit_scope='No root-stop savings credit. Actual whole-token root activity, rail, energy and IR remain unbound.')


def build():
    pins={}
    def load(pin,path):
        raw=subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
        pins[path]=dict(commit=pin,sha256=hashlib.sha256(raw).hexdigest())
        return json.loads(raw)
    join=load(JOIN_PIN,JOIN_PATH)
    requirements=load(PROVIDER_PIN,PROVIDER_PATH)
    result=eligibility(requirements)
    return dict(schema='opentallas.w10.clock-provider-qualification-companion.v1',
        verdict='FAIL_CLOSED_NO_MEASURED_PHYSICAL_VALIDATOR',source_pins=pins,
        current_candidate=result,
        preserved_join=dict(path=JOIN_PATH,commit=JOIN_PIN,unchanged=True,
            source_semantics=join['source_semantics'],clock_accounting=join['clock_accounting']),
        legacy_helper_scope='Pinned bf097 eligibility is historical and superseded; do not use it as a physical qualifier. This companion is the fail-closed entry point.',
        required_future_validator=['Validate actual provider schema and source/control/netlist pins against immutable evidence',
            'Validate measured root/leaf waveform schema, provenance and event/phase/ack coverage',
            'Validate priced completion/prewake/retention/ports/CDC and connected contextual SS/FF plus spatial PG/clock fit',
            'Validate actual rail/slew/load/extracted RC/energy and package/IR before any power credit'],
        physical_admission=False,adopt=False,physical_root_stop_qualified=False,
        credited_root_stop_cycles=0,power_reduction_W=None,
        RTL_changed=False,hardware_jobs_launched=0,new_latency_assumptions=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
