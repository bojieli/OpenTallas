#!/usr/bin/env python3
"""Join actual W17 signal candidates to clock accounting without stop credit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PROVIDER_PIN='4ad1baf66d6411bf01ebd14ad97b4abecbd9ecf9'
PROVIDER_PATH='results/rtl/w17_connected_token_preparation_20261001/rootstop_provider_requirements.json'
CONTRACT_PIN='850d9c79bc3767b4ad4ca5d5106b9c97aecf08cc'
CONTRACT_PATH='results/quality/w10_clock_source_contract_r1/contract.json'


def eligibility(requirements, *, host_quiet=False, runtime_skip=False, standalone_pg_pass=False):
    """Host and isolated component observations cannot satisfy hardware providers."""
    providers={e['event']:e for e in requirements['event_providers']}
    missing=[event for event in ('configuration','go','beat','drain','outputcredit','prewake')
             if event not in providers or providers[event]['binding']!='QUALIFIED_CONNECTED_HARDWARE']
    unpriced=[k for k,v in requirements['model_required'].items() if v is None]
    ready=not missing and not unpriced and requirements['root_stop_ready'] is True
    ready=ready and requirements['actual_root_stop_waveform'] is not None
    return dict(physical_root_stop_qualified=ready,unqualified_events=missing,unpriced_model_fields=unpriced,
        runtime_skip_used_as_provider=False,host_quiet_used_as_provider=False,standalone_pg_used_as_connected_provider=False,
        credited_root_stop_cycles=0 if not ready else None,
        credited_power_reduction_W=None,
        credit_scope='Zero stop-cycle credit while providers are incomplete; not a claim about actual future root activity or operating power.')


def build():
    refs={}
    def read(pin,path):
        raw=subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
        refs[path]=dict(commit=pin,sha256=hashlib.sha256(raw).hexdigest())
        return raw.decode()
    provider=json.loads(read(PROVIDER_PIN,PROVIDER_PATH))
    contract=json.loads(read(CONTRACT_PIN,CONTRACT_PATH))
    assert provider['clock_contract_commit']==CONTRACT_PIN
    sources={}
    for path,pin in provider['source_pins'].items():
        text=read(pin['commit'],path)
        assert refs[path]['sha256']==pin['sha256'], 'actual provider source hash mismatch'
        sources[path]=text
    spine=sources['rtl/v41die/ot_v41_spine_w17w10.sv']
    pair=sources['rtl/v41die/ot_v41_pair_w17w10.sv']
    retn=sources['rtl/v41die/ot_v41_retn_w17w10.sv']
    runtime=sources['rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp']
    ports=spine.split(');',1)[0]
    assert re.search(r'input\s+wire\s+\[R-1:0\]\s+r_v\b',ports)
    assert not re.search(r'\b(?:r_ready|r_cr|r_credit|w_ready|w_ack|w_credit)\b',ports)
    assert re.search(r'assign\s+ready\s*=\s*st\s*==\s*S_IDLE',spine)
    assert re.search(r'rows_left\s*<=\s*rows_left\s*-.*?\$countones\(r_v\)',spine)
    assert re.search(r'if\s*\(r_v\[kr\]\).*?w_we\[kr\]\s*<=\s*1\x27b1',spine,re.S)
    assert re.search(r'`ifdef V41_RT.*?assign quiet.*?`else\s*assign quiet\s*=\s*1\x27b0',retn,re.S)
    assert 'RT_SKIP' in runtime and 'pair_skip' in runtime and 'node_skip' in runtime
    assert re.search(r'assign quiet\s*=\s*!e_busy\s*&&\s*!ld_run\s*&&\s*!c_v',pair)
    for path,count in provider['current_top_PG_controller_instantiations'].items():
        text=re.sub(r'//[^\n]*|/\*.*?\*/','',sources[path],flags=re.S)
        assert count==0 and not re.search(r'\bot_chip_v41_pg_ctrl\b',text)
    assert provider['host_RT_SKIP_is_physical_rootstop'] is False
    check=eligibility(provider)
    assert check['physical_root_stop_qualified'] is False
    assert len(check['unqualified_events'])==6 and len(check['unpriced_model_fields'])==9
    return dict(schema='opentallas.w10.w17-clock-provider-join.v1',
        verdict='SOURCE_BOUND_PARTIAL_SIGNALS_NO_PHYSICAL_ROOTSTOP_CREDIT',source_pins=refs,
        token_runtime_source_commit=provider['token_runtime_source_commit'],
        current_top_PG_controller_instantiations=provider['current_top_PG_controller_instantiations'],
        event_providers=provider['event_providers'],model_required=provider['model_required'],
        stop_condition_requirements=provider['stop_condition_requirements'],
        eligibility=check,
        source_semantics=dict(spine_ready='GO admission/state idle, not a return-ready handshake',
            return_arrival='rows_left decremented by countones(r_v); arrival count is not acknowledged output completion',
            output_write='r_v drives registered w_we; producer write-enable is not consumer acceptance/visibility',
            hardware_return_quiet='Outside V41_RT the return quiet output is tied0; runtime queue inspection is not a physical root-stop provider',
            pair_quiet='Partial !e_busy/!ld_run/!c_v/... candidate, not all-stage/credit/prewake completion',
            host_RT_SKIP='Software evaluation skipping only, does not drive a physical root ICG'),
        clock_accounting=dict(root_buffers=107,gated_buffers=3766,stop_duty_credit=False,
            source_clock_rule='Charge root separately whenever source runs. Do not derive whole-token off-time from host skipping, leaf quiet, r_v arrival or aggregate stage busy.',
            retained_vector_duty_scope='a820 actual-vector windows only; no new full-token activity or rate',
            wire_only_baseline_fF=contract['numerical_wire_baseline_fF'],wire_delta_fF=contract['numerical_wire_delta_fF'],
            existing_endpoint_or_TT_switching_added_again=False),
        ownership=dict(runtime_providers='Godel01a0f697-9bf5-7840-bd23-58a583e983fd: actual consumer ack or fixed-rate reservation/outstanding writes and producer/router prewake',
            model_schedule='Ram01a0f697-9c82-7572-8900-dd7b15d59ebf: integer residency and model-priced whole-stage event joins',
            physical_clock='Current owner: fullmapped slot/clock obligations and power accounting',
            spatial_PG_escape='Sole root01a0f65d-bcde-75d0-a540-0a013866cb8a'),
        remaining=dict(operating_voltage_V=None,actual_slew_load=None,physical_phase=None,
            actual_root_stop_waveform=None,whole_token_activity=None,total_power_W=None,peak_current_A=None,IR_drop_V=None),
        physical_admission=False,adopt=False,RTL_changed=False,hardware_jobs_launched=0,
        next_action='Require source-bound connected providers and model-priced cycles/ports/fanout/retention/CDC before RTL; full spatial PG/clock fit before any heavy job.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
