#!/usr/bin/env python3
"""Native port scope must be reciprocal hard-child connectivity inside each same parent partition."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import native_seams as N
SCOPE=['send_d','send_r','send_v']
WIDTHS={'prod':dict(clk=1,rst_n=1,i_v=1,i_d=8,i_ready=1,send_r=1,send_v=1,send_d=8),
        'dp':dict(clk=1,rst_n=1,send_r=1,send_v=1,send_d=8,o_r=1,o_v=1,o_d=8)}


def context_fixture(root,module):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for mod,wds in WIDTHS.items():
        pins=[dict(name=bus if n==1 else f'{bus}[{b}]',layer='M4',x=0,y=0) for bus,n in wds.items() for b in range(n)]
        (root/(mod+'.pins.json')).write_text(json.dumps(pins))
    children=lambda p,q:[dict(inst=p,module='prod',outline_um=[20,20],pins_file='prod.pins.json'),
                         dict(inst=q,module='dp',outline_um=[20,20],pins_file='dp.pins.json')]
    plan=dict(partition_types=dict(P=dict(hard_cores=children('p','q')),M=dict(hard_cores=children('p2','q2'))))
    conns={parent:{p:{n:['core:'+q] for n in SCOPE},q:{n:['core:'+p] for n in SCOPE}}
           for parent,p,q in [('P','p','q'),('M','p2','q2')]}
    (root/'core_conns.json').write_text(json.dumps(conns))
    raw=json.dumps(plan).encode();(root/'die_plan.json').write_bytes(raw)
    view=dict(module=module,pins_sha256=hashlib.sha256((root/(module+'.pins.json')).read_bytes()).hexdigest(),outline_um=[20,20])
    other='dp' if module=='prod' else 'prod'
    request=dict(schema=N.SCHEMA,module=module,peers={n:dict(module=other,port=n) for n in SCOPE})
    return N.validate(plan,root,view,SCOPE,request,hashlib.sha256(raw).hexdigest())


def run():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);context=context_fixture(root,'prod')
        assert len(context['parent_contexts'])==2
        assert context['bus_widths']==dict(send_d=8,send_r=1,send_v=1)
        plan=json.loads((root/'die_plan.json').read_text())
        view=dict(module='prod',pins_sha256=context['pins_sha256'],outline_um=[20,20])
        request=dict(schema=N.SCHEMA,module='prod',peers={n:dict(module='dp',port=n) for n in SCOPE})
        baseline=json.loads((root/'core_conns.json').read_text())
        for name,edit in [
            ('external',lambda a:a['P']['p'].__setitem__('send_d',['bus:external'])),
            ('mixed_external',lambda a:a['P']['p'].__setitem__('send_d',['core:q','bus:external'])),
            ('peer_not_hard_child',lambda a:a['P']['p'].__setitem__('send_d',['core:q_elsewhere'])),
            ('not_reciprocal',lambda a:a['P']['q'].__setitem__('send_d',['bus:external'])),
            ('other_replica_external',lambda a:a['M']['p2'].__setitem__('send_r',['bus:external']))]:
            bad=copy.deepcopy(baseline);edit(bad);(root/'core_conns.json').write_text(json.dumps(bad))
            try:N.validate(plan,root,view,SCOPE,request,context['plan_sha256'])
            except ValueError:print(name,'REJECTED')
            else:raise AssertionError(name+' accepted')
        (root/'core_conns.json').write_text(json.dumps(baseline))
        original=(root/'dp.pins.json').read_text()
        pins=json.loads(original);pins=[row for row in pins if row['name']!='send_d[7]']
        (root/'dp.pins.json').write_text(json.dumps(pins))
        try:N.validate(plan,root,view,SCOPE,request,context['plan_sha256'])
        except ValueError:print('width_mismatch REJECTED')
        else:raise AssertionError('native peer width mismatch accepted')
        (root/'dp.pins.json').write_text(original)
        # A declared peer in a different partition is insufficient; only the current parent's child list qualifies.
        badplan=copy.deepcopy(plan);badplan['partition_types']['P']['hard_cores'].pop()
        try:N.validate(badplan,root,view,SCOPE,request,context['plan_sha256'])
        except ValueError:print('different_parent REJECTED')
        else:raise AssertionError('different-parent child accepted')
    print('test_native_seams PASS')

if __name__=='__main__':run()
