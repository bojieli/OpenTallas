#!/usr/bin/env python3
"""Whole-graph equivalence certificate for unconditional FF replication.

The lemma (clone_miter.sv) proves equal Q after one source-clock edge when
same-edge FFs share D. This checker accepts ONLY that transformation: original
ports/nets/cells are preserved and every changed consumer sees its source's
copy. Thus every original next-state function and output is unchanged under
the proved Q relation. This is component RTL proof, not routed-kit LEC.
"""
import argparse,copy,json,pathlib

def check(old,new,report):
    assert set(old['modules'])==set(new['modules'])=={'ot_hgi_sfu_split3_ctl_rest'}
    a=old['modules']['ot_hgi_sfu_split3_ctl_rest'];b=new['modules']['ot_hgi_sfu_split3_ctl_rest']
    for key,value in a.items():
        if key not in {'cells','netnames'}:assert b[key]==value, ('module metadata changed',key)
    for n,v in a['netnames'].items():assert b['netnames'][n]==v, ('original net changed',n)
    oldbits={x for c in a['cells'].values()for v in c['connections'].values()for x in v if isinstance(x,int)}
    oldbits|={x for n in a['netnames'].values()for x in n['bits']if isinstance(x,int)}
    cloneq={};sources=set();extras=set()
    for row in report:
        src=a['cells'][row['source']];assert src['type']=='$_DFF_P_', src['type']
        assert src['connections']['Q']==[row['q']]
        sources.add(row['source'])
        assert b['cells'][row['source']]['connections']==src['connections'], 'source FF itself was rewired'
        for r in row['copies']:
            cn=r['cell'];extras.add(cn);cc=b['cells'][cn];q=cc['connections']['Q']
            assert len(q)==1 and q[0] not in oldbits and q[0] not in cloneq
            expected=copy.deepcopy(src);expected['connections']['Q']=q;expected.setdefault('attributes',{})['keep']='1'
            assert cc==expected, ('copy changed clock/D/function',cn)
            cloneq[q[0]]=row['q']
    assert set(b['cells'])-set(a['cells'])==extras
    assert set(a['cells'])<=set(b['cells'])
    rewired=0
    for n,oldc in a['cells'].items():
        c=b['cells'][n]
        for key,value in oldc.items():
            if key=='connections':continue
            if key=='attributes' and n in sources:
                expected=dict(value);expected['keep']='1';assert c[key]==expected
            else:assert c[key]==value,(n,key)
        assert set(c['connections'])==set(oldc['connections'])
        for port,bits in oldc['connections'].items():
            now=c['connections'][port];assert len(now)==len(bits)
            for before,after in zip(bits,now):
                if before==after:continue
                assert c['port_directions'][port]=='input'
                assert cloneq.get(after)==before,('consumer not rewired to its source copy',n,port)
                rewired+=1
    return {'component_verdict':'STRUCTURALLY_EQUIVALENT_AFTER_ONE_SOURCE_EDGE','original_cells':len(a['cells']),
            'added_ff':len(extras),'rewired_input_bits':rewired,'PIN_CYCLES':0,'routed_kit_lec':'NOT_RUN','base_contract':'existing64source-clock boot edges; copies converge after first edge'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('old',type=pathlib.Path);p.add_argument('new',type=pathlib.Path);p.add_argument('report',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);args=p.parse_args()
    a=json.loads(args.old.read_text());b=json.loads(args.new.read_text());r=json.loads(args.report.read_text())
    result=check(a,b,r)
    cn=r[0]['copies'][0]['cell'];before=b['modules']['ot_hgi_sfu_split3_ctl_rest']['cells'][cn]['connections']['D']
    b['modules']['ot_hgi_sfu_split3_ctl_rest']['cells'][cn]['connections']['D']=['0' if before!=['0'] else '1']
    try:check(a,b,r)
    except AssertionError:result['wrong_D_mutant']='CAUGHT'
    else:raise AssertionError('wrong-D mutant survived')
    args.out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
