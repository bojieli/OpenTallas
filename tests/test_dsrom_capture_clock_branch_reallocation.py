import gzip,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_clock_branch_reallocation as M

def model():return json.loads((M.BASE/'model.json').read_text())
def sites(s):return json.loads(gzip.decompress((M.BASE/f'shard{s}_sites.json.gz').read_bytes()))

def test_exact_counts_and_bank():
    m=model();assert [m['shards'][str(s)]['total_fixed_buffers'] for s in (0,1)]==[38383,30231]
    assert m['selected_bank']['core_clock70406']==70406
    assert m['additional_buffers']==m['annex_charge_mm2']==0
    assert not m['source_graph_changed']

@pytest.mark.parametrize('s,n',[(0,102),(1,66)])
def test_named_outside_repair(s,n):
    m=model();assert m['shards'][str(s)]['outside_raw_first_relays']==n
    v=[p for p in sites(s) if p['home']=='common']
    assert len(v)==n
    assert all(p['role']=='first_relay' and p['native_sink']['instance']==p['branch_destination'] for p in v)

@pytest.mark.parametrize('s',[0,1])
def test_unique_disjoint_selected_sites(s):
    v=sites(s);assert len({p['proposed_site_ID'] for p in v})==len(v)
    rows={}
    for p in v:rows.setdefault(p['bbox_DBU'][1],[]).append(p['bbox_DBU'])
    for boxes in rows.values():
        boxes.sort()
        assert all(a[2]<=b[0] for a,b in zip(boxes,boxes[1:]))

@pytest.mark.parametrize('s',[0,1])
def test_repaired_bounds_and_full_row_distribution(s):
    m=model()['shards'][str(s)];assert m['first_relay_failed']==0
    assert m['raw_rows_used']==m['raw_rows_available']
    for p in sites(s):
        if p['role']=='first_relay':
            assert p['optimistic_literal_pin_metal_C_fF']<=p['first_branch_metal_budget_fF']+1e-12
            assert p['constructed_M8_M9_center_route_metal_C_fF']<=p['first_branch_metal_budget_fF']+1e-12

def test_literal_mx_pin_gap_not_center_assumption():
    source=[{'bbox_DBU':[0,0,10,10]}];site={'bbox_DBU':[1000,0,1378,270]}
    assert M.access(source,site,[[18,126,73,144]],{'M8':1,'M9':1})==pytest.approx(1.124)
    assert M.access(source,site,[[18,126,73,144]],{'M8':2,'M9':1})>1.124

def test_half_contact_budget_not_qualified():
    m=model();assert not m['contextual_PR_admitted'] and not m['physical_fit']
    assert m['added_cycles'] is None and not m['single_user_latency_qualified']
    assert all(not v['downstream_relay_and_pad_branch_assignment_complete'] for v in m['shards'].values())
    assert m['old_bd872_rejection_preserved']

def test_existing_source_occupancy_exclusion():
    existing=[{'bbox_DBU':[0,270,378,540]}]
    v=M.candidates([0,0,756,1080],existing,0)
    assert all(not M.overlap(p['bbox_DBU'],existing[0]['bbox_DBU']) for p in v)

@pytest.mark.parametrize('s',[0,1])
def test_native_sinks_pg_and_escapes(s):
    m=model()['shards'][str(s)];assert m['native_sink_escape_ports']>0
    assert m['buffer_native_escape_ports']>2*m['total_fixed_buffers']
    p=json.loads(gzip.decompress((M.BASE/f'shard{s}_PG_upfeed.json.gz').read_bytes()))
    assert p['common_rail_extensions'] and p['source_current_capacity_unknown']
    assert p['raw_feed']['upstream_supply_current_EM_voltage_drop'] is None
    assert not m['actual_global_OBS_PG_via_spacing_proven']

def test_maximum_matching_avoids_greedy_site_theft():
    graph=M.csr_matrix([[1,1],[1,0]])
    selected=M.maximum_bipartite_matching(graph,perm_type='column')
    assert len(set(selected))==2 and all(selected>=0)
    bad=M.maximum_bipartite_matching(M.csr_matrix([[1,0],[1,0]]),perm_type='column')
    assert sum(bad<0)==1
