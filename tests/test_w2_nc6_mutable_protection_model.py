"""Source-format and exhaustive CODEC MODEL gates; not RTL qualification."""
import ast
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w2_nc6_mutable_protection_model as m


def source_encoder():
    p=m.D/'inputs/tools/h4_hbm_baseline_bridge.py'
    tree=ast.parse(p.read_text());names={'DATA_POSITIONS','BYTE_ENCODE','PARITY_MASKS'}
    nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ['require','secded64']) or
           (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
    scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),scope)
    return scope['secded64']


def source_decoder():
    spec=importlib.util.spec_from_file_location('archive_ecc',m.D/'inputs/tools/mem_compiler/ecc.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.decode


def test_source_interleaved_encoder_and_decoder_adapter():
    encode=source_encoder();decode=source_decoder()
    for v in [0,(1<<64)-1,0x123456789abcdef0]+[1<<i for i in range(64)]:
        assert m.encode(v)==encode(v)
        for bit in range(72):
            cw=m.encode(v)^(1<<bit)
            value,status,fixed=m.decode(cw)
            assert value==v and status=='CE' and fixed==m.encode(v)
            assert decode(m.systematic_wire(cw),64)==(v,'corrected')
    # Direct wire connection is demonstrably wrong for the actual format.
    assert decode(m.encode(0x123456789abcdef0),64)!=(0x123456789abcdef0,'ok')


def test_all_physical_single_and_sameword_double_model_positions():
    singles=doubles=0
    for row in m.layout():
        payload=((row['index']+1)*0x9e3779b97f)&((1<<row['payload_bits'])-1)
        cw=m.seal(payload,127,row['index'],row['kind'])
        for bit in range(72):
            result=m.unseal(cw^(1<<bit),127,row['index'],row['kind'],row['payload_bits'])
            assert result==(payload,'CE',cw);singles+=1
        for a,b in combinations(range(72),2):
            result=m.unseal(cw^(1<<a)^(1<<b),127,row['index'],row['kind'],row['payload_bits'])
            assert result==(None,'DUE',None);doubles+=1
    assert singles==13608 and doubles==483084


def test_wrong_address_pc_kind_and_padding_validcode_refused():
    cw=m.seal(7,5,99,2)
    for args in [(6,99,2),(5,98,2),(5,99,3)]:assert m.unseal(cw,*args)[1]=='LOCATION_FAULT'
    assert m.unseal(m.seal(1<<30,5,99,2),5,99,2,payload_bits=20)[1]=='PADDING_FAULT'


def test_held_word_rechecked_on_actual_consumer_edge():
    clean=m.seal(42,5,3,1);s=m.Scrub(clean,5,3,1)
    assert s.begin()=='CLEAN'
    s.word^=1<<71
    assert not s.consume() and not s.retired
    assert s.begin()=='CE' and not s.consume()
    assert s.finish() and s.word==clean and s.consume()


def test_scrub_refuses_new_fault_or_competing_write():
    s=m.Scrub(m.seal(42,5,3,1)^1,5,3,1)
    assert s.begin()=='CE'
    s.word^=2
    assert not s.finish() and s.fault and not s.consume()


def test_due_cannot_consume_or_scrub():
    s=m.Scrub(m.seal(42,5,3,1)^3,5,3,1)
    assert s.begin()=='DUE' and s.fault and not s.finish() and not s.consume()


def test_layout_conservation_nonzero_reset_and_conditional_readiness():
    model=m.model();rows=model['storage']['layout']
    assert [r['index'] for r in rows]==list(range(189))
    assert model['storage']['protected_bits_perPC']==13608
    assert model['storage']['sealed_primary_bits']==9576
    assert model['ports']['correction_engines']==8
    assert model['calendar']['delta']==[4,3,3]
    assert sum(model['ports']['scheduler_bits'].values())==79
    assert model['cell_price']['reset_examples']['0']['encoded_reset_ones']>0
    assert not model['readiness']['RTL_ready'] and not model['geometry']['new_directory_client']


def test_crossword_double_is_not_promised_due():
    for cw in [m.seal(42,5,3,1)^1,m.seal(7,5,4,1)^2]:assert m.decode(cw)[1]=='CE'


def test_exceptional_quarantine_is_explicit_not_legacy_held_compatibility():
    model=m.model();interface=model['exceptional_interface']
    assert interface['repair_busy_output_bits']==1 and not interface['enrolled']
    assert 'valid suppression' in interface['held_protocol']
    assert 'included' in interface['registered_state']
    reset=model['cell_price']['reset_examples']
    assert set(reset)=={str(i) for i in range(128)}
    assert model['cell_price']['reset_all128_encoded_ones']+model['cell_price']['reset_all128_encoded_zeroes']==13608*128
