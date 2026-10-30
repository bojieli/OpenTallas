import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-41/tools/die_plan')
import schema as S, lane_add as LA
raw=json.load(open(sys.argv[1])); P=S.Plan(raw)
per=float(P.budgets.get("face_pins_per_um",6.0)); tm=float(P.budgets.get("pin_track_max",0.6))
print('budget face_pins_per_um',per,'pin_track_max',tm,'face_pin_layers',P.budgets.get('face_pin_layers'),'reach',P.budgets.get('ft_station_max_um'))
for e in sys.argv[2].split(','):
    a,b=e.split('|')
    se=LA.shared_edge(P,a,b)
    if not se: print(e,'NO EDGE gap',round(LA.gap_um(P,a,b),1)); continue
    df,lo,hi=se
    lay=LA.face_layers(P,a,df); layb=LA.face_layers(P,b,LA.OPP[df])
    occ=LA.face_intervals(P,a,df)+LA.face_intervals(P,b,LA.OPP[df])
    gaps=LA.free_gaps(lo+1,hi-1,occ,2.0)
    used=sum(min(hi,y)-max(lo,x) for x,y in S_merge(occ)) if False else None
    # merged occupancy
    m=[]; 
    for x,y in sorted(occ):
        x,y=max(x,lo),min(y,hi)
        if y<=x: continue
        if m and x<=m[-1][1]: m[-1][1]=max(m[-1][1],y)
        else: m.append([x,y])
    occl=sum(y-x for x,y in m)
    gl=sorted((round(y-x,1) for x,y in gaps),reverse=True)
    perL=per*len(lay)/float(P.budgets.get("face_pin_layers",2))
    print(f"{e} face {df} edge {lo:.1f}-{hi:.1f} len {hi-lo:.1f} occ {occl:.1f} ({100*occl/(hi-lo):.0f}%) layers {lay}/{layb} free_total {sum(gl):.1f} cap_bits~{sum(gl)*perL:.0f} biggest {gl[:6]}")
