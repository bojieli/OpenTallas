import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import copy
import pytest
import bind_elab as E
from bind_compose import compose, CompositionError

class Rules:
    def part_of(self,p): return 'hg' if p.startswith('top.') else None

def fixture():
    f=E.Flat();f.new(10)
    f.top_ports={'out':('output',[5])}
    f.cells=[E.Cell('top.front','front',{'W':'2'},{'hid':['0','0'],'clk':[1],'q':[2,3]},
                   {'hid':'input','clk':'input','q':'output'},'leaf'),
             E.Cell('top.stin','regpair',{'W':'2'},{'clk':[1],'d':[2,3],'q':[4,6]},
                   {'clk':'input','d':'input','q':'output'},'leaf'),
             E.Cell('top.lane','lane',{}, {'clk':[1],'hid':[4,6],'bsel':['0','0'],'y':[5]},
                   {'clk':'input','hid':'input','bsel':'input','y':'output'},'leaf')]
    ep=lambda m,p,i:dict(member='top.'+m,port=p,bit=i)
    spec={'cores':[dict(inst='top.core',module='real_core',members=[c.path for c in f.cells],ports={
        'clk':dict(dir='input',bits=[[ep(m,'clk',0) for m in ('front','stin','lane')]]),
        'strap_hid':dict(dir='input',bits=[[ep('front','hid',i)] for i in range(2)]),
        'strap_bsel':dict(dir='input',bits=[[ep('lane','bsel',i)] for i in range(2)]),
        'y':dict(dir='output',bits=[[ep('lane','y',0)]])})]}
    return f,spec

def test_preserves_registered_hid_and_exact_straps():
    f,s=fixture();sources,r=compose(f,Rules(),s,E.Cell)
    assert len(f.cells)==1 and f.cells[0].ports['strap_hid']==['0','0']
    rtl=sources[0][1]
    assert '.hid({n3, n2})' in rtl and '.q({n3, n2})' in rtl
    assert '.hid({strap_hid[1], strap_hid[0]})' in rtl
    assert '.W(2)' in rtl and r['cores'][0]['terminal_count']==16
    assert r['terminal_equality']

def test_wrong_index_is_rejected():
    f,s=fixture();s['cores'][0]['ports']['clk']['bits'][0][1]['port']='d'
    with pytest.raises(CompositionError,match='net or direction mismatch'):compose(f,Rules(),s,E.Cell)
    assert len(f.cells)==3

def test_missing_boundary_is_rejected():
    f,s=fixture();del s['cores'][0]['ports']['y']
    with pytest.raises(CompositionError,match='omitted boundary'):compose(f,Rules(),s,E.Cell)

def test_private_reset_or_distinct_clock_not_unified():
    f,s=fixture();f.cells[1].ports['clk']=[7]
    with pytest.raises(CompositionError,match='net or direction mismatch'):compose(f,Rules(),s,E.Cell)

def test_overlap_atomic():
    f,s=fixture();s['cores'].append(copy.deepcopy(s['cores'][0]))
    with pytest.raises(CompositionError,match='overlapping'):compose(f,Rules(),s,E.Cell)
    assert len(f.cells)==3

def test_output_driver_wrong_direction():
    f,s=fixture();s['cores'][0]['ports']['y']['dir']='input'
    with pytest.raises(CompositionError,match='direction mismatch'):compose(f,Rules(),s,E.Cell)

def test_unmapped_external_sink_is_boundary():
    f,s=fixture();f.cells.append(E.Cell('elsewhere.spy','spy',{}, {'d':[4]}, {'d':'input'},'leaf'))
    with pytest.raises(CompositionError,match='omitted boundary'):compose(f,Rules(),s,E.Cell)

def test_const_straps_are_endpoint_local():
    f,s=fixture();del s['cores'][0]['ports']['strap_bsel']
    sources,_=compose(f,Rules(),s,E.Cell)
    assert ".bsel({1'b0, 1'b0})" in sources[0][1]

def test_sparse_contiguous_port_indices_preserve_abi():
    f,s=fixture();s['cores'][0]['ports']['strap_hid']['indices']=[4,5]
    sources,_=compose(f,Rules(),s,E.Cell)
    assert 'input wire [5:4] strap_hid' in sources[0][1]
    assert '.hid({strap_hid[5], strap_hid[4]})' in sources[0][1]
    assert f.cells[0].ports['strap_hid']==['0','0']

def test_reject_duplicate_alias_ports_on_real_net():
    f,s=fixture();s['cores'][0]['ports']['clock_alias']=copy.deepcopy(s['cores'][0]['ports']['clk'])
    with pytest.raises(CompositionError):compose(f,Rules(),s,E.Cell)

def test_dissolved_constant_driver_is_preserved():
    f,s=fixture();f.cells[2].ports['bsel']=[7,7];f.const_drivers[7]=('1','dissolved.literal')
    del s['cores'][0]['ports']['strap_bsel']
    sources,_=compose(f,Rules(),s,E.Cell)
    assert "assign n4 = 1'b1;" in sources[0][1]

def test_hidden_undriven_internal_net_rejected():
    f,s=fixture();f.cells[2].ports['bsel']=[7,7]
    del s['cores'][0]['ports']['strap_bsel']
    with pytest.raises(CompositionError,match='no preserved driver'):compose(f,Rules(),s,E.Cell)


def test_explicit_live_clock_aliases_cover_disjoint_terminals():
    f,s=fixture();p=s['cores'][0]['ports'];old=p.pop('clk')
    for i,anchor in enumerate(old['bits'][0]):p['clk'+str(i)]=dict(dir='input',bits=[[anchor]])
    sources,_=compose(f,Rules(),s,E.Cell)
    assert all(f.cells[0].ports['clk'+str(i)]==[1] for i in range(3))
    assert all('.clk({clk'+str(i)+'[0]})' in sources[0][1] for i in range(3))

def test_incomplete_live_aliases_rejected():
    f,s=fixture();p=s['cores'][0]['ports'];old=p.pop('clk')
    for i,anchor in enumerate(old['bits'][0][:2]):p['clk'+str(i)]=dict(dir='input',bits=[[anchor]])
    with pytest.raises(CompositionError,match='complete terminal coverage'):compose(f,Rules(),s,E.Cell)

def test_repeated_same_master_has_identical_source_despite_global_net_ids():
    f,s=fixture();clones=copy.deepcopy(f.cells);core=copy.deepcopy(s['cores'][0])
    remap={c.path:c.path.replace('top.','top.rep.') for c in clones}
    for c in clones:
        c.path=remap[c.path]
        c.ports={p:[b+10 if isinstance(b,int) else b for b in bs] for p,bs in c.ports.items()}
    core['inst']='top.rep.core';core['members']=[remap[p] for p in core['members']]
    for pd in core['ports'].values():
        for anchors in pd['bits']:
            for a in anchors:a['member']=remap[a['member']]
    f.cells+=clones;f.top_ports['out2']=('output',[15]);s['cores'].append(core)
    sources,receipt=compose(f,Rules(),s,E.Cell)
    assert len(sources)==1 and len(f.cells)==2 and len(receipt['cores'])==2


def test_parent_input_alias_pattern_is_not_internal_master_topology():
    a,sa=fixture();b,sb=fixture()
    for spec in (sa,sb):
        ports=spec['cores'][0]['ports'];old=ports.pop('clk')
        for i,anchor in enumerate(old['bits'][0]):ports['clk'+str(i)]=dict(dir='input',bits=[[anchor]])
    b.cells[1].ports['clk']=[7];b.cells[2].ports['clk']=[8]
    b.top_ports['clk1']=('input',[7]);b.top_ports['clk2']=('input',[8])
    source_a,_=compose(a,Rules(),sa,E.Cell);source_b,_=compose(b,Rules(),sb,E.Cell)
    assert source_a==source_b
    assert a.cells[0].ports['clk1']==[1] and b.cells[0].ports['clk1']==[7]
    assert a.cells[0].ports['clk2']==[1] and b.cells[0].ports['clk2']==[8]
