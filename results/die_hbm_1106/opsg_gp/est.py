#!/usr/bin/env python3
"""DIE-HBM-83-OPSG estimate: cut usage + hauls for group forms. est.py PLAN_DIR"""
import json,sys,re,collections
D=sys.argv[1]; W,H=760.32,233.28
T={'M2':1/.036,'M3':1/.036,'M4':1/.048,'M5':1/.048,'M6':1/.064}; USE=0.6
MW,MH=92.664,43.752
BANK_NETS=88
tops={'group0':'ot_hgi_sfu_opsa_group0__760.32x233.28__d44v_split.json','group1':'ot_hgi_sfu_opsa_group1__760.32x233.28__d44v_split.json','opsb':'ot_hgi_sfu_opsb_group__760.32x233.28__d44v_split.json'}
def form_4x4():  # PART 41 like spacing in 233 tall: uniform columns
    gx=(W-4*MW)/5; gy=(H-4*MH)/5
    return [(gx+c*(MW+gx),gy+r*(MH+gy)) for c in range(4) for r in range(4)]
def form_22(strip=30.24,cg=14.04,my=8.64):
    gy=(H-2*my-4*MH)/3
    xs=[strip,strip+MW+cg,W-strip-2*MW-cg,W-strip-MW]
    return [(x,my+r*(MH+gy)) for x in xs for r in range(4)]
def form_332(strip=21.6,cg=10.8,my=12.96):
    gy=(H-2*my-3*MH)/2
    xs=[strip,strip+MW+cg,strip+2*(MW+cg),W-strip-3*MW-2*cg,W-strip-2*MW-cg,W-strip-MW]
    out=[]
    for i,x in enumerate(xs):
        rows=[0,1,2] if i not in (2,3) else [0,2]
        out+=[(x,my+r*(MH+gy)) for r in rows]
    return out
forms={'4x4_uniform':(form_4x4(),None),'2+2_hub':(form_22(),None),'3+3+2_hub':(form_332(),None)}
for fn,(M,_) in forms.items():
    xs=sorted(x for x,y in M); 
    # hub = widest macro-free x gap
    cols=sorted(set(round(x,3) for x,y in M)); gaps=[(cols[i+1]-(cols[i]+MW),cols[i]+MW,cols[i+1]) for i in range(len(cols)-1)]
    g=max(gaps); h0,h1=g[1],g[2]
    print(f'== {fn}: n={len(M)} columns {cols} hub x {h0:.1f}-{h1:.1f} ({h1-h0:.1f} um, {(h1-h0)*H:.0f} um2) ygaps {sorted(set(round(y,2) for x,y in M))}')
    assert len(M)==16
    for t,f in tops.items():
        L=json.load(open(f'{D}/cores/{f}'))
        pins=[(p['x'],p['y'],p['name']) for p in L if p['name'] not in('clk',)]
        best=None; res=[]
        for cx in [i*10.0 for i in range(1,76)]:
            dem=0
            for x,y,n in pins:
                # pin to nearest hub edge
                tx=min(max(x,h0),h1)
                if min(x,tx)<cx<max(x,tx): dem+=1
            for mx,my in M:
                mc=mx+MW/2; tx=min(max(mc,h0),h1)
                if min(mc,tx)<cx<max(mc,tx): dem+=BANK_NETS
            # capacity at cx: free y for M2/M4 + M6 all
            occ=sum(MH for mx,my in M if mx<=cx<=mx+MW)
            free=H-occ
            cap_lo=free*(T['M2']+T['M4'])*USE; cap_m6=H*T['M6']*USE
            res.append((cx,dem,cap_lo,cap_m6))
        wm5=max(res,key=lambda r:r[1]/max(r[2],1)); wm6=max(res,key=lambda r:r[1]/(r[2]+r[3]))
        # hauls
        hp=max(abs(x-min(max(x,h0),h1))+0 for x,y,n in pins)
        hb=max(abs(mx+MW/2-min(max(mx+MW/2,h0),h1)) for mx,my in M)
        print(f'  {t:7s} worst cut M2-M5: x={wm5[0]:.0f} {wm5[1]} nets / {wm5[2]:.0f} = {wm5[1]/max(wm5[2],1):.2f}; M2-M6: x={wm6[0]:.0f} {wm6[1]} / {wm6[2]+wm6[3]:.0f} = {wm6[1]/(wm6[2]+wm6[3]):.2f}; x-haul pin->hub edge max {hp:.0f}, bank centre->hub edge max {hb:.0f}')
    # macro channel ratio N32 (per vk_chan: pins on channel vs channel tracks), per col gap
    for a,b in zip(cols,cols[1:]+[None]):
        pass
