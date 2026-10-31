import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan')
import schema as S, lane_add as LA
raw=json.load(open(sys.argv[1])); P=S.Plan(raw)
for n in ('NW_su11','NW_su10','NW_su31','NW_su30','NW_b113','NW_b112','NW_b100','NW_b102','NW_b101','NW_b103','NW_spu0','NW_b012','NW_b003'):
    t=P.ptype(n); w,h=t['outline_um']; hc=t.get('hard_cores',[])
    ca=sum(c['outline_um'][0]*c['outline_um'][1] for c in hc)
    print(n,P.parts[n]['type'],[round(v,1) for v in P.rect(n)],'cores',len(hc),'frac',round(ca/(w*h),3))
    if n in ('NW_b100','NW_b102'):
        for c in hc: print('    ',c['inst'],c['module'],c['outline_um'],c['origin_um'])
print('su11|b113',LA.shared_edge(P,'NW_su11','NW_b113'),'gap',round(LA.gap_um(P,'NW_su11','NW_b113'),1))
print('b100|b102',LA.shared_edge(P,'NW_b100','NW_b102'),'gap',round(LA.gap_um(P,'NW_b100','NW_b102'),1))
for lid,ln in P.lanes.items():
    ps=[P.ports[q] for q in ln['ports']]; s,d=ps[0]['src']['part'],ps[-1]['dst']['part']
    if {s,d} in ({'NW_su11','NW_b113'},{'NW_su31','NW_b113'}): print(lid,s,'->',d,ps[0]['width'],raw['latency']['lanes'][lid]['cycles'],[x['dst']['part'] for x in ps])
