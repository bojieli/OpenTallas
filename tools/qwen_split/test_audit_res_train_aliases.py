"""Independent negative controls for the numeric/physical alias identity audit."""
from copy import deepcopy
import pytest
from qwen_split.audit_res_train_aliases import audit, COMMAND, TAPS


def fixture():
    insts=[dict(n='tt_ctlm',m='tt'),dict(n='peer',m='peer'),dict(n='res_train_issue',m='issue')]
    insts += [dict(n=f'sp_res_ser_{b}',m='ser') for b in range(3)]
    def pins(port,width):
        return [dict(name=f'{port}[{b}]',layer='M4',rect=[0,b,1,b+.1]) for b in range(width)]
    old=dict(insts=deepcopy(insts),masters={'tt':dict(pins=pins('ib',380)+pins('c1',341)),
                  'peer':dict(pins=pins('ib',380)+pins('c1',341)),
                  'issue':dict(pins=[]),'ser':dict(pins=[])},
             buses=[dict(b=port,c='data',n=n,e=[['tt_ctlm',port],['peer',port]]) for port,n in [('ib',380),('c1',341)]],port_join={})
    new=deepcopy(old)
    new['buses']=[]
    new['port_join']={'tt':{},'peer':{}}
    new['masters']['tt']['pins']=[];new['masters']['peer']['pins']=[]
    for real,width in [('ib',380),('c1',341)]:
        # Per-bit aliases intentionally stress numeric index versus alias index.
        for b in range(width):
            a=f'{real}__{b}_{b}'
            es=[['tt_ctlm',a],['peer',a]]
            for mst in ('tt','peer'):
                new['port_join'][mst][a]=[real,[b]]
                new['masters'][mst]['pins'].append(dict(name=a+'[0]',layer='M4',rect=[0,b,1,b+.1]))
            for sink,(src,lo,hi) in TAPS.items():
                if src==real and lo<=b<=hi:
                    name=f'{sink}__{b-lo}_{b-lo}'
                    new['port_join'].setdefault('issue',{})[name]=[sink,[b-lo]]
                    new['masters']['issue']['pins'].append(dict(name=name+'[0]',layer='M4',rect=[0,b,1,b+.1]))
                    es.append(['res_train_issue',name])
            new['buses'].append(dict(b=a,c='data',n=1,e=es))
    for port,width in COMMAND.items():
        new['masters']['issue']['pins']+=pins(port,width)
        if port not in [p['name'].split('[')[0] for p in new['masters']['ser']['pins']]:
            new['masters']['ser']['pins']+=pins(port,width)
        new['buses'].append(dict(b=port,c='data',n=width,e=[['res_train_issue',port]]+[[f'sp_res_ser_{b}',port] for b in range(3)]))
    old['insts']=[i for i in old['insts'] if i['n']!='res_train_issue']
    return old,new


def test_exact_aliases_pass():
    a,b=fixture();r=audit(a,b)
    assert r['verdict']=='PASS',r
    assert r['numeric_physical_pins_checked']==1442
    assert r['source_bits']==721 and r['command_bits']==42


@pytest.mark.parametrize('mutant,kind',[
    ('movement','pin_moved'),('missing_pin','missing_or_extra_numeric_pin'),
    ('permutation','numeric_connectivity'),('missing_peer','numeric_connectivity'),
    ('duplicate_net','source_multiconnection'),('duplicate_pin','malformed_alias_or_pin'),
    ('command_width','issuer_command_fanout')])
def test_mutants_refused(mutant,kind):
    a,b=fixture()
    if mutant=='movement':b['masters']['peer']['pins'][0]['rect'][0]=.5
    elif mutant=='missing_pin':b['masters']['peer']['pins'].pop(0)
    elif mutant=='permutation':
        x=b['port_join']['peer'];x['ib__0_0'][1]=[1];x['ib__1_1'][1]=[0]
    elif mutant=='missing_peer':b['buses'][0]['e'].pop(1)
    elif mutant=='duplicate_net':b['buses'].append(deepcopy(b['buses'][0]))
    elif mutant=='duplicate_pin':b['masters']['peer']['pins'].append(deepcopy(b['masters']['peer']['pins'][0]))
    else:b['buses'][-1]['n']=3
    r=audit(a,b)
    assert r['verdict']=='FAIL'
    assert kind in r['failure_counts'],r
