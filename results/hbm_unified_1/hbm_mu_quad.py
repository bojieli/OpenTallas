#!/usr/bin/env python3
"""HBM-UNIFIED-1: structural fix for GEOM-13 hub-plan FAIL: one replicated 'VM/FUSED quad' tile per hub segment.
Plan geometry only (no packing of the rest of the hub, no stations, no cuts). Usage: hbm_mu_quad.py <candidate_NW.json> <candidate_NE.json> <outdir>
Quad = 2x2 bank-pair cells (each cell: [FUSED|VM] buddy A, n1 street, buddy B) around a centre service column
(hb_vms/xl_ctl/dbk/calendar/smw/vmdel x4/keybuf of the segment) with a symmetric H-tree n1 -> n2L/n2R -> n3 at the quad centre.
Same relative layout for q0/q1 and NW/NE (NE hub MY at die level => die-level mirror)."""
import json, sys, re, os
G=8.64
def r(v): return round(v,3)
nw,ne,out=sys.argv[1:4]; os.makedirs(out,exist_ok=True)
C=json.load(open(nw)); dims={h['module']:tuple(h['outline_um']) for h in C['hard_cores']}
VM=dims['hnx_vms_bank_q0_faces']; FU=dims['hnx_fused_lane']; TN=dims['ot_hnx_fused_tnode']
gap=G; bw=FU[0]+gap+VM[0]; bh=max(VM[1],FU[1])            # buddy 624.24 x 518.4
st1=TN[1]+2*G                                              # n1 street 190.08
cellh=2*bh+st1                                             # 1226.88
mid=TN[1]+2*G                                              # middle E-W street (n2/n3) 190.08
colw=881.28; s=43.2
xW=0; xC=bw+s; xE=xC+colw+s; QW=xE+bw
QH=8.64*320                                                # 2764.8 (hb_vms upper half needs 1334.88)
rows=[0.0, cellh+mid]
M={}   # member -> (x,y,w,h,orient,kind)
def put(n,x,y,wh,o='R0',k=''): M[n]=(r(x),r(y),wh[0],wh[1],o,k)
# cells: k=0 W-low,1 W-high,2 E-low,3 E-high ; bank b = 4*seg + k ; fused 2b (with VMQb), 2b+1 (with VMQb_mu1)
cells=[('W',0),('W',1),('E',0),('E',1)]
for k,(side,ri) in enumerate(cells):
    y0=rows[ri]
    for j,(vm,fu) in enumerate([('VM{k}','F{2k}'),('VM{k}_mu1','F{2k1}')]):
        yb=y0+(0 if j==0 else bh+st1)
        if side=='W': put(f'fu{k}_{j}',xW,yb,FU,'MY','fused'); put(f'vm{k}_{j}',xW+FU[0]+gap,yb,VM,'MY','vm')
        else:         put(f'vm{k}_{j}',xE,yb,VM,'R0','vm');   put(f'fu{k}_{j}',xE+VM[0]+gap,yb,FU,'R0','fused')
    fx=(xW if side=='W' else xE+VM[0]+gap)+(FU[0]-TN[0])/2
    put(f'n1_{k}',fx,y0+bh+G,TN,'R0','tnode')
n2y=cellh+G
put('n2L',xW+(FU[0]-TN[0])/2,n2y,TN,'R0','tnode'); put('n2R',xE+VM[0]+gap+(FU[0]-TN[0])/2,n2y,TN,'R0','tnode')
put('n3',xC+(colw-TN[0])/2,n2y,TN,'R0','tnode')
# centre service column: hb_vms in the upper half, small services in the lower half
sv={'hb_vms':dims['hfd_hgi_vms_glue_nw_t'],'xl_ctl':(388.8,388.8),'dbk':dims['ot_hgi_dma_back_static_vp4_banks_cp'],
    'cal':dims['hfd_hgi_vm_calendar_f20'],'smw':dims['ot_hbm_sm_vm_wr_q_t_lanes4'],'vmdel':dims['ot_hbm_svc_vmdel_lane_n'],'keybuf':(324.0,324.0)}
put('hb_vms',xC+(colw-sv['hb_vms'][0])/2,QH-sv['hb_vms'][1],sv['hb_vms'],'R0','svc')
put('xl_ctl',xC,G,sv['xl_ctl'],'R0','svc'); put('smw',xC+388.8+G,G,sv['smw'],'R0','svc')
put('dbk',xC+388.8+G+142.56+G,G,sv['dbk'],'R0','svc'); put('cal',xC+388.8+G+142.56+G,G+240.84+G,sv['cal'],'R0','svc')
for k in range(4): put(f'vmdel{k}',xC+(k%2)*(257.04+G),397.44+G+(k//2)*(108+G),sv['vmdel'],'R0','svc')
put('keybuf',xC+colw-324.0,397.44+G,sv['keybuf'],'R0','svc')
# overlap / containment check
names=list(M); ov=[]
for i,a in enumerate(names):
    xa,ya,wa,ha=M[a][:4]
    assert xa>=-1e-6 and ya>=-1e-6 and xa+wa<=QW+1e-6 and ya+ha<=QH+1e-6,(a,M[a],QW,QH)
    for b in names[i+1:]:
        xb,yb,wb,hb=M[b][:4]
        if xa<xb+wb-1e-6 and xb<xa+wa-1e-6 and ya<yb+hb-1e-6 and yb<ya+ha-1e-6: ov.append((a,b))
def c(n): x,y,w,h=M[n][:4]; return (x+w/2,y+h/2)
def man(a,b): (ax,ay),(bx,by)=c(a),c(b); return r(abs(ax-bx)+abs(ay-by))
legs={}
for k in range(4):
    for j in range(2): legs[f'fu{k}_{j}->n1_{k}']=man(f'fu{k}_{j}',f'n1_{k}')
for k in (0,1): legs[f'n1_{k}->n2L']=man(f'n1_{k}','n2L')
for k in (2,3): legs[f'n1_{k}->n2R']=man(f'n1_{k}','n2R')
legs['n2L->n3']=man('n2L','n3'); legs['n2R->n3']=man('n2R','n3')
svcd={f'vm{k}_0->{s_}':man(f'vm{k}_0',s_) for k in range(4) for s_ in ('hb_vms','xl_ctl','dbk')}
area_hard=sum(v[2]*v[3] for v in M.values())
# hub placement: MU district at the root-facing local E end; q1 flush E, q0 just W of it (segment bound moves to the q0 quad W edge)
HW,HH=C['outline_um']; y0=r((HH-QH)/2/G//1*G)
quads={'q1':(r(HW-QW),y0),'q0':(r(HW-2*QW-s),y0)}
res=dict(quad_um=[r(QW),r(QH)],members={k:dict(xy=[v[0],v[1]],wh=[v[2],v[3]],orient=v[4],kind=v[5]) for k,v in M.items()},
         overlaps=ov,legs_um=legs,legs_max=max(legs.values()),legs_hops405={k:int(-(-v//405)) for k,v in legs.items()},
         vm_to_service_um=svcd,hard_area_mm2=r(area_hard/1e6),fill=r(area_hard/(QW*QH)),hub_um=[HW,HH],quad_origin_local=quads,
         segment_bound_local=quads['q0'][0],
         mapping='cell k: bank Q(4*seg+k) -> vm{k}_0, Q(4*seg+k)_mu1 -> vm{k}_1; fused_(2b) -> fu{k}_0, fused_(2b+1) -> fu{k}_1; n1_q{seg}_k -> n1_{k}; n2L/R_q{seg}, n3_q{seg}; services __q{seg}; vmdel Q(4*seg+k) -> vmdel{k}')
# root legs: n3 of each quad -> root partition centre (die): NW hub die origin x 5140.8, root W edge 13357.44 / width 1684.8
n3x,n3y=c('n3'); rootx_local_from_E=1684.8/2
res['n3_to_hub_E_um']={q:r(HW-(o[0]+n3x)) for q,o in quads.items()}
res['n3_to_root_centre_um']={q:r(HW-(o[0]+n3x)+rootx_local_from_E) for q,o in quads.items()}
json.dump(res,open(out+'/mu_quad.json','w'),indent=1)
print(json.dumps({k:res[k] for k in ('quad_um','overlaps','legs_max','hard_area_mm2','fill','n3_to_hub_E_um','n3_to_root_centre_um','segment_bound_local')}))
print(json.dumps(res['legs_um'])); print(json.dumps(res['vm_to_service_um']))
# render
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
col={'vm':'#5b9bf0','fused':'#f4a6cf','tnode':'#7ee2a0','svc':'#ffe08a'}
fig,ax=plt.subplots(2,1,figsize=(16,15),gridspec_kw=dict(height_ratios=[1.25,1]))
a=ax[0]
for n,(x,y,w,h,o,k) in M.items():
    a.add_patch(Rectangle((x,y),w,h,fc=col[k],ec='k',lw=.6)); a.text(x+w/2,y+h/2,n+('' if o=='R0' else '\n'+o),ha='center',va='center',fontsize=7)
tree=[(f'fu{k}_{j}',f'n1_{k}') for k in range(4) for j in range(2)]+[('n1_0','n2L'),('n1_1','n2L'),('n1_2','n2R'),('n1_3','n2R'),('n2L','n3'),('n2R','n3')]
for p,q in tree:
    (x1,y1),(x2,y2)=c(p),c(q); a.plot([x1,x2,x2],[y1,y1,y2],color='green',lw=1.6)
a.set_xlim(-50,QW+50); a.set_ylim(-50,QH+50); a.set_aspect('equal')
a.set_title(f'ONE replicated VM/FUSED quad tile {QW:.2f} x {QH:.2f} um (x4: NW q0/q1, NE q0/q1 mirrored) | H-tree legs max {res["legs_max"]} um, overlaps {len(ov)}')
b=ax[1]
b.add_patch(Rectangle((0,0),HW,HH,fc='#eef1f5',ec='k')); b.text(HW*0.25,HH*0.5,'rest of hub (SU cores, SM groups, coll, hc_subtree...)\nre-packed by the hub packer around the fixed quads',ha='center',fontsize=9)
for q,(ox,oy) in quads.items():
    b.add_patch(Rectangle((ox,oy),QW,QH,fc='none',ec='m',lw=2,ls='--')); b.text(ox+QW/2,oy+QH+60,f'quad {q}',ha='center',color='m')
    for n,(x,y,w,h,o,k) in M.items(): b.add_patch(Rectangle((ox+x,oy+y),w,h,fc=col[k],ec='k',lw=.3))
    for p,qq in tree:
        (x1,y1),(x2,y2)=c(p),c(qq); b.plot([ox+x1,ox+x2,ox+x2],[oy+y1,oy+y1,oy+y2],color='green',lw=1)
    nx,ny=ox+n3x,oy+n3y; b.annotate('',xy=(HW+400,ny),xytext=(nx,ny),arrowprops=dict(arrowstyle='->',color='r'))
b.add_patch(Rectangle((HW,0),1684.8,HH,fc='#fff2c6',ec='r')); b.text(HW+842,HH*0.2,'root partition\n(central FUSED\nroot 345.6 sq\nat n3 row)',ha='center',fontsize=8)
b.axvline(quads['q0'][0],color='orange',ls=':'); b.text(quads['q0'][0],HH+150,'segment bound (moves to quad q0 W edge)',color='orange',fontsize=8)
b.set_xlim(-100,HW+1800); b.set_ylim(-100,HH+400); b.set_aspect('equal')
b.set_title('NW hub (local, R0) 8216.64 x 4320: MU district at root-facing E end; NE hub = same type layout under die MY')
plt.tight_layout(); plt.savefig(out+'/mu_quad.png',dpi=110)
