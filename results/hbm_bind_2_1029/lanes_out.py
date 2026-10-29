"""HBM-BIND-2: UNPLANNED lane list of the winning form (S1 = h1) for DIE-HBM-14 (combined C25c event).
usage: lanes_out.py WINNER_REPORT B1S_REPORT S2_REPORT H2_REPORT OUT"""
import json,sys,re,collections
def load(f):
    d={}
    for e in json.load(open(f))['errors']:
        m=re.match(r'UNPLANNED (\S+) -> (\S+): (\d+) as-built crossing bits with no plan lane path \((\d+) b planned',str(e))
        if m: d[(m.group(1),m.group(2))]=(int(m.group(3)),int(m.group(4)))
    return d
W,B1,S2,H2=[load(f) for f in sys.argv[1:5]]
def cls(s,d):
    t=lambda x: re.sub(r'^(NE|NW)_','',x)
    a,b=t(s),t(d)
    if a.startswith('su') or b.startswith('su'):
        if a.startswith('b11') or b.startswith('b11'): return 'SFU<->SU (sfucore control at b113 talks to all 4 SU slices; plan has b113<->su00 only)'
        return 'SU slice split (B1s/Codex r3 two-halves control) / hub<->su'
    if re.match(r'b11',a) or re.match(r'b11',b): return 'SFU (control/store at b113 <-> grid lanes b110-b112 / hub)'
    if re.match(r'b[01][01]\d',a) and re.match(r'b[01][01]\d|root|hub',b) or re.match(r'b[01][01]\d',b) and re.match(r'root|hub',a):
        return 'IDX scorer (leaf W->E chain / split leaf / front<-hub,root / tail->root score)'
    return 'other (hub/root/spb/sm; pre-existing in B1s)'
rows=[]
for (s,d),(bits,pl) in sorted(W.items(),key=lambda x:-x[1][0]):
    rows.append(dict(src=s,dst=d,unplanned_bits=bits,planned_direct_bits=pl,cls=cls(s,d),in_b1s=B1.get((s,d),(0,0))[0]))
tot=lambda D: (len(D),sum(v[0] for v in D.values()))
byc=collections.defaultdict(lambda:[0,0])
for r in rows: byc[r['cls']][0]+=1; byc[r['cls']][1]+=r['unplanned_bits']
out=dict(schema='hbm_bind_2.unplanned_lanes.v1',winner='S1 = h1 (B1s two-halves SU control + landing homes)',
 totals=dict(S1_h1=tot(W),B1s=tot(B1),S2_central=tot(S2),h2_sfu_b110=tot(H2)),by_class={k:dict(pairs=v[0],bits=v[1]) for k,v in byc.items()},
 note='Bits = as-built crossing bits with no plan lane path on plan 16e0513d (bind.py strict). Scorer: plan lands root->scorer inputs (L80m 171 b, L124m 9 b) and the score output (L64m 297 b) at b101; hub->front L6m/L7m (4968 b) only for N quarters (b100). Extending those lanes by hops (root..b101->b100, b103->b102->b101) carries the root/score bits; S quarters (front b000) have only 304 b hub->b000.',
 rows=rows)
json.dump(out,open(sys.argv[5],'w'),indent=1)
print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=1))
