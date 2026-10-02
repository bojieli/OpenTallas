import sys,json,gzip
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_allocator_resident_audit as A

def fixture(p,overlap=False):
    m={'candidate_id':'DS4096-TP4-S58-PAIR1','source_commit':'synthetic-only','stage_stats':[{'stage':0,'compiled_NP':2,'NBF_shape':1}], 'capacity_verdict':'FAIL','allocation_failures':[{'layer':0}], 'current_source_PHW6_verdict':'FAIL','ECC_verdict':'unbound'}
    (p/'model.json').write_text(json.dumps(m));(p/'compiler_source.py').write_text('# synthetic metadata fixture')
    rows=[{'stage':0,'layer':0,'format':'fp4','alias':'q','plans':[[0,0,0,1,1,0,64]]},{'stage':0,'layer':0,'format':'bf16','alias':'bf','plans':[[0,0,0,1,1,32 if overlap else 64,64]]},{'stage':None,'layer':0,'format':'bf16','alias':'missing','plans':[]}]
    with gzip.open(p/'assignments.jsonl.gz','wt') as f:
        for x in rows:f.write(json.dumps(x)+'\n')
    with gzip.open(p/'provider_assignment.jsonl.gz','wt') as f:f.write('')

def test_shared_capacity_and_unallocated_failures_retained(tmp_path):
    fixture(tmp_path);x=A.audit(tmp_path)
    assert x['census']['unallocated_matrix_records']==1
    assert x['shared_residency']['unique_sites']==1
    assert x['shared_residency']['matrix_payload_reserved_words_both_slots']==256
    assert x['shared_residency']['overlapping_immutable_spans']==0
    assert x['source_provider_faults']['q_on_source_BF_plan_spans_needing_dual_abstract']==1
    assert x['preserved_allocator_verdict']=='FAIL' and not x['hardware_or_area_credit']

def test_overlapping_format_words_visible(tmp_path):
    fixture(tmp_path,True)
    assert A.audit(tmp_path)['shared_residency']['overlapping_immutable_spans']==1
