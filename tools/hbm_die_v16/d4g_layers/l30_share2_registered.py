#!/usr/bin/env python3
"""H15.8 actual REG1 share source and exact16 CLOSED KQ leaves, no cycle change for KQ."""
import argparse,collections,copy,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
Q=('SW','SE','NW','NE')
VIEW='physical/ref_tile/hcoll_kqs_leaf_1018/views/ot_hgi_coll_kq_share2_leaf'
REGION='d4g_l30_h158'
OR_SRC='rtl/hbm_accel/die_glue/ot_hbm_kqs_fault_or4.sv'

def split_edge(edge,endpoint,parent):
    at=edge[endpoint];lo,hi=at[2:];out=[]
    assert edge['bits']==hi-lo, ('noncontiguous edge',edge)
    for pair in range(4):
        a=max(lo,562*pair);b=min(hi,562*(pair+1))
        if a>=b:continue
        e=copy.deepcopy(edge);e['name']+=f'_p{pair}';e['bits']=b-a
        e[endpoint]=[parent+f'_p{pair}',at[1],a-562*pair,b-562*pair]
        other='sink' if endpoint=='source' else 'source'
        v=e[other];e[other]=v[:2]+[v[2]+a-lo,v[2]+b-lo]
        e['region']=REGION;out.append(e)
    assert sum(e['bits'] for e in out)==edge['bits']
    return out

def apply(c,grants):
    I=c['instances'];report=dict(registered_soft=[],closed_kq_leaves=[],kq_latency_delta=0,consumer_share_extra_edges=2)
    for name in ['hb_idx__nwsh']+['hcollrs_'+q for q in Q]:
        i=I[name];assert i['master']=='ot_hbm_idx_vm_share2_static', (name,i['master'])
        i['master']='ot_hbm_idx_vm_share2_static_r';i.pop('physical_view',None);i.pop('closed_record',None)
        i['force_synth']=True;i['params'].pop('REG',None)
        i['note']+=' | H15.8 REG1 soft; +2 actual consumer edges priced by L12 SHARE_EXTRA, no BANK_RT6 hard alias'
        report['registered_soft'].append(name)
    source='rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv'
    text=(ROOT/source).read_text();old=subprocess.check_output(['git','-C',str(ROOT),'show','7ff7a9f0d:'+source]).decode()
    pat=r'module ot_hgi_coll_kq_share2_leaf\b[\s\S]*?endmodule'
    body=re.search(pat,text).group();assert body==re.search(pat,old).group(), 'CLOSED KQ body mismatch'
    assert (ROOT/'rtl/lib/ot_rst_relay.sv').read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show','7ff7a9f0d:rtl/lib/ot_rst_relay.sv'])
    report['closed_leaf_body_sha256']=hashlib.sha256(body.encode()).hexdigest()
    bindings=json.loads((ROOT/'results/arch/hbm_die_d4g/collq/kqs_leaf_binding.json').read_text())['instances']
    slots={g['name']:g for g in grants['slots']};newslots=[]
    for q in Q:
        parent='hcollks_'+q;oldi=I[parent];assert oldi['master']=='ot_hgi_coll_kq_share2' and oldi['params']=={}
        slot=slots[oldi['slot']];assert slot['outline']==dict(w=345.6,h=345.6)
        # Keep existing parent fault sink and the exact OR4 expression; no NF widening.
        I[parent]=dict(master='ot_hbm_kqs_fault_or4',source=OR_SRC,rtl_deps=[],params={},slot='collks_fault_'+q,
                       region=REGION,note='Exact OR4 from original KQ parent; leaf sticky fault timing unchanged',
                       force_synth=True,ports=dict(leaf_faults=dict(direction='input',bits=4),fault=dict(direction='output',bits=1)))
        cr=[r for r in c['clock_resets'] if r['instance']==parent]
        clk=next(r for r in cr if r['kind']=='clock');rst=next(r for r in cr if r['kind']=='reset')
        assert clk['bits']==4 and rst['bits']==1
        c['clock_resets']=[r for r in c['clock_resets'] if r['instance']!=parent]
        edges=[]
        for e in c['edges']:
            if e['source'][0]==parent and e['source'][1]=='vm_kq':edges+=split_edge(e,'source',parent)
            elif e['sink'][0]==parent:
                assert e['sink'][1] in ('a_kq','b_kq');edges+=split_edge(e,'sink',parent)
            else:edges.append(e)
        c['edges']=edges
        for pair,(dx,dy) in enumerate(((0,0),(172.8,0),(172.8,172.8),(0,172.8))):
            name=parent+f'_p{pair}';i=copy.deepcopy(bindings[name]);i.pop('slot_origin',None);i.pop('slot_size',None)
            i.update(physical_view=VIEW,closed_record='hcoll_kqs_leaf_1018-k1-7ff7a9f0d CLOSED; body/dependency exact',region=REGION)
            I[name]=i;report['closed_kq_leaves'].append(name)
            for rec,port in ((clk,'clk'),(rst,'rst_n')):
                r=copy.deepcopy(rec);r.update(instance=name,port=port,bits=1);c['clock_resets'].append(r)
            c['edges'].append(dict(name=f'h158_{name}_fault',bits=1,source=[name,'fault',0,1],sink=[parent,'leaf_faults',pair,pair+1],clock='stream',ready_or_credit=False,region=REGION))
            s=copy.deepcopy(slot);s.update(name=i['slot'],cell=i['master'],outline=dict(w=129.6,h=129.6),kit='physical/ref_tile/hcoll_kqs_leaf_1018')
            s['origin'].update(x=slot['origin']['x']+dx,y=slot['origin']['y']+dy);s['clock_entry']['offset']=64.8;newslots.append(s)
        s=copy.deepcopy(slot);s.update(name='collks_fault_'+q,cell='ot_hbm_kqs_fault_or4',outline=dict(w=43.2,h=43.2),kit=None)
        s['origin'].update(x=slot['origin']['x']+129.6,y=slot['origin']['y']+129.6);s.pop('clock_entry',None);newslots.append(s)
    grants['slots']=[s for s in grants['slots'] if s['name'] not in {'collks_'+q for q in Q}]+newslots
    c['masters']=dict(sorted(collections.Counter(i['master'] for i in I.values()).items()))
    c['summary'].update(instances=len(I),edges=len(c['edges']),edge_bits=sum(e['bits'] for e in c['edges']),clock_reset_ports=len(c['clock_resets']))
    report['qualification']='SOURCE_SELECTION; current S4/L12 repricing + GEN geometry + required S11 timing/IR remain'
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('grants',type=Path);p.add_argument('output',type=Path);p.add_argument('output_grants',type=Path);p.add_argument('--report',required=True,type=Path);a=p.parse_args()
    c=json.loads(a.input.read_text());g=json.loads(a.grants.read_text());r=apply(c,g)
    for path,item in ((a.output,c),(a.output_grants,g),(a.report,r)):path.write_text(json.dumps(item,indent=1)+'\n')
    print('H158_SOURCE_SELECTED',len(r['registered_soft']),'REG1soft',len(r['closed_kq_leaves']),'CLOSED_KQ')
