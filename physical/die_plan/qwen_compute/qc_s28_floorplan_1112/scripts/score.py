# first-order die-level channel model: current s28 slot rects vs hand floorplan HF-1
import json,re,collections,copy,sys
p=json.load(open('in/plan_qc99_s28.json'))
T=p['partition_types']; lat=p['latency']['lanes']
C=json.load(open('lane_chains.json'))
cur={}; typ={}
for line in open('parts.tsv'):
    n,t,o,x0,y0,x1,y1=line.rstrip('\n').split('\t'); cur[n]=[float(x0),float(y0),float(x1),float(y1)]; typ[n]=t
# --- hand floorplan HF-1 (slice band only; everything else unchanged)
DY=34.56  # cbn_q00 row +34.56 (QC-S28-B gap) on bn_00/bn_10 and tn_00/tn_10 rows, absorbed inside the slice band
SU=(10143.36+DY,11482.56+DY); MID=(11482.56+DY,13314.24+DY); CTL=(13314.24+DY,14653.44+DY); HC=(14653.44+DY,15431.04+DY)
MIDW=[('fw',622.08),('stm',613.44),('sc',656.64),('fe',578.88)]
def hand_rects():
    h=copy.deepcopy(cur)
    cols=sorted(set(re.match(r'sl_([EW]\d)_',n).group(1) for n in cur if n.startswith('sl_')))
    for c in cols:
        X0=cur[f'sl_{c}_fw'][0]
        x=X0
        for f,w in MIDW: h[f'sl_{c}_{f}']=[x,MID[0],x+w,MID[1]]; x+=w
        for f in ('su_l1','su_c','su_l0'):
            r=cur[f'sl_{c}_{f}']; h[f'sl_{c}_{f}']=[r[0],SU[0],r[2],SU[1]]
        for f in ('st_a','ctl','st_b'):
            r=cur[f'sl_{c}_{f}']; h[f'sl_{c}_{f}']=[r[0],CTL[0],r[2],CTL[1]]
        for f in ('hc0','hc1','hc2','hc3'):
            r=cur[f'sl_{c}_{f}']; h[f'sl_{c}_{f}']=[r[0],HC[0],r[2],HC[1]]
    for n in cur:
        m=re.match(r'c_[EW]\d_(bn_00|bn_10)$',n)
        if m: r=cur[n]; h[n]=[r[0],r[1],r[2],r[3]+DY]
        m=re.match(r'c_[EW]\d_(tn_00|tn_10)$',n)
        if m: r=cur[n]; h[n]=[r[0],r[1]-DY,r[2],r[3]]
    return h
hand=hand_rects()
RER={ # R1/R2/R3 lane re-routes (plan ft chain), slice-relative family chains
 'x_fw_ctl_p1':['fw','stm','ctl'],
 'x_fw_ctl_p2':['fw','stm','ctl'],
 'x_su_l1_ctl':['su_l1','su_c','stm','ctl'],
}
def reroute(chains):
    out=[]
    for lid,ch,w in chains:
        m=re.match(r'sl_([EW]\d)_[a-z0-9_]+?__(.+)$',lid)
        if m and m.group(2) in RER and all(n.startswith('sl_'+m.group(1)) for n in ch):
            ch=[f'sl_{m.group(1)}_{f}' for f in RER[m.group(2)]]
        out.append((lid,ch,w))
    return out
# capacity model (route_supply pitches/derates; ft_track_frac 0.5; over a hard core only M6 H / M7 V, halved)
PITCH={"M2":0.0419,"M3":0.0371,"M4":0.048,"M5":0.0503,"M6":0.074,"M7":0.0681}
DER={"M2":0.2914,"M3":0.2573,"M4":0.2568,"M5":0.2599,"M6":0.3118,"M7":0.3239}
tpu=lambda L:(1/PITCH[L])*(1-DER[L])
H_ST=sum(tpu(L) for L in ('M2','M4','M6')); V_ST=sum(tpu(L) for L in ('M3','M5','M7'))
H_CO=tpu('M6')*0.5; V_CO=tpu('M7')*0.5
FT=0.5
def core_span(n):
    t=T[typ[n]]; hc=t.get('hard_cores',[])
    # cores blocking: sum of max widths per y-band approx -> use union-ish: total core w over height fraction
    if not hc: return 0.0,0.0
    W,H=t['outline_um']; A=sum(c['outline_um'][0]*c['outline_um'][1] for c in hc)
    return A/H, A/W   # equivalent blocked width (for V cut), blocked height (for H cut)
def cap(n,r):
    w=r[2]-r[0]; h=r[3]-r[1]
    bw,bh=core_span(n)  # unchanged by reslot (core-shape freeze)
    capV=((w-min(bw,w*0.9))*V_ST+min(bw,w*0.9)*V_CO)*FT
    capH=((h-min(bh,h*0.9))*H_ST+min(bh,h*0.9)*H_CO)*FT
    return capH,capV
def side(a,b,R):
    A=R[a];B=R[b];e=0.5
    if abs(A[2]-B[0])<e: return 'E'
    if abs(A[0]-B[2])<e: return 'W'
    if abs(A[3]-B[1])<e: return 'N'
    if abs(A[1]-B[3])<e: return 'S'
    return None
def run(R,chains,tag):
    thruH=collections.Counter(); thruV=collections.Counter(); bad=0; bm=0.0
    for lid,ch,w in chains:
        for i in range(len(ch)-1):
            a,b=R[ch[i]],R[ch[i+1]]
            bm+=w*(abs((a[0]+a[2])/2-(b[0]+b[2])/2)+abs((a[1]+a[3])/2-(b[1]+b[3])/2))/1000
        for i in range(1,len(ch)-1):
            s_in=side(ch[i],ch[i-1],R); s_out=side(ch[i],ch[i+1],R)
            if s_in is None or s_out is None: bad+=1; continue
            hz=lambda s:s in 'EW'
            if hz(s_in) and hz(s_out): thruH[ch[i]]+=w
            elif not hz(s_in) and not hz(s_out): thruV[ch[i]]+=w
            else: thruH[ch[i]]+=w/2; thruV[ch[i]]+=w/2
    rows={}
    for n in R:
        if not n.startswith('sl_'): continue
        cH,cV=cap(n,R[n]); rows[n]=(thruH[n],cH,thruH[n]/cH,thruV[n],cV,thruV[n]/cV)
    return rows,bad,bm
base=run(cur,C,'cur'); hf=run(hand,reroute(C),'hand'); hf0=run(hand,C,'hand_noreroute'); rr=run(cur,reroute(C),'cur_reroute')
print('non-adjacent hops: cur %d hand %d'%(base[1],hf[1]))
print('bit-mm total (all lanes, centre-centre per hop): cur %.0f  hand+R %.0f  hand-only %.0f  cur+R %.0f'%(base[2],hf[2],hf0[2],rr[2]))
fams=['su_l1','su_c','su_l0','fw','stm','sc','fe','st_a','ctl','st_b','hc0','hc1','hc2','hc3']
out=open('channel_score.tsv','w')
out.write('family\tcur_thruH\tcur_capH\tcur_H\tcur_thruV\tcur_capV\tcur_V\thand_thruH\thand_capH\thand_H\thand_thruV\thand_capV\thand_V\tcurR_H\tcurR_V\thandnoR_H\thandnoR_V\n')
print('%-6s | %18s | %18s | %11s | %11s'%('fam','cur H/V ratio','hand+R H/V','cur+R only','hand only'))
for f in fams:
    agg=lambda res:max((res[0][n] for n in res[0] if n.endswith('_'+f) and re.match(r'sl_[EW]\d_'+f+'$',n)),key=lambda r:max(r[2],r[5]))
    a=agg(base);b=agg(hf);c=agg(rr);d=agg(hf0)
    print('%-6s | %5.0f/%4.2f %5.0f/%4.2f | %5.0f/%4.2f %5.0f/%4.2f | %4.2f %4.2f | %4.2f %4.2f'%(f,a[0],a[2],a[3],a[5],b[0],b[2],b[3],b[5],c[2],c[5],d[2],d[5]))
    out.write('\t'.join([f]+['%.0f'%a[0],'%.0f'%a[1],'%.3f'%a[2],'%.0f'%a[3],'%.0f'%a[4],'%.3f'%a[5],'%.0f'%b[0],'%.0f'%b[1],'%.3f'%b[2],'%.0f'%b[3],'%.0f'%b[4],'%.3f'%b[5],'%.3f'%c[2],'%.3f'%c[5],'%.3f'%d[2],'%.3f'%d[5]])+'\n')
json.dump({'hand':hand,'cur':cur},open('rects.json','w'))
json.dump([(l,c,w) for l,c,w in reroute(C)],open('lane_chains_hand.json','w'))
