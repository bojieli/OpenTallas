#!/usr/bin/env python3
"""Apply the reviewed B2-D3 candidate and regenerate neighbor FT + latency.

Still a single pending S81 plan event, no freeze or kit release. The explicit
bank recipe is a master-plan/generator input; it must be consumed before build.
"""
import gzip,json,sys
from pathlib import Path
repo=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(repo),str(repo/'tools/die_plan')]
import schema as S
import ft_sites
import gen
from tools.die_trial.legal_sites import RowAllocator

raw=json.load(gzip.open(out/'die_plan_b2d3_preview.json.gz'))
old=json.load(gzip.open(repo/'physical/die_plan/s81/b2d2_1026/die_plan_b2d2.json.gz'))
ledger=json.load(open(out/'ledger.json'))
tn=ledger['type'];t=raw['partition_types'][tn]
b=next(x for x in t['buses'] if x['name']=='xtier_o0')
core='u_bk_sel.u_sel.u_g.vo_s'
means=lambda bank:[sum(x[k]+([1.404,.27][k]/2) for x in bank)/len(bank) for k in (0,1)]
reg_centres=[means(x) for x in ledger['banks_ll_um'][:2]]
t.setdefault('internal_stations',[]).append({'conn':'bus:xtier_o0','from_um':[1164.6,501.15],
    'to_um':means(ledger['banks_ll_um'][2]),'regs_um':reg_centres,'bits':276,
    'launch':core,'capture':core,
    'bit_sites_um':ledger['banks_ll_um'][:2],'bit_site_cell_um':ledger['cell_um'],
    'face_bit_sites_um':ledger['banks_ll_um'][2],
    'note':'B2-D3: +2 egress-only cycles, core vo_s -> 2 FIRM stations -> source face reg. Exact277-bit banks in b2d3_0733/ledger.json; must be consumed by master-plan slice/generator before any build. No q/control loop cycles.'})
for k,rect in enumerate(ledger['bays_um']):
    t.setdefault('channels',[]).append({'rect_um':rect,'reason':f'B2-D3 reserved egress bank{k}:277 FF incl epoch,<=60% fill; exact sites ledger.json'})
parts={p['name']:p for p in raw['partitions']}
bp=parts['bk_sel'];assert bp.get('orient','R0')=='R0'
pr=next(p for p in raw['ports'] if p['src']['part']=='bk_sel' and p['src']['bus']=='xtier_o0')
window=[bp['origin_um'][0]+x for x in b['window_um']]
nb=parts[pr['dst']['part']];nt=raw['partition_types'][nb['type']]
assert nb['orient']=='MY' and sum(p['type']==nb['type'] for p in raw['partitions'])==1
slot=next(s for s in nt['ft_slots'] if pr['dst']['bus']==s['name']+'_i')
old_ft=slot['stations'];nw=nt['outline_um'][0];nx=nb['origin_um'][0]
slot['in_window_um']=[round(nx+nw-window[1],6),round(nx+nw-window[0],6)]
pr['window_um']=window
lane=next(l for l in raw['lanes'] if pr['id'] in l['ports'])
assert not lane.get('fixed_cycles'),lane
lane['fixed_cycles']=2
physical_ledger,_=ft_sites.place(raw,RowAllocator,types=[nb['type']])
json.dump(physical_ledger,open(out/'neighbor_ft_ledger.json','w'),indent=2)
P=S.Plan(raw,repo/'physical/die_plan/s81/die_plan_b2d3_0733.json')
tab=gen.latency_table(P)
raw['latency']={'lanes':tab}
delta={key:{'old':old.get('latency',{}).get('lanes',{}).get(key),'new':v,
            'delta_cycles':v['cycles']-old['latency']['lanes'][key]['cycles']}
       for key,v in tab.items() if key in old['latency']['lanes'] and v['cycles']!=old['latency']['lanes'][key]['cycles']}
ledger.update({'state':'PENDING SINGLE B2 EVENT; no kit/freeze/adoption',
 'neighbor':nb,'neighbor_ft':slot['name'],'neighbor_old_stations':old_ft,'neighbor_new_stations':slot['stations'],
 'source_lane':lane['id'],'latency_delta_from_b2d2':delta,
 'native_bind_requirement':{'internal_stations_types':[tn],'source_lane_fixed_cycles':2},
 'materialization':'Exact277-bit banks now consumed by canonical kit_istations tool (51f9bd78a); actual native rebind/kit still held on master-plan slice.',
 'epoch_source_blocker':ledger['epoch_first_source'],
 'capacity_blocker':'Actual M5/M7 PG/via-field/corridor traffic check still required before P&R.'})
json.dump(ledger,open(out/'event_ledger.json','w'),indent=2)
with gzip.open(out/'die_plan_b2d3.json.gz','wt') as f:json.dump(raw,f,separators=(',',':'))
(repo/'physical/die_plan/s81/die_plan_b2d3_0733.json').write_text(json.dumps(raw,separators=(',',':'))+'\n')
print(json.dumps({'neighbor_ft_stations':[old_ft,slot['stations']],'latency_delta':{k:v['delta_cycles'] for k,v in delta.items()}},indent=1))
