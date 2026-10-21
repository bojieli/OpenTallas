#!/usr/bin/env python3
"""Prepare the exact CPLW source/geometry candidate without activating its physical view.

The production static calendar must first consume the cumulative edge ledger.
This helper never changes a running source snapshot or declares a die bind PASS.
"""
import argparse,copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BIND=ROOT/'results/arch/hbm_dbk_cplw_binding_1021/binding.json'
NEW='ot_hgi_dma_back_static_vp4_banks_cplw'
OLD='ot_hgi_dma_back_static_vp4_banks_cp'
VIEW='physical/ref_tile/hv16_dbk_cpl_w1/views/'+NEW

def apply(c,g):
    b=json.loads(BIND.read_text())
    for s in b['sources']:
        assert hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()==s['sha256'],s['path']
    slots={s['name']:s for s in g['slots']};selected=[]
    for q in ('SW','SE','NW','NE'):
        n='hb_dbk_'+q;i=c['instances'][n]
        assert i['master']==OLD and i['params']=={},(n,i['master'],i['params'])
        i.update(master=NEW,source=b['sources'][0]['path'],params={'RR_RT':80},
                 rtl_deps=[s['path'] for s in b['sources'][1:]],force_synth=True,
                 candidate_physical_view=VIEW, candidate_closed_record=b['qualified_record'])
        i.pop('physical_view',None);i.pop('closed_record',None)
        i['note']+=' | CPLW SOURCE CANDIDATE ONLY: production cumulative calendar and exact mapper77 pending; no physical alias'
        base=next(r for r in c['clock_resets'] if r['instance']==n and r['port']=='clk')
        for p,w in (('clk_land',8),('clk_rly',3),('clk_out',4)):
            assert p not in i['ports'];i['ports'][p]=dict(direction='input',bits=w)
            r=copy.deepcopy(base);r.update(port=p,bits=w);c['clock_resets'].append(r)
        i['slot']=n; s=slots[n]
        # Old child/floorplan annotations do not describe this different parent.
        for key in ('children','synth','pins','source_sha256','parent_qualified','controller_binding_status','child_binding_refresh_2116'):
            s.pop(key,None)
        s.update(cell=NEW,source=i['source'],params={'RR_RT':80},outline={'w':606.96,'h':542.16},
                 candidate_physical_view=VIEW,qualification='SOURCE_CANDIDATE_ONLY')
        selected.append(n)
    # Actual new outline covers two previously placed small relays. Move those
    # real21.6um cells into clear left channels, then require actualGEN/S4 reprice.
    for n,x,y in (('stu_SW_00',10209.456,10297.8),('stu_NW_00',10398.456,22177.8)):
        i=c['instances'][n];assert not i.get('slot'),(n,i.get('slot'))
        i['slot']=n+'_cplw_clear';s=dict(name=i['slot'],cell=i['master'],kind='relay',parent='die',
            instance=n,outline={'w':21.6,'h':21.6},origin={'x':x,'y':y,'orient':'R0'},
            layer_rule='tile',signal_max_layer='M6',pg_layer='M7',strap_layer='M8')
        g['slots'].append(s)
    import collections
    c['masters']=dict(sorted(collections.Counter(i['master'] for i in c['instances'].values()).items()))
    c['summary']['clock_reset_ports']=len(c['clock_resets'])
    return dict(status='UNBOUND_SOURCE_CANDIDATE',selected=selected,physical_view_activation=False,
        source_identity=b['sources'],physical_parameter_resolution=b['parameters'],
        mapper={'RR_RT':80,'old_raw_target':79,'new_raw_target':77,'physical_port_interval':78,
                'rule_reference_parameter':7,'rule_reference_roundtrip':4,'require_exact_equality':True},
        cumulative_edge_ledger=b['cumulative_edge_ledger_relative_CP'],
        obligations=['production compiler consumes cumulative request/read/write/fill/ready events',
                     'replace CP L12 budget with CPLW RR_RT80 and exact mapper reference7/roundtrip4',
                     'explicit ignored-wrapper-param resolution to fixed physical child80',
                     'individual real physical clock entries and hard child insertion refs',
                     'actual GEN geometry/S4 hop and capacity/strict bind/TT-FF STA/required IR'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('input','grants','output','output_grants','report'):p.add_argument(n,type=Path)
    a=p.parse_args();c=json.loads(a.input.read_text());g=json.loads(a.grants.read_text());r=apply(c,g)
    for path,item in ((a.output,c),(a.output_grants,g),(a.report,r)):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(item,indent=1)+'\n')
    print('DBK_CPLW_UNBOUND_CANDIDATE',len(r['selected']),'physical_activation=0 mapper77/calendar_pending')
