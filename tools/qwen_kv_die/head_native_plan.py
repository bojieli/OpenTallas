#!/usr/bin/env python3
"""Native Qwen head (r2, 51 roots) intra-slot plan: lane8/ktree R0 grid inside the qkd_rhead 734.4 x 855.36 contract slot,
greedy stin/stout placement minimising each lane's worst hop (front->stin, stin->lane8, lane8->stout, stout->ktree,
stout->astk face).  Usage: head_native_plan.py OUT.json   (kvsys-elements r2, 2026-10-14)"""
W,H=734.4,855.36
import itertools, json, sys
LW=129.6
def lane_in(x,y): return (x+12.3,y)            # S-face input cluster (x 0.7..24)
def lane_out(x,y): return (x+129.6,y+70.6)     # E-face outputs (y 48..93)
def man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
def rect_face_pt(r,face,tgt):
    x,y,w,h=r
    if face=='N': return (min(max(tgt[0],x),x+w),y+h)
    if face=='S': return (min(max(tgt[0],x),x+w),y)
    if face=='W': return (x,min(max(tgt[1],y),y+h))
    if face=='E': return (x+w,min(max(tgt[1],y),y+h))
def overlap(a,b,m=5.4):
    return not (a[0]+a[2]+m<=b[0] or b[0]+b[2]+m<=a[0] or a[1]+a[3]+m<=b[1] or b[1]+b[3]+m<=a[1])
def evaluate(P, astk='E', ectl='N', verbose=False):
    lanes=P['lanes']; fr=P['front']; kt=P['ktree']; sc=P['score']; st=P['stations']; F=P['faces']
    rows=[]
    for t,(lx,ly) in enumerate(lanes):
        s=st[t]
        li=lane_in(lx,ly); lo=lane_out(lx,ly)
        sin=rect_face_pt(s,F['st_in'],(fr[0]+fr[2]/2,fr[1]+fr[3]/2))
        fo=rect_face_pt(fr,F['fr_out'],sin); rows.append(('front->st%d'%t,man(fo,sin)))
        so=rect_face_pt(s,F['st_lane_out'],li); rows.append(('st%d->lane'%t,man(so,li)))
        si=rect_face_pt(s,F['st_lane_in'],lo); rows.append(('lane%d->st'%t,man(lo,si)))
        kpx=kt[0]+101.34-(101.34-5.34)*t/15.0; kp=(kpx,kt[1]+97.16)
        sk=rect_face_pt(s,F['st_kp_out'],kp); rows.append(('st%d->ktree'%t,man(sk,kp)))
        nbface=(W if astk=='E' else 0.0)
        sn=rect_face_pt(s,F['st_nb_out'],(nbface,s[1])); rows.append(('st%d->nb_edge'%t,abs(sn[0]-nbface)+0))
    kso=(kt[0]+133,kt[1]); si=rect_face_pt(sc,F['sc_in'],kso); rows.append(('ktree->score',man(kso,si)))
    eface=(H if ectl=='N' else 0.0)
    so=rect_face_pt(sc,F['sc_out'],(sc[0],eface)); rows.append(('score->ectl_edge',abs(so[1]-eface)))
    fi=rect_face_pt(fr,F['fr_in'],(fr[0],eface)); rows.append(('ectl_edge->front',abs(fi[1]-eface)))
    # overlaps
    rects=[(x,y,LW,LW) for x,y in lanes]+[fr,kt,sc]+list(st)
    ov=[(i,j) for i,j in itertools.combinations(range(len(rects)),2) if overlap(rects[i],rects[j])]
    oob=[i for i,r in enumerate(rects) if r[0]<0 or r[1]<0 or r[0]+r[2]>W+1e-6 or r[1]+r[3]>H+1e-6]
    return rows,ov,oob
LANES=[(x,y) for y in (0,140.4,585.36,725.76) for x in (0,183.6,367.2,550.8)]
FR=(237.6,400.0,259.2,162.0); KT=(291.6,286.2,151.2,97.2); SC=(448.2,286.2,43.2,43.2)
order=sorted(range(16),key=lambda t:(LANES[t][0],LANES[t][1])); KTI={t:15-i for i,t in enumerate(order)}   # ktree kp_in: lane 0 at the E end of its N face
def grid(w,h,step,fixed):
    xs=set(x*step for x in range(int((W-w)/step)+1)); ys=set(y*step for y in range(int((H-h)/step)+1))
    for f in fixed:
        xs|={round(f[0]+f[2]+5.4,3),round(f[0]-5.4-w,3)}; ys|={round(f[1]+f[3]+5.4,3),round(f[1]-5.4-h,3)}
    xs={x for x in xs if 0<=x<=W-w}; ys={y for y in ys if 0<=y<=H-h}
    g=[(x,y) for x in sorted(xs) for y in sorted(ys)]
    return [p for p in g if not any(overlap((p[0],p[1],w,h),f) for f in fixed)]
def place(lanes,fr,kt,sc,astk,F,step=10.8,verbose=False):
    fixed=[(x,y,LW,LW) for x,y in lanes]+[fr,kt,sc]
    nbx=W if astk=='E' else 0.0
    placed=[]; worst={}
    gi=grid(54,43.2,step,fixed); go=grid(43.2,43.2,step,fixed)
    pos={}
    for t in sorted(range(16),key=lambda t:-abs(lanes[t][0]+65-W/2)-abs(lanes[t][1]+65-H/2)):
        lx,ly=lanes[t]; li=lane_in(lx,ly); lo=lane_out(lx,ly)
        best=None
        for gx,gy in gi:
            r=(gx,gy,54,43.2)
            if any(overlap(r,p) for p in placed): continue
            sin=rect_face_pt(r,F['i_in'],(fr[0]+fr[2]/2,fr[1])); fo=rect_face_pt(fr,'S',sin)
            so=rect_face_pt(r,F['i_out'],li)
            m=max(man(fo,sin),man(so,li))
            if best is None or m<best[0]: best=(m,r)
        placed.append(best[1]); pos[('i',t)]=best
        kp=(kt[0]+101.34-(101.34-5.34)*KTI[t]/15.0,kt[1]+97.16)
        best=None
        for gx,gy in go:
            r=(gx,gy,43.2,43.2)
            if any(overlap(r,p) for p in placed): continue
            si=rect_face_pt(r,F['o_in'],lo); sk=rect_face_pt(r,F['o_kp'],kp); sn=rect_face_pt(r,F['o_nb'],(nbx,r[1]))
            m=max(man(lo,si),man(sk,kp),abs(sn[0]-nbx))
            if best is None or m<best[0]: best=(m,r)
        placed.append(best[1]); pos[('o',t)]=best
    return max(v[0] for v in pos.values()),pos

FACES=dict(i_in='E',i_out='S',o_in='N',o_kp='E',o_nb='E')     # stin in E / out S; stout in N / out E
FRONT=(259.2,394.2,259.2,172.8); KTREE=(313.2,286.2,151.2,97.2); SCORE=(469.8,286.2,43.2,43.2)
if __name__=='__main__':
    out=sys.argv[1]
    plans={}
    for astk in ('E','W'):
        m,pos=place(LANES,FRONT,KTREE,SCORE,astk,FACES,step=10.8)
        lanes=[]
        for p,(lx,ly) in enumerate(LANES):
            lanes.append({'lane':KTI[p],'lane8':[lx,ly],'stin':list(pos[('i',p)][1][:2]),'stout':list(pos[('o',p)][1][:2]),
                'hop_um':{'stin_max(front->stin,stin->lane8)':round(pos[('i',p)][0],1),
                          'stout_max(lane8->stout,stout->ktree,stout->astk_face)':round(pos[('o',p)][0],1)}})
        lanes.sort(key=lambda d:d['lane'])
        plans['astk_'+astk]={'max_intra_hop_um':round(m,1),'lanes':lanes}
    order=[d['lane'] for d in sorted(plans['astk_E']['lanes'],key=lambda d:d['stin'][0])]
    doc={'schema':'qwen-kvsys-head-native-plan/r2','slot':'qkd_rhead','slot_outline_um':[W,H],'orient_all_leaves':'R0',
      'leaves':{'front':{'master':'ot_qkh_head_front_native','xy':FRONT[:2],'wh':FRONT[2:]},
                'ktree':{'master':'ot_qkh_ktree','view':'physical/ref_tile/qkh_ktree_ref/views/ot_qkh_ktree','xy':KTREE[:2],'wh':KTREE[2:]},
                'score':{'master':'ot_qkh_head_score_native','xy':SCORE[:2],'wh':SCORE[2:]},
                'lane8':{'master':'ot_qkh_lane8','view':'physical/ref_tile/qkh_lane8_ref_b/views/ot_qkh_lane8','wh':[LW,LW]},
                'stin':{'master':'ot_qkh_head_stin_native','wh':[54.0,43.2]},'stout':{'master':'ot_qkh_head_stout_native','wh':[43.2,43.2]}},
      'faces':{'front':{'N':'die inputs (ectl t0/t1 word, hid strap)','S':'f_t<lane> x16 in station x order + pack_fault','W':'clk rst_n'},
               'stin':{'E':'cr_i dr_i','S':'cr_o dr_o lane_rst_n','W':'clk rst_n'},'stout':{'N':'kp_i kpv_i gf_i nb_i','E':'kp_o kpv_o gf_o nb_o','W':'clk rst_n'},
               'score':{'W':'sc_i sf_i gf_i kt_rst_n','N':'pack_fault','E':'sc_o sf_o gf_o (to die)','S':'clk rst_n'}},
      'front_port_order_W_to_E':order,'plans':plans,
      'clock_entries_per_head':51,'reach_rule_um':500,
      'die_hops_owned_by_lead':{'ectl->front N face':'near head ~290 um from the ectl-side slot edge to the front N face (+ ectl depth); FAR head adds the 855 um near-head slot: ~1.15 mm -> die relays + equal latency for the 4 heads of an ectl (lead decision)',
                                'score E face -> ectl':'same geometry as ectl->front','stout nb -> astk':'<= max_intra_hop_um to the slot face + astk depth'}}
    json.dump(doc,open(out,'w'),indent=1); print({k:v['max_intra_hop_um'] for k,v in plans.items()}, order)
