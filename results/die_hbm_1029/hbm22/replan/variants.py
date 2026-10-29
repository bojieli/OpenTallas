import sys, json
sys.argv=['x','lanes.json','rows103.json','rows_h8b.json']
import replan_est as R
V={
 'VA_min': (False, ["NW_b102","NW_b103","NW_b111","NW_su20","NW_su21","NW_spu1","NW_su30","NW_su31","NW_b110","NW_b100","NW_b101"],
                   ["NW_b113","NW_b112","NW_su00","NW_su01","NW_spu0","NW_su10","NW_su11"]),
 'VB_opt': (True, ["NW_spu1","NW_b103","NW_b102","NW_b100","NW_b101","NW_su20","NW_su21","NW_su31","NW_su30"],
                  ["NW_spu0","NW_su01","NW_su00","NW_b110","NW_b113","NW_b111","NW_b112","NW_su11","NW_su10"]),
 'VB2':    (True, ["NW_spu1","NW_b102","NW_b100","NW_b101","NW_b103","NW_su20","NW_su21","NW_su31","NW_su30"],
                  ["NW_spu0","NW_su01","NW_su00","NW_b110","NW_b113","NW_b111","NW_b112","NW_su11","NW_su10"]),
 'VB3':    (True, ["NW_spu1","NW_b102","NW_b100","NW_b101","NW_b103","NW_su20","NW_su21","NW_su31","NW_su30"],
                  ["NW_spu0","NW_su01","NW_b112","NW_b111","NW_b113","NW_b110","NW_su00","NW_su11","NW_su10"]),
}
out={}
for k,(b,A,C) in V.items():
    R.SIZE.clear()
    if b: R.SIZE.update({'NW_spu0':466.56,'NW_spu1':1468.8+1218.24})
    rect=R.apply_rows({'A':A,'C':C}); s=R.score(rect)
    moved={n for n in rect if abs(rect[n][0]-R.rect0[n][0])>0.01 or abs(rect[n][1]-R.rect0[n][1])>0.01 or abs(rect[n][2]-R.rect0[n][2])>0.01}
    aff=[l for l in R.D['lanes'] if any(a in moved or c in moved for a,c in l['hops'])]
    far_new=[(a,b2,nb) for (a,b2),(pb,nb) in R.pairs.items() if nb and R.rel(rect[a],rect[b2])[0]<R.MIN_EDGE and R.rel(rect[a],rect[b2])[1]>R.NEAR]
    out[k]=dict(order_A=A,order_C=C,sfu_rowC=b,moved=len(moved),lanes_rerouted=len(aff),lane_bits_rerouted=sum(l['w'] for l in aff),
        far_pairs_new=len(far_new),far_bits_new=sum(x[2] for x in far_new),unadj_new_bits=s['new_unadj'],
        far_pairs_all=s['far_pairs'],far_bits_all=s['far_bits'],bit_mm_all=s['bit_mm'],edge_over=len(s['edge_over']),
        far_new_list=sorted(far_new,key=lambda x:-x[2]))
    print(k,{kk:v for kk,v in out[k].items() if kk not in('order_A','order_C','far_new_list')})
base=R.score(dict(R.rect0)); print('BASE',{k:v for k,v in base.items() if k!='edge_over'})
out['BASE']=dict(far_pairs_all=base['far_pairs'],far_bits_all=base['far_bits'],bit_mm_all=base['bit_mm'],far_bits_new=base['new_far'],unadj_new_bits=base['new_unadj'])
json.dump(out,open('variants_est.json','w'),indent=1)
