import copy
import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lifetimes',ROOT/'tools/dsrom_selected_context_lifetimes.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def test_whole_selected_program_peak_and_scope():
    m=M.model()
    assert m['conditional_maximum_selected_output_versions']==8
    assert m['conditional_maximum_selected_output_FP32_words']==7680
    assert m['existing_VM_payload_bytes_per_rank']==30720
    assert m['existing_VM_payload_bytes_TP4']==122880
    assert m['necessary_future_consumer_witness']['pc']==94
    assert set(m['necessary_future_consumer_witness']['live_versions'])=={79,84,87,88,89,92,93,94}
    assert m['necessary_future_consumer_witness']['FP32_words']==7424
    assert m['maximum_payload_witness']['pc']==100
    assert m['maximum_payload_witness']['version_count']==6
    assert m['all18_output_frame_words']==14592
    assert m['actual_maximum_full_contexts'] is None
    assert m['absolute_F_bound'] is None
    assert m['additional_credits']==m['additional_payload_reservations']==0


def test_W2_final_producer_and_last_consumer_included():
    m=M.model();last=next(v for v in m['versions'] if v['producer']==100)
    assert last['words']==1280 and not last['captured_candidate']
    assert last['consumers'][0]['pc']==105
    assert last['consumers'][0]['operand']=='c'
    assert len([v for v in m['versions'] if v['captured_candidate']])==12


@pytest.mark.parametrize('mutation',['old_slice','alias','predicate','missing_consumer','barrier','idle','geometry'])
def test_source_mutants_fail_closed(mutation):
    nodes,rtl=M.sources();nodes=copy.deepcopy(nodes);rtl=dict(rtl)
    if mutation=='old_slice':nodes=[n for n in nodes if n['instruction_index']<=98]
    if mutation=='alias':nodes[1]['instruction']['qe_obase']=nodes[0]['instruction']['qe_obase']
    if mutation=='predicate':nodes[0]['instruction']['pred']=1
    if mutation=='missing_consumer':nodes[-1]['instruction']['c_base']=0
    if mutation=='barrier':nodes[5]['instruction']['wait']=0
    if mutation=='idle':rtl['vec.sv']=rtl['vec.sv'].replace('!pipe_live','1\'b1')
    if mutation=='geometry':nodes[-6]['instruction']['qe_nout']=576
    with pytest.raises(ValueError):M.derive(nodes,rtl)


def test_lease_does_not_end_at_consumer_dispatch():
    m=M.model();s={x['pc']:x for x in m['ordered_envelope']}
    assert {66,67}.issubset(s[70]['live_versions'])
    assert not {66,67}.intersection(s[71]['live_versions'])
    assert all(v in s[105]['live_versions'] for v in [79,84,89,94,97,100])
