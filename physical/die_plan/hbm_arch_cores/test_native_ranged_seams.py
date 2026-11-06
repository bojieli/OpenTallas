#!/usr/bin/env python3
"""One wide producer and four identical-master peers; actual bit nets are authority."""
import copy,hashlib,json,tempfile
from pathlib import Path
import native_seams as N

def digest(obj):return hashlib.sha256(json.dumps(obj).encode()).hexdigest()
def write(root,name,obj):
    (root/name).write_text(json.dumps(obj));return digest(obj)

def fixture(root):
    wds={'out':dict(clk=1,rst_n=1,d=32,v=4,r=4),'ks':dict(clk=1,rst_n=1,d=8,v=1,r=1)}
    dirs={'out':dict(clk='input',rst_n='input',d='output',v='output',r='input'),
          'ks':dict(clk='input',rst_n='input',d='input',v='input',r='output')}
    pins={mod:write(root,mod+'.json',[dict(name=b if n==1 else f'{b}[{i}]') for b,n in wd.items() for i in range(n)]) for mod,wd in wds.items()}
    children=[dict(inst=i,module=m,pins_file=m+'.json',outline_um=[20,20]) for i,m in [('o','out')]+[(f'k{n}','ks') for n in range(4)]]
    plan=dict(partition_types=dict(P=dict(hard_cores=children)))
    conn=dict(clk=[2],rst_n=[3],d=list(range(10,42)),v=list(range(42,46)),r=list(range(46,50)))
    cells={'o':dict(type='out',connections=conn,port_directions=dirs['out'])}
    eps=[dict(inst='o',module='out',pins_sha256=pins['out'],clock_port='clk',reset_port='rst_n',buses={b:[] for b in ('d','v','r')})]
    for n in range(4):
        inst=f'k{n}';connections={b:(conn[b] if b in ('clk','rst_n') else conn[b][(n*8 if b=='d' else n):((n+1)*8 if b=='d' else n+1)]) for b in conn}
        cells[inst]=dict(type='ks',connections=connections,port_directions=dirs['ks'])
        ep=dict(inst=inst,module='ks',pins_sha256=pins['ks'],clock_port='clk',reset_port='rst_n',buses={})
        for b in ('d','v','r'):
            width=8 if b=='d' else 1;lo=n*width
            eps[0]['buses'][b].append(dict(own_lsb=lo,width=width,peer_inst=inst,peer_module='ks',peer_port=b,peer_lsb=0))
            ep['buses'][b]=[dict(own_lsb=0,width=width,peer_inst='o',peer_module='out',peer_port=b,peer_lsb=lo)]
        eps.append(ep)
    modules={m:dict(attributes=dict(blackbox=1),ports={b:dict(direction=dirs[m][b],bits=list(range(n))) for b,n in wd.items()}) for m,wd in wds.items()}
    modules['P']=dict(cells=cells,ports={})
    netlist=dict(modules=modules);sha=write(root,'parent.json',netlist)
    ctx=dict(parent_partition_type='P',netlist=dict(path='parent.json',sha256=sha,top='P'),endpoints=eps)
    request=dict(schema=N.RANGED_SCHEMA,module='out',contexts=[ctx])
    view=dict(module='out',pins_sha256=pins['out'],outline_um=[20,20])
    return plan,request,view,netlist

def run():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);plan,req,view,nl=fixture(root)
        good=N.validate(plan,root,view,['d','v','r'],req,digest(plan))
        assert good['bus_widths']==dict(d=32,v=4,r=4)
        import internal_core_guard as I
        I.check_ranged_context(good,good['parent_contexts'][0])
        for field in ('netlist_sha256','family_endpoints'):
            bad=copy.deepcopy(good);bad['parent_contexts'][0].pop(field)
            try:I.check_ranged_context(bad,bad['parent_contexts'][0])
            except ValueError:print('receipt_'+field,'REJECTED')
            else:raise AssertionError('damaged receipt accepted')
        # Select the identical-master receiver view: all four replicas must match.
        kr=copy.deepcopy(req);kr['module']='ks';kv=dict(module='ks',pins_sha256=req['contexts'][0]['endpoints'][1]['pins_sha256'],outline_um=[20,20])
        assert len(N.validate(plan,root,kv,['d','v','r'],kr,digest(plan))['parent_contexts'])==4
        def check(name,mutate,change_net=False):
            p,r,v,n=map(copy.deepcopy,(plan,req,view,nl));mutate(p,r,v,n)
            if change_net:r['contexts'][0]['netlist']['sha256']=write(root,'parent.json',n)
            else:write(root,'parent.json',nl)
            try:N.validate(p,root,v,['d','v','r'],r,digest(p))
            except (ValueError,KeyError,OSError):print(name,'REJECTED')
            else:raise AssertionError(name+' accepted')
        ep=lambda r:r['contexts'][0]['endpoints']
        cells=lambda n:n['modules']['P']['cells']
        check('wrong_instance',lambda p,r,v,n:ep(r)[0]['buses']['d'][0].update(peer_inst='k1'))
        check('wrong_master',lambda p,r,v,n:ep(r)[0]['buses']['d'][0].update(peer_module='other'))
        check('wrong_port',lambda p,r,v,n:ep(r)[0]['buses']['d'][0].update(peer_port='v'))
        check('overlap',lambda p,r,v,n:ep(r)[0]['buses']['d'][1].update(own_lsb=0))
        check('missing_coverage',lambda p,r,v,n:ep(r)[0]['buses']['d'].pop())
        check('missing_reciprocal',lambda p,r,v,n:ep(r)[1]['buses']['d'][0].update(peer_lsb=1))
        check('missing_replica',lambda p,r,v,n:ep(r).pop())
        check('different_parent',lambda p,r,v,n:p['partition_types']['P']['hard_cores'].pop())
        check('missing_evidence',lambda p,r,v,n:r['contexts'][0]['netlist'].update(path='absent.json'))
        check('wrong_hash',lambda p,r,v,n:r['contexts'][0]['netlist'].update(sha256='0'*64))
        check('net_reorder',lambda p,r,v,n:cells(n)['k0']['connections']['d'].reverse(),True)
        check('constant',lambda p,r,v,n:cells(n)['k0']['connections']['d'].__setitem__(0,'0'),True)
        check('clock',lambda p,r,v,n:cells(n)['k0']['connections'].update(clk=[100]),True)
        check('reset',lambda p,r,v,n:cells(n)['k0']['connections'].update(rst_n=[101]),True)
        check('direction',lambda p,r,v,n:cells(n)['k0']['port_directions'].update(d='output'),True)
        check('external',lambda p,r,v,n:n['modules']['P']['ports'].update(leak=dict(direction='output',bits=[10])),True)
        check('extra_load',lambda p,r,v,n:cells(n).update(tap=dict(type='buf',connections=dict(A=[10]))),True)
        check('actual_master',lambda p,r,v,n:cells(n)['k0'].update(type='other'),True)
        print('native_ranged_seams PASS: wide producer and all4 identical-master peers;18 negatives')
if __name__=='__main__':run()
