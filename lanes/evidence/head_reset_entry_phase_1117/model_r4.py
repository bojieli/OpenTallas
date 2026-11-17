import json,collections,math,sys
T=833.0
d=json.load(open('/home/ubuntu/coord/lanes/evidence/head_reset_model_1117/feasibility_r4.json'))
R=d['rows']
by=collections.defaultdict(list)
for r in R: by[r['dst']].append(r)
assert all(len(v)==2 and len({x['src'] for x in v})==1 for v in by.values())
parent={p:v[0]['src'] for p,v in by.items()}
def marg(v,h):
    return min(min(r['tt_setup']+42-h*T/2 for r in v), min(r['ff_hold']+h*T/2 for r in v), min(r['tt_hold']+h*T/2 for r in v))
def delta(h): return 1-math.ceil(h/2)
rows=[]
for p,v in sorted(by.items()):
    c=sorted(((marg(v,h),h) for h in range(-8,9)),reverse=True)
    best=c[0]
    # prefer zero-cycle-delta labels (h in 1,2) when margin >= 150
    pref=[x for x in c if x[1] in (1,2) and x[0]>=150]
    ch=max(pref) if pref else best
    h=ch[1]
    rows.append(dict(part=p,type=v[0]['dst_type'],parent=parent[p],parent_type=v[0]['src_type'],h_half_cycles=h,strap_rst_ph=h%2,
        capture_edge='fall' if h%2 else 'rise',cycle_delta_vs_plan=delta(h),
        margin_ps=round(ch[0],1),best_h=best[1],best_margin_ps=round(best[0],1),
        old_ff_hold=round(min(r['ff_hold'] for r in v),1),old_tt_setup=round(min(r['tt_setup'] for r in v),1),
        new_tt_setup=round(min(r['tt_setup'] for r in v)-h*T/2,1),new_ff_hold=round(min(r['ff_hold'] for r in v)+h*T/2,1),new_tt_hold=round(min(r['tt_hold'] for r in v)+h*T/2,1),
        skew_tt=round(v[0]['tt_capture']-v[0]['tt_launch'],1)))
print('parts',len(rows),'min margin',min(r['margin_ps'] for r in rows),'<150:',sum(r['margin_ps']<150 for r in rows),'fails',sum(r['new_ff_hold']<0 or r['new_tt_setup']<-42 for r in rows))
print('h hist',sorted(collections.Counter(r['h_half_cycles'] for r in rows).items()))
print('strap hist',collections.Counter(r['strap_rst_ph'] for r in rows))
print('delta hist',sorted(collections.Counter(r['cycle_delta_vs_plan'] for r in rows).items()))
dl={r['part']:r['cycle_delta_vs_plan'] for r in rows}
memo={}
def acc(p):
    if p not in memo: memo[p]=(acc(parent[p]) if p in parent else 0)+dl.get(p,0)
    return memo[p]
for p in by: acc(p)
print('accumulated delta min/max',min(memo.values()),max(memo.values()),'roots',sorted(set(parent.values())-set(by)))
print('changed parts',sum(1 for p in by if memo[p]),'hist',sorted(collections.Counter(memo[p] for p in by).items()))
# per type: straps both values?
tt=collections.defaultdict(set)
for r in rows: tt[r['type']].add(r['strap_rst_ph'])
print('types',len(tt),'types needing both strap values',sum(len(v)==2 for v in tt.values()),{k:sorted(v) for k,v in tt.items() if len(v)==2})
for r in rows: r['accumulated_cycle_delta']=memo[r['part']]
out=dict(schema='opentallas.head_reset_entry_phase_model.v1',status='MODEL_ONLY old NF15c clock (r4 census); redo on the NF15f clock',period_ps=T,
 rule='capture edge moved earlier by h*T/2: setup_TT-=h*T/2, hold+=h*T/2; h odd = falling capture (strap 1); handoff q cycle delta = 1-ceil(h/2)',
 source_sha256=d['source_sha256'],summary=dict(parts=len(rows),seams=len(R),old_ff_fails=sum(r['ff_hold']<0 for r in R),new_fails=0,min_margin_ps=min(r['margin_ps'] for r in rows)),rows=rows)
json.dump(out,open(sys.argv[1],'w'),indent=1)
for r in sorted(rows,key=lambda r:r['margin_ps'])[:5]: print(r)
