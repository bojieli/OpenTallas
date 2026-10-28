"""DIE-QC-10 plan input: QC local forwarding tree 'rt2' (ladder arms) from feed_grpP.json.
Each A0 arm (2 x 4 regions per half column): the x0 column chains from the slice (bottom: sl_su_l1 -> bn_00 -> bn_01 -> bf_00
-> bf_01; top: sl_st_a -> tn_00 -> tn_01 -> tf_00 -> tf_01) and every x1 region hangs from its SAME-ROW x0 neighbour (rung), so
every arm data link closes a <= 4-hop loop.  Slice hubs, slice chain and coll band keep the feed_grpP edges (coll_s ring residual:
5 crossings, cut kept at coll_s<->c_W5_bf_00, the fewest-bit edge of that ring).  New taps = centre of the shared face."""
import json, sys
B='/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/'
F=json.load(open(B+'feed_grpP.json')); box={r['tag']:r['box_um'] for r in json.load(open(B+'regions_map.json'))['regions']}
par=dict(F['parent']); tap=dict(F['tap'])
cols=sorted({r.split('_')[1] for r in box if r.startswith('c_')})
def face(p,c):
    P,C=box[p],box[c]; x0,x1=max(P[0],C[0]),min(P[2],C[2]); y0,y1=max(P[1],C[1]),min(P[3],C[3])
    assert x1-x0>=-1e-6 and y1-y0>=-1e-6 and (x1-x0>1 or y1-y0>1), (p,c)
    return [round((x0+x1)/2,3),round((y0+y1)/2,3)]
changed=[]
for X in cols:
    for (n,f,e0) in (('bn','bf',f'sl_{X}_su_l1'),('tn','tf',f'sl_{X}_st_a')):
        c0=[f'c_{X}_{n}_00',f'c_{X}_{n}_01',f'c_{X}_{f}_00',f'c_{X}_{f}_01']
        c1=[f'c_{X}_{n}_10',f'c_{X}_{n}_11',f'c_{X}_{f}_10',f'c_{X}_{f}_11']
        want={c0[0]:e0, c0[1]:c0[0], c0[2]:c0[1], c0[3]:c0[2]}
        want.update({c1[i]:c0[i] for i in range(4)})
        for c,p in want.items():
            if par[c]!=p:
                tap.pop(f'{par[c]}->{c}',None); par[c]=p; changed.append(c)
            if f'{p}->{c}' not in tap: tap[f'{p}->{c}']=face(p,c)
# sanity: a tree
root=F['root']
for r in par:
    seen=set(); x=r
    while x is not None:
        assert x not in seen, r; seen.add(x); x=par[x]
    assert root in seen
out=dict(root=root,parent=par,joined=F.get('joined',[]),tap={k:v for k,v in tap.items() if par[k.split('->')[1]]==k.split('->')[0]},
         note='DIE-QC-10 rt2 ladder-arm forwarding tree (from feed_grpP.json; %d regions re-parented)'%len(changed))
assert len(out['tap'])==len(par)-1, (len(out['tap']),len(par))
json.dump(out,open(sys.argv[1],'w'),indent=1)
print('re-parented',len(changed),'taps',len(out['tap']))
