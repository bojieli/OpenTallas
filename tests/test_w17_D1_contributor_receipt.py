import copy
import json
from pathlib import Path
import pytest
from tools.w17_D1_contributor_receipt import verify
from tools.w17_D1_reset_fault_attribution import verify_pins
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_actual_union_contributors_20261002_r1'


def inputs():
    return json.loads((E/'receipt.json').read_text()),(E/'gdb_runtime.log').read_text()


def rewrite(receipt,log,phase,key,value):
    old=receipt[phase][key]
    receipt[phase][key]=value
    prefix='D1_FATAL_FIELD' if phase=='fatal_fields' else 'D1_FIRST_PRIME_READY_SAMPLE'
    import re
    pattern=r'^'+re.escape(prefix+' '+key+'=')+r'0x[0-9a-f]+$'
    return re.sub(pattern,prefix+' '+key+'='+hex(value),log,flags=re.M)


def test_actual_source_fault_reset_and_missing_row0():
    result=verify(*inputs())
    assert result['missing_valid_rows']==[0]
    assert result['first_prime_internal_rn']==0
    assert not result['reset_qualified_DUT_acceptance']
    assert result['actual_masks']==dict(fault_r=64,dbg_fs=0,violations=0)
    assert result['prefetch_fault_code'] is None
    assert result['original_PC24_cause']=='UNOBSERVED'


@pytest.mark.parametrize('phase,key,value',[
 ('first_prime_fields','rst_s',3),('first_prime_fields','source_prime_ready',0),
 ('first_prime_fields','bench_prime_row',1),('fatal_fields','row_valid[word0]',0xffffffff),
 ('fatal_fields','row_valid[word1]',0xfffffffe),('fatal_fields','prefetch_row',1),
 ('fatal_fields','pf_fault',0),('fatal_fields','rope_fault',1),
 ('fatal_fields','unsupported_read',1),('fatal_fields','bad_block',1),
 ('fatal_fields','merge_fault',1),('fatal_fields','descriptor_fault',0),
 ('fatal_fields','schedule_fault',0)])
def test_alternative_states_cannot_inherit_this_attribution(phase,key,value):
    receipt,log=inputs();log=rewrite(receipt,log,phase,key,value)
    with pytest.raises(ValueError):verify(receipt,log)


def test_missing_first_prime_blocks_temporal_attribution():
    receipt,log=inputs()
    log='\n'.join(line for line in log.splitlines() if not line.startswith('D1_FIRST_PRIME_READY_SAMPLE'))
    with pytest.raises(ValueError):verify(receipt,log)


def test_source_prediction_cannot_fill_missing_generated_code():
    receipt,log=inputs();receipt['prefetch_fault_code']=1
    with pytest.raises(ValueError):verify(receipt,log)


@pytest.mark.parametrize('key,value',[('inferior_exit_code',0),('GDB_exit_code',1),
 ('input_postcheck',False),('simulator_launches',2),('compiler_or_link_launches',1),
 ('runtime_qualification',True),('fulltoken',True)])
def test_wrong_terminal_or_scope_rejected(key,value):
    receipt,log=inputs();receipt[key]=value
    with pytest.raises(ValueError):verify(receipt,log)


def test_duplicate_packet_and_changed_identity_rejected():
    receipt,log=inputs()
    with pytest.raises(ValueError):verify(receipt,log+'\nD1_FATAL_FIELD pf_fault=0x1\n')
    receipt['input_hashes_after']=dict(receipt['input_hashes_after'],binary='0'*64)
    with pytest.raises(ValueError):verify(receipt,log)


def test_protected_sources_and_actual_artifact_hashes():
    assessment=json.loads((E/'attribution.json').read_text())
    verify_pins(ROOT,assessment['source_SHA256'])
    verify_pins(E,json.loads((E/'artifact_SHA256.json').read_text()))
    assert assessment['scope']['fixture_successor_prepared'] is False
    assert assessment['scope']['I66_used'] is False
