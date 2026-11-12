import json,re,collections,math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
p=json.load(open('in/plan_qc99_s28.json')); T=p['partition_types']
R=json.load(open('rects.json')); cur=R['cur']; hand=R['hand']
io=json.load(open('in/die_io.json'))
typ={l.split('\t')[0]:l.split('\t')[1] for l in open('parts.tsv')}
ori={l.split('\t')[0]:l.split('\t')[2] for l in open('parts.tsv')}
CH=json.load(open('lane_chains.json')); CHH=json.load(open('lane_chains_hand.json'))
lat=p['latency']['lanes']
FAMC={'su_l1':'#7fb3d5','su_l0':'#7fb3d5','su_c':'#5499c7','fw':'#f5b041','fe':'#f5b041','stm':'#eb984e','sc':'#e74c3c',
      'st_a':'#58d68d','st_b':'#58d68d','ctl':'#28b463','hc0':'#bb8fce','hc1':'#a569bd','hc2':'#a569bd','hc3':'#bb8fce'}
def fam(n):
    m=re.match(r'sl_[EW]\d_(.+)$',n)
    if m: return m.group(1)
    m=re.match(r'c_[EW]\d_(\w\w)_\d\d$',n)
    if m: return 'cb_'+m.group(1)
    return 'io'
def color(n):
    f=fam(n)
    if f in FAMC: return FAMC[f]
    if f.startswith('cb_'): return {'cb_tf':'#34495e','cb_tn':'#2e4053','cb_bn':'#2e4053','cb_bf':'#34495e'}[f]
    return '#7f8c8d'
# ---------- (a) data-flow diagram (one slice + its cb neighbours + ring neighbours) ----------
def dataflow():
    E=collections.defaultdict(lambda:[0,[]])
    for lid,ch,w in CH:
        if not any(re.match(r'(sl|c)_E0_',n) for n in (ch[0],ch[-1])): continue
        def lab(n):
            if n.startswith('sl_E0_'): return n[6:]
            if n.startswith('c_E0_'): return n[5:]
            m=re.match(r'sl_([EW]\d)_(fw|fe)$',n)
            if m: return ('fw(E1)' if m.group(2)=='fw' else 'fe(W0)')
            return None
        a,b=lab(ch[0]),lab(ch[-1])
        if not a or not b or a==b: continue
        L=lat.get(lid,{}); E[(a,b)][0]+=w; E[(a,b)][1].append(L.get('cycles'))
    pos={'tf_01':(0,13.5),'tf_11':(4,13.5),'tf_00':(0,12),'tf_10':(4,12),'tn_01':(0,10.5),'tn_11':(4,10.5),'tn_00':(0,9),'tn_10':(4,9),
         'hc0':(-1,7.2),'hc1':(1,7.2),'hc2':(3,7.2),'hc3':(5,7.2),
         'st_a':(-1,5.4),'ctl':(2,5.4),'st_b':(5,5.4),
         'fw':(-1,3.6),'stm':(1,3.6),'sc':(3,3.6),'fe':(5,3.6),'fe(W0)':(-3.2,3.6),'fw(E1)':(7.2,3.6),
         'su_l1':(-1,1.8),'su_c':(2,1.8),'su_l0':(5,1.8),
         'bn_00':(0,0),'bn_10':(4,0),'bn_01':(0,-1.5),'bn_11':(4,-1.5),'bf_00':(0,-3),'bf_10':(4,-3),'bf_01':(0,-4.5),'bf_11':(4,-4.5)}
    fig,ax=plt.subplots(figsize=(17,19)); ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')
    und=collections.defaultdict(lambda:[0,0,[],[]])
    for (a,b),(w,c) in E.items():
        if a not in pos or b not in pos: continue
        k=tuple(sorted((a,b))); fwd=(a==k[0])
        und[k][0 if fwd else 1]+=w; und[k][2 if fwd else 3]+= [x for x in c if x is not None]
    mx=max(v[0]+v[1] for v in und.values())
    for (a,b),(w1,w2,c1,c2) in sorted(und.items(),key=lambda kv:kv[1][0]+kv[1][1]):
        tot=w1+w2
        if tot<90: continue
        (x1,y1),(x2,y2)=pos[a],pos[b]
        lw=0.6+9*tot/mx
        col='#f39c12' if tot>=3000 else ('#f7dc6f' if tot>=1500 else '#85929e')
        rad=0.18 if abs(y1-y2)<0.1 and abs(x1-x2)>2.5 else (0.12 if abs(x1-x2)>0.1 and abs(y1-y2)>0.1 else 0)
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),connectionstyle=f'arc3,rad={rad}',arrowstyle='-',lw=lw,color=col,alpha=0.75,zorder=1))
        def cy(c): return '' if not c else (f'{min(c)}' if min(c)==max(c) else f'{min(c)}-{max(c)}')
        txt=[]
        if w1: txt.append(f'{a}>{b} {w1}b [{cy(c1)}c]')
        if w2: txt.append(f'{b}>{a} {w2}b [{cy(c2)}c]')
        mxp=(x1+x2)/2+(rad*(y2-y1)*-0.5); myp=(y1+y2)/2+(rad*(x2-x1)*0.5)
        if tot>=500: ax.text(mxp,myp,'\n'.join(txt),fontsize=6.3,color='white',ha='center',va='center',zorder=5,
                bbox=dict(boxstyle='round,pad=0.15',fc='#1c2833',ec='none',alpha=0.85))
    for n,(x,y) in pos.items():
        f=n.split('(')[0]; c=FAMC.get(f, '#34495e' if n[:2] in ('tf','tn','bn','bf') else '#7f8c8d')
        ax.add_patch(Rectangle((x-0.62,y-0.32),1.24,0.64,fc=c,ec='white',lw=1,zorder=3))
        ax.text(x,y,n,ha='center',va='center',fontsize=10,fontweight='bold',color='black' if n[:2] not in ('tf','tn','bn','bf') else 'white',zorder=9,bbox=dict(fc=c,ec='none',pad=0.1))
    ax.set_xlim(-4.2,8.2); ax.set_ylim(-5.3,14.4); ax.axis('off')
    ax.set_title('QC die data flow, one column (slice E0 + its cb rows); all 12 columns identical (W mirror). plan_qc99_s28 2f0c17d5f1a3\n'
                 'edge = lanes summed per direction, b = bits, [c] = declared lane cycles (latency table). width ~ bits; orange >= 3000 b, yellow >= 1500 b.\n'
                 'fe(W0)/fw(E1) = the E-W slice ring: fe(k) <-> fw(k+1) abut at the column seam. cb rows = 4x4 A0 tile ring (tf/tn above, bn/bf below)',
                 color='white',fontsize=11,loc='left')
    fig.savefig('out/qc_dataflow_column.png',dpi=110,facecolor=fig.get_facecolor(),bbox_inches='tight')
    fig.savefig('out/qc_dataflow_column.svg',facecolor=fig.get_facecolor(),bbox_inches='tight'); plt.close(fig)
# ---------- (b) hand floorplan: one column, current vs hand ----------
def tap_xy(n,rects):
    t=T[typ[n]]; tp=(t.get('clock') or {}).get('tap_um')
    if not tp: return None
    W,H=t['outline_um']; r=rects[n]
    x,y=tp
    if ori[n]=='MX': y=H-y
    if ori[n]=='MY': x=W-x
    sx=(r[2]-r[0])/W; sy=(r[3]-r[1])/H
    return r[0]+x*sx, r[1]+y*sy
def seam_bits(rects,chains):
    S=collections.Counter()
    for lid,ch,w in chains:
        for a,b in zip(ch,ch[1:]): S[tuple(sorted((a,b)))]+=w
    out=[]
    for (a,b),w in S.items():
        A,B=rects[a],rects[b]
        if abs(A[2]-B[0])<0.5 or abs(B[2]-A[0])<0.5:
            L=min(A[3],B[3])-max(A[1],B[1]); x=A[2] if abs(A[2]-B[0])<0.5 else A[0]
            if L>0: out.append(('V',x,max(A[1],B[1]),L,w,a,b))
        elif abs(A[3]-B[1])<0.5 or abs(B[3]-A[1])<0.5:
            L=min(A[2],B[2])-max(A[0],B[0]); y=A[3] if abs(A[3]-B[1])<0.5 else A[1]
            if L>0: out.append(('H',y,max(A[0],B[0]),L,w,a,b))
    return out
def column(ax,rects,chains,title,col='E0',X0=None,Y=(7300,15900)):
    names=[n for n in rects if re.match(rf'(sl|c)_{col}_',n)]
    xs=[rects[n][0] for n in names]; X0=min(xs); X1=max(rects[n][2] for n in names)
    for n in names:
        r=rects[n]
        if r[3]<Y[0] or r[1]>Y[1]: continue
        ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=color(n),ec='white',lw=1.2,alpha=0.9))
        t=T[typ[n]]; W,H=t['outline_um']; w=r[2]-r[0]; h=r[3]-r[1]
        lab=n.split('_',2)[2]
        ax.text((r[0]+r[2])/2,(r[1]+r[3])/2+min(h*0.18,160),f'{lab}\n{w:.0f}x{h:.0f}',ha='center',va='center',fontsize=8,fontweight='bold')
        # hard cores at the current place scaled (shape frozen: draw at true size, anchored by fraction)
        for c in t.get('hard_cores',[]):
            cx,cy=c['origin_um']; cw,chh=c['outline_um']
            if ori[n]=='MX': cy=H-cy-chh
            fx=cx/W*(w-cw)/(max(W-cw,1)) if W>cw else 0
            ax.add_patch(Rectangle((r[0]+min(cx,w-cw),r[1]+min(cy*(h/H) if h<H else cy,h-chh)),cw,chh,fc='#1b2631',ec='#d5d8dc',lw=0.4,alpha=0.85))
        tp=tap_xy(n,rects)
        if tp: ax.plot(*tp,marker='+',color='cyan',ms=7,mew=1.5,zorder=6)
    # seams: bits crossing / pin cap (12 pins/um)
    for o,a,b0,L,w,pa,pb in seam_bits(rects,chains):
        if not (re.match(rf'(sl|c)_{col}_',pa) or re.match(rf'(sl|c)_{col}_',pb)): continue
        if w<300: continue
        r=w/(L*12); c='#e74c3c' if r>0.6 else ('#f4d03f' if r>0.4 else '#ecf0f1')
        if o=='V':
            if b0>Y[1] or b0+L<Y[0]: continue
            ax.plot([a,a],[b0,b0+L],color=c,lw=1+5*min(r,1)); ax.text(a,b0+L*0.5,f'{w}b\n{r:.2f}',fontsize=6.5,color='black',ha='center',va='center',rotation=90,bbox=dict(fc=c,ec='none',pad=0.5,alpha=0.9),zorder=7)
        else:
            if a>Y[1] or a<Y[0]: continue
            ax.plot([b0,b0+L],[a,a],color=c,lw=1+5*min(r,1)); ax.text(b0+L*0.5,a,f'{w}b {r:.2f}',fontsize=6.5,color='black',ha='center',va='center',bbox=dict(fc=c,ec='none',pad=0.5,alpha=0.9),zorder=7)
    # clock trunk: column trunk at the column centre from the die H-tree (schematic), taps
    xc=(X0+X1)/2
    ax.plot([xc,xc],[Y[0],Y[1]],color='cyan',lw=2,ls='--',alpha=0.7)
    ax.text(xc+20,Y[1]-120,'die clock H-tree branch (M8/M9, schematic)\n+ = type clock tap_um',color='cyan',fontsize=7)
    ax.set_xlim(X0-400,X1+400); ax.set_ylim(*Y); ax.set_aspect('equal'); ax.set_facecolor('#0d1117')
    ax.tick_params(colors='white',labelsize=7); ax.set_title(title,color='white',fontsize=10,loc='left')
def column_fig():
    fig,axs=plt.subplots(1,2,figsize=(22,16)); fig.patch.set_facecolor('#0d1117')
    column(axs[0],cur,CH,'CURRENT s28 slots, column E0 (bn_00 row .. tn_00 row)\nseam label = lane bits crossing / (len x 12 pins/um)')
    column(axs[1],hand,CHH,'HAND FLOORPLAN HF-1b, column E0 (same for all 12 columns, W mirror)\nsu 1399.7 / mid 1831.7 / st 1339.2 / hc 717.1 tall, sc 656.6 / fe 578.9 wide, cbn_q00 rows +34.56; R1+R2 re-routes')
    fig.savefig('out/qc_floorplan_column_cur_vs_hand.png',dpi=100,facecolor=fig.get_facecolor(),bbox_inches='tight')
    fig.savefig('out/qc_floorplan_column_cur_vs_hand.svg',facecolor=fig.get_facecolor(),bbox_inches='tight'); plt.close(fig)
def die_fig():
    fig,axs=plt.subplots(1,2,figsize=(26,11.5)); fig.patch.set_facecolor('#0d1117')
    DW,DH=p['die']['outline_um']
    for ax,rects,title in ((axs[0],cur,'CURRENT s28 die (31.2 x 25.6 mm)'),(axs[1],hand,'HAND FLOORPLAN HF-1b die (outline unchanged; changed slots outlined red)')):
        for n,r in rects.items():
            ch = (r!=cur[n])
            ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=color(n),ec='#e74c3c' if (ch and rects is hand) else '#17202a',lw=1.4 if ch and rects is hand else 0.3))
        for m in io:
            x0,y0,x1,y1=m['rect_um']; ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='none',ec='#f1c40f',hatch='///',lw=1.2))
            ax.text((x0+x1)/2,(y0+y1)/2,m['part']+'\nFIXED seam',fontsize=6,color='#f1c40f',ha='center',va='center',rotation=90)
        for c in p['die'].get('channels',[]):
            x0,y0,x1,y1=c['rect_um']; ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='none',ec='#566573',hatch='..',lw=0.5))
        rx,ry=p['clock']['spine']['root_um']; ax.plot(rx,ry,marker='*',color='cyan',ms=16)
        # schematic H-tree: root -> horizontal trunk at y root -> 12 column branches
        cols=sorted({(rects[f'sl_{c}_fw'][0]+rects[f'sl_{c}_fe'][2])/2 for c in [f'{s}{i}' for s in 'EW' for i in range(6)]})
        ax.plot([cols[0],cols[-1]],[ry,ry],color='cyan',lw=1.5,ls='--'); [ax.plot([x,x],[1300,DH-1300],color='cyan',lw=0.8,ls=':') for x in cols]
        ax.set_xlim(-200,DW+200); ax.set_ylim(-200,DH+200); ax.set_aspect('equal'); ax.set_facecolor('#0d1117')
        ax.tick_params(colors='white',labelsize=7); ax.set_title(title,color='white',fontsize=11,loc='left')
    fig.savefig('out/qc_floorplan_die_cur_vs_hand.png',dpi=90,facecolor=fig.get_facecolor(),bbox_inches='tight'); plt.close(fig)
import os; os.makedirs('out',exist_ok=True)
dataflow(); column_fig(); die_fig(); print('ok')
