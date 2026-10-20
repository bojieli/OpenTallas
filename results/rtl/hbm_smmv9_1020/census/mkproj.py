# input: results/rtl/hbm_rate7_1020/census/m_all.json (claude/hbm-rate7-1020, md5 b1aa6ab2a2b4792acefee8c5e2d713bb = RATE8 cen/m_all.json), saved as /tmp/smmv9_mall.json
import json,re,copy,sys
src=json.load(open('/tmp/smmv9_mall.json'))
sm=src['designs']['ds_ar']['SM.MATVEC']['shapes']
def info(s,v):
    m=re.search(r'rows/SM (\d+) blocks (\d+) lines (\d+)',v['notes']); r,b,L=map(int,m.groups())
    k=json.loads(s); fmt=k['B'][3]; K,M=k['B'][1],k['B'][2]
    pair = (M==24)            # w1/w3 measured as one w1+w3 record
    return r,b,L,fmt,pair,K,M
XF={'FP4E2M1':(88,3),'FP8E4M3':(84,2),'BF16':(81,1)}
def pace(L,b): return L*80/64+8*b
rows=[]
V={k:copy.deepcopy(src) for k in ('p_floor','p_fetch','p_fetch_xlr','p_fix')}
for s,v in sm.items():
    if v.get('cycles') is None: continue
    r,b,L,fmt,pair,K,M=info(s,v); d=2 if pair else 1
    routed = fmt=='FP4E2M1'
    fp={('FP4E2M1',24):24,('FP4E2M1',53):16,('FP8E4M3',24):40,('FP8E4M3',13):40,('FP8E4M3',5):40,('FP8E4M3',512):16,
        ('BF16',1024):8,('FP8E4M3',53):(64 if K==8192 else 24),('BF16',4):80,('FP8E4M3',42):16,('BF16',10):80,('FP8E4M3',266):48,('BF16',5):80}.get((fmt,M),40)
    F,cad=XF[fmt]; xser=F+2*fp*cad+16; xthr=2*fp*cad
    floor=L*136/99/d
    rec_fetch=max(pace(L,b), xser, v['cycles']*d if not routed else 0)   # routed: FETCH law gone; x still serial
    if not routed: rec_fetch=v['cycles']*d
    rec_xlr = (pace(L,b)) if (routed and pair) else rec_fetch                # x reused across routed w1+w3
    if routed and pair: rec_xlr=(5*pace(L,b)+max(pace(L,b),xser))/6
    rec_fix = max(pace(L,b), xthr)
    if routed and pair: rec_fix=(5*pace(L,b)+max(pace(L,b),xthr))/6
    out={'p_floor':floor,'p_fetch':rec_fetch/d,'p_fetch_xlr':rec_xlr/d,'p_fix':rec_fix/d}
    for k,c in out.items():
        V[k]['designs']['ds_ar']['SM.MATVEC']['shapes'][s]['cycles']=round(min(c,v['cycles']),1)
    rows.append((s[:60],v['cycles'],round(floor,1),{k:round(min(c,v['cycles']),1) for k,c in out.items()}))
for k,j in V.items():
    j['designs']['ds_ar']['SM.MATVEC']['grade']='PROJECTION (HBM-SMMV9, not measured)'
    json.dump(j,open(f'{k}.json','w'),indent=1)
for r in rows: print(r)
