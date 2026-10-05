"""The physical multiplier cut must be carried through the composed token price."""
import sys
from pathlib import Path

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_model_propagation_gate as G
import hdc_isa as I
import hdc_timing as T


@pytest.mark.parametrize('context',[1,8192])
def test_missing_one_cycle_is_exposed_at_all217_actual_model_issues(context):
 r=G.replay_delta(context)
 assert r['issued_me_instructions']==217 and r['kv_me_instructions']==72
 assert r['weight_me_instructions']==145
 assert r['total_cycles_delta']==217 and r['max_issue_time_shift']==216
 assert r['LV']==7 and r['TP']==4 and r['SU']==64


def test_identical_latency_inputs_have_zero_token_price_difference():
 r=G.replay_delta(1,target_extra=54,priced_extra=54)
 assert r['total_cycles_delta']==0 and all(d['issue_shift']==0 for d in r['me_issue_deltas'])


def test_reverse_price_audit_is_symmetric_not_a_headline_multiplier():
 r=G.replay_delta(1,target_extra=54,priced_extra=55)
 assert r['total_cycles_delta']==-217


def test_audit_restores_global_model_parameters():
 before=dict(T.K);sw=I.SU_WIDTH;G.replay_delta(1)
 assert dict(T.K)==before and I.SU_WIDTH==sw


def test_real_sourcebound_physical_price_gate_rejects_missing_multiplier_cycle():
 r=G.run_gate()
 assert r['status']=='fail' and r['source_stable']
 assert r['physical_raw_status']=='error' and r['priced_extra']==54 and r['target_extra']==55
 assert not r['model_price_joined'] and not r['build_ready'] and not r['adoption']
 assert r['new_jobs']==0 and len(r['seven_runtime_gaps'])==7
