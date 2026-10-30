import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-41/tools/die_plan')
import schema as S, lane_add as LA
raw=json.load(open(sys.argv[1])); P=S.Plan(raw)
a,b=sys.argv[2].split('|')
df,lo,hi=LA.shared_edge(P,a,b)
rows=[]
for pid,pr in P.ports.items():
    if 'face' not in pr: continue
    s,d=pr['src']['part'],pr['dst']['part']
    if not ((s==a and pr['face']==df) or (d==a and LA.OPP.get(pr['face'])==df) or (s==b and pr['face']==LA.OPP[df]) or (d==b and LA.OPP.get(pr['face'])==LA.OPP[df])): continue
    for _,_,w in S.port_segments(pr):
        w=sorted(w)
        if w[1]<lo or w[0]>hi: continue
        rows.append((w[0],w[1],pid,s,d,pr['width'],pr.get('layers')))
tot=0
for r in sorted(rows):
    L=r[1]-r[0]; tot+=L
    print(f"{r[0]:9.1f} {r[1]:9.1f} len {L:7.1f} w {r[5]:5d} b/um {r[5]/max(L,1e-3):5.2f} {r[2]} {r[3]}->{r[4]} {r[6]}")
L=S.window_for(0.0,2066,['M6','M4'],P.layers,per_um=6.0,track_max=0.6); print('window_for 2066 pins',L)
