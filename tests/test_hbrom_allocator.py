"""Real layout invariants: bijective coordinates, capacity tails, SM swizzle."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hbrom_allocator as A


def tensor(name='w.weight',rows=11,k=5120,fmt='fp4'):
    return dict(name=name,rows=rows,k=k,format=fmt,bytes=rows*k//2)


@pytest.mark.parametrize('fmt,k,records',[('fp4',5120,24),('fp4',2304,16),('fp8',5120,40),('bf16',5120,80)])
def test_full_shape_row(fmt,k,records):
    g=A.row_geometry(fmt,k)
    assert g['records_per_row']==records
    coords=[]
    for group in range(g['groups']):
        for t in range(8):
            for lane in range(g['lanes']):
                for j in range(1 if fmt=='bf16' else 32):
                    pos=A.code_coordinate(fmt,group,t,lane,j)
                    if pos<k: coords.append(pos)
    assert sorted(coords)==list(range(k))


@pytest.mark.parametrize('fmt,k',[('fp4',2304),('fp8',5120),('bf16',5120)])
def test_payload_permutation_matches_independent_sm_lane_decode(fmt,k):
    g=A.row_geometry(fmt,k); width={'fp4':4,'fp8':8,'bf16':16}[fmt]
    code=lambda pos:(pos*13+7)% (1<<width)
    scale=lambda block:(block*17+29)%256
    for group in range(g['groups']):
        for step in range(8):
            record=A.swizzle(fmt,A.encode_record(fmt,k,group,step,code,scale))
            for lane in range(g['lanes']):
                for j in range(1 if fmt=='bf16' else 32):
                    # Independent inverse from retained SM lane contract.
                    pos=(group*g['lanes']+lane)*(8 if fmt=='bf16' else 256)+step*(1 if fmt=='bf16' else 32)+j
                    bit=(lane if fmt=='bf16' else lane*32+j)*width
                    assert ((record>>bit)&((1<<width)-1))==(code(pos) if pos<k else 0)
                if fmt!='bf16':
                    pos=(group*g['lanes']+lane)*256+step*32
                    assert (record>>(1024+8*lane))&255==(scale(pos//32) if pos<k else 127)


def test_ownership_physical_inverse_and_no_overlap():
    data=A.allocate([tensor(rows=23),tensor('v.weight',rows=7,k=2304)],2,3,8,rows_per_macro=64)
    owners=set();addresses=set()
    for run in data['runs']:
        for i in range(run['row_count']):
            row=run['first_row']+i*run['row_stride']
            assert (run['name'],row) not in owners
            owners.add((run['name'],row))
            for step in run['physical_steps']:
                for stream in range(4):
                    a=A.physical_address(run,row,step,stream,64)
                    key=tuple(a[k] for k in ('rank','tile','macro','row'))
                    assert key not in addresses;addresses.add(key)
                    assert A.inverse_address(run,a['macro'],a['row'],64)==dict(source_row=row,group_step=step,stream=stream)
    assert len(owners)==30


def test_capacity_actual_integer_groups_not_total_bytes():
    a=A.allocate([tensor(rows=4)],1,1,4,rows_per_macro=40)
    assert not a['fits']
    assert a['required_pairs_per_tile']==8
    assert a['group_tail_padding_records']==8
    assert a['used_record_highwaters']==[[104]]


def test_compact_only_elides_allzero_records_not_partial_lanes():
    padded=A.allocate([tensor(rows=2)],1,1,4)
    compact=A.allocate([tensor(rows=2)],1,1,4,layout_mode='compact')
    assert padded['used_record_highwaters']==[[48]]
    assert compact['used_record_highwaters']==[[48]]
    assert A.row_geometry('fp4',2304,'compact')['records_per_row']==16
    assert A.selected_calendar(padded,['w.weight'])['max_cycles']==A.selected_calendar(compact,['w.weight'])['max_cycles']
    with pytest.raises(ValueError,match='generated zero'):
        A.physical_address(compact['runs'][0],0,24,0)


def test_selected_experts_calendar_uses_actual_owner_rows():
    ts=[tensor(f'e{e}.weight',rows=17,k=2304) for e in range(6)]
    a=A.allocate(ts,2,3,16)
    cal=A.selected_calendar(a,[t['name'] for t in ts])
    assert sum(t['records'] for t in cal['tiles'])==6*17*16
    assert cal['max_cycles']==384
    with pytest.raises(ValueError,match='unmapped'):
        A.selected_calendar(a,['missing'])


def test_raw_scales_archive_and_invalid_geometry():
    a=A.allocate([dict(name='x.scale',is_scale=True,format='ue8m0',bytes=129,rows=129,k=1)],1,1,4)
    assert a['used_record_highwaters']==[[2]]
    with pytest.raises(ValueError): A.allocate([],1,1,5)


def test_group_slot_addresses_meet_two_cycle_macro_capture():
    a=A.allocate([tensor(rows=19)],1,1,16,rows_per_macro=64)
    previous={};count=0
    for event in A.access_calendar(a,'w.weight',0,0):
        if event['bubble']: continue
        count+=1
        for addr in event['addresses']:
            macro=addr['macro']
            assert event['cycle']-previous.get(macro,-100)>=2
            previous[macro]=event['cycle']
    assert count==19*24


def test_gate_up_and_all_down_outputs_share_exact_row_owners():
    ts=[tensor('archive.scale',rows=5,k=1)]
    ts += [tensor(f'layer.expert{e}.{op}.weight',rows=23 if op!='down' else 31,k=5120 if op!='down' else 2304)
           for e in range(7) for op in ('gate','up','down')]
    a=A.allocate(ts,2,3,128)
    maps={}
    for r in a['runs']:
        if r['format']=='raw': continue
        d=maps.setdefault(r['name'],{})
        for i in range(r['row_count']):
            row=r['first_row']+i*r['row_stride']
            d[row]=(r['rank'],r['tile'])
            assert d[row]==(row%6//3,row%3)
    for e in range(7):
        assert maps[f'layer.expert{e}.gate.weight']==maps[f'layer.expert{e}.up.weight']
        assert maps[f'layer.expert{e}.down.weight']==maps['layer.expert0.down.weight']


def test_calendar_charges_each_matrix_tail_not_combined_rows():
    ts=[tensor(f'expert{e}.weight',rows=1,k=5120) for e in range(6)]
    a=A.allocate(ts,1,1,16)
    cal=A.selected_calendar(a,[t['name'] for t in ts])
    assert cal['max_cycles']==6*64
    assert cal['max_cycles']>A.ceildiv(6*3,8)*8*8


def test_native_storage_bound_never_claims_padding_holes_as_capacity():
    ts=[tensor(rows=4)]
    bound=A.summarize_storage_records(ts,1)
    actual=A.allocate(ts,1,1,4,rows_per_macro=40)
    assert bound['total_records']==96
    assert actual['used_record_highwaters'][0][0]==104
    assert not actual['fits']


@pytest.mark.parametrize('fmt,k,groups',[('fp4',5120,3),('fp4',2304,2),('fp8',5120,5),('bf16',5120,10)])
@pytest.mark.parametrize('rows',range(1,17))
def test_dense_source_calendar_tail_recursions(fmt,k,groups,rows):
    a=A.allocate([tensor(rows=rows,k=k,fmt=fmt)],1,1,32,rows_per_macro=128)
    events=list(A.source_request_calendar(a,'w.weight',0,0))
    assert len(events)==rows*groups*8
    last={}
    for event in events:
        for addr in event['addresses']:
            assert event['cycle']-last.get(addr['macro'],-2)>=2
            last[addr['macro']]=event['cycle']
    source_cycles=events[-1]['cycle']+1
    cal=A.selected_calendar(a,['w.weight'])['tiles'][0]['matrices'][0]
    assert source_cycles<=cal['source_request_cycles_upper']
    assert source_cycles<=cal['issue_cycles']
    assert sum(e['macro_busy_stall_cycles'] for e in events)<=cal['macro_busy_stalls_upper']


def test_odd_dense_request_tail_really_stalls_not_bubble_assumption():
    a=A.allocate([tensor(rows=1,k=5120)],1,1,4)
    events=list(A.source_request_calendar(a,'w.weight',0,0))
    assert len(events)==24
    assert sum(e['macro_busy_stall_cycles'] for e in events)==7
    assert events[-1]['cycle']+1==31
