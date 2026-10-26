import sys,json,collections
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/path-hbm-r9-1026/tools/die_plan')
import hbm_r9_delta as D
P=json.load(open('/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json'))
t=P['partition_types'][sys.argv[1]]; S=int(sys.argv[2])
Q=D.plan_quadrants(t,S)
k=S//2-1  # middle boundary
C=collections.Counter(); hc={h['inst']:h for h in Q['cores']}
def lab(e):
    if e[0]=='F':
        y=e[2][1]; H=t['outline_um'][1]
        return 'faceNS' if (y<=0.5 or y>=H-0.5) else 'faceEW'
    m=hc[e[1]]['module']; return ('R:' if '__q' in e[1] else 'D:')+m
for s,ea,eb,ka,kb in Q['stations']:
    if min(ka,kb)<=k<max(ka,kb):
        C[(lab(ea),lab(eb))]+=s['bits']
tot=sum(C.values()); print('boundary',k,'bits',tot)
for kk,v in C.most_common(25): print(v,kk)
