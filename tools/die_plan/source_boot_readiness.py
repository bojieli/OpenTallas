#!/usr/bin/env python3
"""Ingest the measured KV control boot bound without granting physical closure.

The selected R52 control profile is separate from the unqualified physical POR.
The generator can carry this contract only while its exact control identity
matches. Budgets describe bounds; actual registered ready/fault still gate START.
"""
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path

MEASUREMENT_SHA256='8639e9b5adb17db044cf5664d110ed6f0c840b505fb4a086dca1cc6620175a47'
MEASUREMENT_SEMANTIC_SHA256='baa38f8cd8ecb28853a23a04182db4ee33068f5eaed1b080e833d32bac5c3a68'
CONTROL_SIDECAR_SHA256='e9d8d16ff0502f95bca3e999026b8b8312ddeb14b129a67a3518fa1ac6d686dc'
CONTROL_RTL_SHA256='f80f821a3a371413a11f75c548735aedcb9720dc5d4473676b2b923c04e5dec5'

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def identity(side):
    s=copy.deepcopy(side)
    s.pop('source_boot_readiness_contract',None)
    s['collector'].pop('boot_budget',None)
    return sha(canonical(s))
def ceildiv(n,d): return (n+d-1)//d

def validate_measurement(blob):
    if sha(blob)!=MEASUREMENT_SHA256: raise ValueError('unreviewed boot measurement bytes')
    m=json.loads(blob)
    if m['schema']!='opentallas.native_clock_boot_measurement.v1' or m['native_control_measurement_pass'] is not True:
        raise ValueError('native control boot measurement is not PASS')
    if m['physical_qualified'] is not False or m['period_fs']!=833000 or m['period_ps']!=833:
        raise ValueError('source-only 833ps scope required')
    if m['emitted_RTL_files']!=58 or m['emitted_RTL_semantic_sha256']!=CONTROL_RTL_SHA256:
        raise ValueError('selected complete 58-file control cohort differs')
    for name,c in m['nominal_selected_cases'].items():
        if not all(c[k] is True for k in ('terminal_pass','all_160_part_ready','all_160_part_fault_zero','old392_negative')) or c['CA_faults']!=0:
            raise ValueError('incomplete nominal cold/warm case '+name)
        if c['post_qualified_raw_cycles']!=m['causal_bound']['measured_post_qualified_raw_cycles']:
            raise ValueError('post-qualified-raw causal path differs')
    w=m['worst_REF_case']
    if not w['required_cold_warm_measurement_complete'] or w['CA_faults_observed']!=0 or not w['warm_retained_PLL_POR']:
        raise ValueError('worst REF cold/warm case incomplete')
    if w['cold_elapsed_fs']!=w['complete_glue_ready_fs']-w['POR_fs'] or w['warm_elapsed_fs']!=w['warm_complete_fs']-w['warm_start_release_fs']:
        raise ValueError('measured event interval differs')
    cold=ceildiv(w['cold_elapsed_fs'],m['period_fs'])
    warm=ceildiv(w['warm_elapsed_fs'],m['period_fs'])
    if cold!=m['ready_at_glue_max_cycles'] or cold!=m['causal_bound']['whole_cold_cycles_ceiling'] or warm!=m['warm_mission_observed_max_cycles']:
        raise ValueError('event interval/bound arithmetic differs')
    if not m['old392_negative_pass'] or m['839_negative_fs']<=0:
        raise ValueError('underbudget negative controls missing')
    return m,cold,warm

def apply(side,measurement_blob):
    m,cold,warm=validate_measurement(measurement_blob)
    if identity(side)!=CONTROL_SIDECAR_SHA256: raise ValueError('unmeasured source sidecar/control graph')
    old=copy.deepcopy(side['collector']['boot_budget'])
    if old['ready_at_glue_max_cycles']!=m['historic_ready_at_glue_max_cycles'] or old['observer_input_capture_cycles']!=m['observer_input_capture_cycles']:
        raise ValueError('historic source budget/capture boundary differs')
    out=copy.deepcopy(side)
    contract={'schema':'opentallas.source_boot_readiness_contract.v1',
        'measurement_sha256':MEASUREMENT_SHA256,'measurement':m,
        'source_control_identity_sha256':identity(side),
        'emitted_RTL_semantic_sha256':CONTROL_RTL_SHA256,
        'historic_boot_budget':old,'physical_qualified':False,'emitted_RTL_requalification_required':False,
        'scope':m['scope'],'phase_scope':m['phase_scope']}
    out['source_boot_readiness_contract']=contract
    return reapply(out)

def reapply(side):
    """Used by clock_landing_plan after regenerating this exact source profile."""
    out=copy.deepcopy(side);c=out['source_boot_readiness_contract']
    # Packet bytes are pinned above. Embedded JSON is checked against those
    # canonical bytes through the pinned source packet's semantic digest.
    if c.get('schema')!='opentallas.source_boot_readiness_contract.v1' or type(c.get('emitted_RTL_requalification_required')) is not bool or c.get('physical_qualified') is not False:
        raise ValueError('incomplete source-only boot contract')
    m=c['measurement']
    if c['measurement_sha256']!=MEASUREMENT_SHA256 or c['emitted_RTL_semantic_sha256']!=CONTROL_RTL_SHA256:
        raise ValueError('unreviewed embedded source boot contract')
    if c['source_control_identity_sha256']!=CONTROL_SIDECAR_SHA256 or identity(out)!=CONTROL_SIDECAR_SHA256:
        raise ValueError('source control/sidecar changed: remeasure boot readiness')
    # Preserve original formatting-independent semantic identity of the packet.
    if sha(canonical(m))!=MEASUREMENT_SEMANTIC_SHA256: raise ValueError('embedded measurement changed')
    c['measurement_semantic_sha256']=sha(canonical(m))
    w=m['worst_REF_case'];cold=ceildiv(w['cold_elapsed_fs'],m['period_fs']);warm=ceildiv(w['warm_elapsed_fs'],m['period_fs'])
    historic=c['historic_boot_budget']
    if historic['ready_at_glue_max_cycles']!=m['historic_ready_at_glue_max_cycles'] or historic['observer_input_capture_cycles']!=m['observer_input_capture_cycles']:
        raise ValueError('historic source budget/observer capture changed')
    b=copy.deepcopy(c['historic_boot_budget'])
    b.update(ready_at_glue_max_cycles=cold,warm_mission_restore_max_cycles=warm,
        observer_input_capture_cycles=m['observer_input_capture_cycles'],
        raw_reset_release_max_cycles=ceildiv(m['causal_bound']['qualified_raw_prefix_ps_strict_upper'],m['period_ps']),
        measured_post_qualified_raw_cycles=m['causal_bound']['measured_post_qualified_raw_cycles'],
        source_causal_bound_qualified=not c.get('emitted_RTL_requalification_required',False),physical_clock_phase_qualified=False,
        emitted_RTL_requalification_required=c.get('emitted_RTL_requalification_required',False),required_emitted_RTL_semantic_sha256=CONTROL_RTL_SHA256,
        historic_ready_at_glue_max_cycles=m['historic_ready_at_glue_max_cycles'],
        one_time_boot_delta_cycles=cold-m['historic_ready_at_glue_max_cycles'],
        data_cycles_added=0,measurement_sha256=MEASUREMENT_SHA256,
        contract='SOURCE causal clock-landing bound after POR; excludes programming/install/first-token. START still requires actual registered ready and no fault. Physical/internal/new-SD clock qualification remains held.')
    b.pop('local_registered_depths',None)  # old partial formula stays only in historical record
    out['collector']['boot_budget']=b
    return out

def admission(side):
    side=reapply(side);b=side['collector']['boot_budget'];c=side['source_boot_readiness_contract'];m=c['measurement']
    return {'schema':'opentallas.kv.source_boot_admission.v1','status':'SOURCE_BOUND_PHYSICAL_HELD' if b['source_causal_bound_qualified'] else 'SOURCE_BOUND_EMITTED_RTL_REQUALIFICATION_REQUIRED',
        'source_causal_bound_qualified':b['source_causal_bound_qualified'],
        'emitted_RTL_requalification_required':b['emitted_RTL_requalification_required'],
        'period_ps':m['period_ps'],'ready_at_glue_max_cycles':b['ready_at_glue_max_cycles'],
        'observer_input_capture_cycles':b['observer_input_capture_cycles'],
        'cold_registered_ready_bound_cycles':b['ready_at_glue_max_cycles']+b['observer_input_capture_cycles'],
        'warm_mission_restore_max_cycles':b['warm_mission_restore_max_cycles'],
        'one_time_boot_bound_increase_cycles':b['one_time_boot_delta_cycles'],
        'one_time_boot_bound_increase_ps':b['one_time_boot_delta_cycles']*m['period_ps'],
        'steady_token_cycle_delta':0,'physical_qualified':False,'production_admission_granted':False,
        'requires':['actual registered root ready','no registered root fault','actual programme/local installation','delivered mission START'],
        'budget_alone_grants_START':False,'first_token_latency_inferred':False,
        'measurement_sha256':MEASUREMENT_SHA256,'source_control_identity_sha256':identity(side),
        'emitted_RTL_semantic_sha256':CONTROL_RTL_SHA256,'source_profile':m['current_logical_cohort'],
        'holds':['current die clock load 2337 FAIL','four current raw-clock holds','current new-SD/internal/core/PMA phase qualification'],
        'source_template_scope':'Only the measured emitted RTL cohort; any regeneration requires fresh full semantic comparison',
        'phase_scope':m['phase_scope']}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sidecar',type=Path,required=True);ap.add_argument('--measurement',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admission-out',type=Path,required=True)
    a=ap.parse_args();raw=a.sidecar.read_bytes();blob=a.measurement.read_bytes();m,_,_=validate_measurement(blob)
    selected=json.loads(raw)
    if selected.get('source_boot_readiness_contract'):
        out=reapply(selected)
    else:
        if sha(raw)!=m['sources']['R52_sidecar']['sha256']:raise ValueError('wrong selected R52 source sidecar')
        out=apply(selected,blob)
    a.out.write_text(json.dumps(out,indent=1)+'\n');a.admission_out.write_text(json.dumps(admission(out),indent=2)+'\n')
    print(json.dumps(admission(out),indent=2))
if __name__=='__main__':main()
