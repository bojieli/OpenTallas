"""Bounded per-bit/model-footprint search on a frozen generated landing row.

Never runs GEN or writes a contract. SYNTH LEF coordinates remain estimates.
"""
import argparse,hashlib,json,math
from pathlib import Path
from case_reach import lef,xf
from relay_row_model import layout,exact_contract_cost,Reservations


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('case');a.add_argument('contract');a.add_argument('row');a.add_argument('out')
    args=a.parse_args();case=Path(args.case)
    m=json.loads((case/'manifest.json').read_text());c=json.loads(Path(args.contract).read_text())
    names=sorted([n for n in m['placement'] if n.startswith(args.row+'_l')],key=lambda n:int(n.rsplit('_l',1)[1]))
    if not names: raise ValueError('missing landing row')
    nameset=set(names)
    edges=[e for e in c['edges'] if e['source'][0] in nameset or e['sink'][0] in nameset]
    endpoints=nameset|{e[k][0]for e in edges for k in ['source','sink']}
    # Add raw contract clock/reset producers separately: none may be mistaken
    # for a proved regional root/phase/first-active landing.
    cr=[r for r in c['clock_resets']if r['instance']in nameset]
    cre=[dict(source=[r['source'][0],r['source'][1],0,1],sink=[r['instance'],r['port'],i,i+1],bits=1)
         for r in cr for i in range(r['bits'])]
    endpoints|={e['source'][0]for e in cre}
    masters={n:m['placement'][n]['m']for n in endpoints}
    views={}
    for master in set(masters.values()): views.update(lef(case/'views'/(master+'.lef')))
    widths={(n,p):v['bits']for n in endpoints for p,v in c['instances'][n]['ports'].items()}
    placements={n:dict(x=m['placement'][n]['x'],y=m['placement'][n]['y'],orient=m['placement'][n]['o'])for n in endpoints}
    baseline=exact_contract_cost(edges,placements,masters,views,widths)
    clock_reset=exact_contract_cost(cre,placements,masters,views,widths)
    def category(edge):
        sp,tp=edge['source'][1],edge['sink'][1]
        if sp in ('ck_o','clk_out','clk_fwd') or tp in ('ckf','clk_fwd'):
            return 'forwarded_clock'
        if sp in ('rs','rst_n','reset_n') or tp in ('rs','rst_n','reset_n'):
            return 'reset_edge'
        if sp in ('eb','ea','en') or tp in ('eb','ea','en'):
            return 'epoch_control'
        return 'data_control'
    typed={}
    for typ in sorted({category(e)for e in edges}):
        selected=[e for e in edges if category(e)==typ]
        cost=exact_contract_cost(selected,placements,masters,views,widths)
        worst=sorted(cost['over_reach'],key=lambda x:-x['span_um'])[:8]
        for pair in worst:
            for role in ('source','sink'):
                n,pin=pair[role];v=views[masters[n]]
                pair[role+'_detail']=dict(instance=n,master=masters[n],pin=pin,LEFdirection=v['directions'][pin],
                    LEFuse=v['uses'][pin],placement=placements[n],LEFwh=[v['w'],v['h']],
                    local_pin=v['pins'][pin],die_pin=xf(placements[n],v['w'],v['h'],*v['pins'][pin]),
                    qualification=m['routed_view_qualification'].get(masters[n],'unknown'))
        typed[typ]=dict(bit_edges=cost['bits_checked'],max_um=cost['max_span_um'],over405=len(cost['over_reach']),worst=worst,
                       port_edges=[dict(source=e['source'],sink=e['sink'],bits=e['bits'])for e in selected])
    root_types={}
    for kind in ('clock','reset'):
        selected=[e for e in cre if any(r['instance']==e['sink'][0]and r['port']==e['sink'][1]and r['kind']==kind for r in cr)]
        if selected:
            cost=exact_contract_cost(selected,placements,masters,views,widths)
            root_types[kind]=dict(bit_edges=cost['bits_checked'],max_um=cost['max_span_um'],worst=sorted(cost['over_reach'],key=lambda x:-x['span_um'])[:8],
                 interpretation='Global CLOCK root Manhattan distance is NOT a data405 violation; actual CTS/root/phase authority required' if kind=='clock' else 'Reset source distance requires actual regional/reset landing authority; not inferred from data routing')
    wh={(m['placement'][n]['w'],m['placement'][n]['h'])for n in names}
    if len(wh)!=1: raise ValueError('coupon requires equal exact tile dimensions')
    wh=wh.pop();x=min(placements[n]['x']for n in names);y=min(placements[n]['y']for n in names)
    occupied=[(n,v['x'],v['y'],v['x']+v['w'],v['y']+v['h'])for n,v in m['placement'].items()if n not in nameset]
    candidates=[]
    for columns in (1,3,6,9,len(names)):
        bank=layout(names,wh,columns)
        for dx in (-86.4,0,86.4):
            for dy in (-86.4,0,86.4):
                pl=dict(placements)
                for n,(ox,oy)in bank['offsets'].items():pl[n]=dict(x=x+dx+ox,y=y+dy+oy,orient='R0')
                reserve=Reservations(m['die_um'],occupied)
                ok,conflict=reserve.reserve({n:pl[n]for n in names},views,masters)
                cost=exact_contract_cost(edges,pl,masters,views,widths)
                candidates.append(dict(columns=columns,offset=[dx,dy],width=bank['width'],height=bank['height'],
                    nonoverlap=ok,conflict=conflict,max_um=cost['max_span_um'],over405=len(cost['over_reach']),
                    all_data_forward_edges_fit=cost['feasible']and ok))
    result=dict(status='MODEL ONLY / rawclock-reset qualification OPEN / no GEN or binding',row=args.row,
        inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [case/'manifest.json',Path(args.contract)]},
        actual_generated_master=masters[names[0]],tile_wh=wh,tiles=len(names),bit_edges=baseline['bits_checked'],
        baseline_max_um=baseline['max_span_um'],baseline_over405=len(baseline['over_reach']),
        clock_reset_ports=cr,raw_clock_reset_max_um=clock_reset['max_span_um'],raw_clock_reset_over405=len(clock_reset['over_reach']),
        typed_bit_costs=typed,raw_root_costs=root_types,
        LEFsha256={master:hashlib.sha256((case/'views'/(master+'.lef')).read_bytes()).hexdigest()for master in views},
        candidates=candidates,feasible_data_candidates=sum(r['all_data_forward_edges_fit']for r in candidates),
        qualification='Frozen generated SYNTH per-bit pins, not hardened native pins. No source, stage/depth, schedule or production phase change.')
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['inputs','clock_reset_ports','candidates']}))


if __name__=='__main__':main()
