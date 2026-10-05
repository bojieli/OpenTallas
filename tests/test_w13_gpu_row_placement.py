import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('placement',Path(__file__).resolve().parents[1]/'tools/w13_gpu_row_placement.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def demand(rows,K):
    base=128;local=[0]*4;cross=[0]*4
    for sm in range(32):
        a=rows*sm//32;b=rows*(sm+1)//32
        for stack,n in enumerate(m.striped_lines(base+a*K,(b-a)*K)):
            (local if stack==m.quad(sm) else cross)[stack]+=n
    return dict(id=0,die=0,weight='test',output_rows=rows,K=K,code_base=base,golden_split=1,weight_INT8_bytes=rows*K,candidate_local_code_line_requests_by_stack=local,candidate_cross_quad_code_line_requests_by_stack=cross)


def test_balanced_striping_pays75percent_cross_and_retains_fullrow_owners():
    j=m.compare({'matrix_weight_demand_instances':[demand(4096,4096)]});r=j['rows'][0]
    assert r['existing_cross_quad_fraction']==.75
    assert r['candidate_weight_code_cross_quad_return_sectors']==0
    assert sum(x['valid_code_bytes'] for x in r['SM_row_ownership'])==4096*4096
    assert r['descriptor_bytes_charged_per_invocation']==1024 and j['rate_credit']==0 and not j['physical_build_ready']


def test_partial_rows_padding_and_metadata_are_charged_without_free_capacity():
    j=m.compare({'matrix_weight_demand_instances':[demand(33,130)]});r=j['rows'][0]
    assert r['candidate_padding_bytes']>0
    intervals=[x['row_interval'] for x in r['SM_row_ownership']]
    assert intervals[0][0]==0 and intervals[-1][1]==33
    assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
    assert r['descriptor_worst_case_cross_quad_wire_bytes']==2560
