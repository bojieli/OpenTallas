import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_core_graph as G


def vehicle(tmp_path,names):
    cores=[]
    for n in names:
        pf=n+'.json';(tmp_path/pf).write_text(json.dumps([dict(name='d',x=.019,y=5)]))
        cores.append(dict(inst=n,module=n,pins_file=pf))
    return dict(partition_types={'t':dict(hard_cores=cores)})


def test_one_producer_multidrop_does_not_invent_consumer_links(tmp_path):
    raw=vehicle(tmp_path,['a','b','c'])
    conn=lambda tn,t,h:(h['inst'],{'d':[('a__d',0)]})
    direction=lambda tn,h,label,p,v:'output' if h['inst']=='a' else 'input'
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,direction)
    assert r['verdict']=='PASS' and len(edges)==2
    assert cc['t']['a']['d']==['core:b','core:c']
    assert cc['t']['b']['d']==['core:a'] and cc['t']['c']['d']==['core:a']


def test_two_physical_copies_cannot_claim_one_native_source(tmp_path):
    raw=vehicle(tmp_path,['a','b'])
    conn=lambda tn,t,h:('same_native',{'d':[('a__d',0)]})
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,lambda *args:'output')
    assert r['verdict']=='FAIL' and len(r['source_alias_collisions'])==1 and not edges


def test_missing_physical_port_binding_fails(tmp_path):
    raw=vehicle(tmp_path,['a'])
    cc,edges,r=G.build(raw,tmp_path,lambda tn,t,h:('a',{}),lambda tn,h,l:l,lambda *a:'input')
    assert r['verdict']=='FAIL' and any(e['kind']=='port_binding' for e in r['errors'])


def test_actual_bus_bit_source_is_required(tmp_path):
    raw=vehicle(tmp_path,['a']);conn=lambda tn,t,h:('a',{'d':[('host__d',0)]})
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,lambda *a:'input')
    assert r['verdict']=='FAIL' and any(e['kind']=='producer_count' for e in r['errors'])
    bus=[dict(type='t',bus='L0_i',direction='input',bits=[['host__d',0]])]
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,lambda *a:'input',bus_bindings=bus)
    assert r['verdict']=='PASS' and cc['t']['a']['d']==['bus:L0_i']


def test_multiple_producers_are_not_silently_merged(tmp_path):
    raw=vehicle(tmp_path,['a','b','c']);conn=lambda tn,t,h:(h['inst'],{'d':[('net',0)]})
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,lambda tn,h,*a:'input' if h['inst']=='c' else 'output')
    assert r['verdict']=='FAIL' and not edges and any(e.get('producer_count')==2 for e in r['errors'])


def test_native_alias_collision_is_global_across_partition_types(tmp_path):
    raw=vehicle(tmp_path,['a','b'])
    a,b=raw['partition_types']['t']['hard_cores']
    raw['partition_types']={'t0':dict(hard_cores=[a]),'t1':dict(hard_cores=[b])}
    conn=lambda tn,t,h:('one_native',{'d':[('net',0)]})
    cc,edges,r=G.build(raw,tmp_path,conn,lambda tn,h,l:l,lambda *a:'output')
    assert r['verdict']=='FAIL' and len(r['source_alias_collisions'])==1 and not edges
