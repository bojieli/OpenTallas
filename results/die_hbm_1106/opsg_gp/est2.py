import json,sys
D=sys.argv[1]; W,H=760.32,233.28; T={'M2':1/.036,'M3':1/.036,'M4':1/.048,'M5':1/.048,'M6':1/.064}; USE=0.6; MW,MH=92.664,43.752; BN=88
tops={'group0':'ot_hgi_sfu_opsa_group0__760.32x233.28__d44v_split.json','group1':'ot_hgi_sfu_opsa_group1__760.32x233.28__d44v_split.json','opsb':'ot_hgi_sfu_opsb_group__760.32x233.28__d44v_split.json'}
def col(xs,my=8.64):
    gy=(H-2*my-4*MH)/3; return [(x,my+r*(MH+gy)) for x in xs for r in range(4)]
F={'A 2+2 hub (cg19.44 strip30.24)':(col([30.24,142.344,W-30.24-2*MW-19.44,W-30.24-MW])),
   'B 4+0 W, hub E (cg19.44 strip13.8)':(col([13.824,125.928,238.032,350.136])),
   'C 3+1 hub (strip21.6)':(col([21.6,133.704,245.808,W-30.24-MW]))}
for fn,M in F.items():
    cols=sorted(set(round(x,3) for x,y in M)); ext=[(cols[0],0,cols[0])]+[(cols[i+1]-cols[i]-MW,cols[i]+MW,cols[i+1]) for i in range(len(cols)-1)]+[(W-cols[-1]-MW,cols[-1]+MW,W)]
    g=max(ext); h0,h1=g[1],g[2]
    print('==',fn,'cols',cols,f'hub {h0:.1f}-{h1:.1f} = {h1-h0:.1f} um {(h1-h0)*H:.0f} um2; col gaps',[round(e[0],1) for e in ext])
    for t,f in tops.items():
        L=json.load(open(f'{D}/cores/{f}')); P=[(p['x'],p['y']) for p in L if p['name']!='clk']
        R=[]
        for cx in [5.0*i for i in range(1,152)]:
            d=sum(1 for x,y in P if min(x,min(max(x,h0),h1))<cx<max(x,min(max(x,h0),h1)))
            d+=sum(BN for mx,my in M if min(mx+MW/2,min(max(mx+MW/2,h0),h1))<cx<max(mx+MW/2,min(max(mx+MW/2,h0),h1)))
            occ=sum(MH for mx,my in M if mx<=cx<=mx+MW); fr=H-occ
            R.append((cx,d,fr*(T['M2']+T['M4'])*USE,H*T['M6']*USE))
        a=max(R,key=lambda r:r[1]/max(r[2],1)); b=max(R,key=lambda r:r[1]/(r[2]+r[3]))
        hp=max(abs(x-min(max(x,h0),h1))+abs(y-H/2) for x,y in P); hb=max(abs(mx+MW/2-min(max(mx+MW/2,h0),h1))+abs(my+MH/2-H/2) for mx,my in M)
        print(f'  {t:7s} M2-M5 x={a[0]:.0f} {a[1]}/{a[2]:.0f}={a[1]/a[2]:.2f}; M2-M6 x={b[0]:.0f} {b[1]}/{b[2]+b[3]:.0f}={b[1]/(b[2]+b[3]):.2f}; manh. pin->hub max {hp:.0f}, bank->hub max {hb:.0f}')
    # macro channel ratio (HBM-CONS-2 method): 45 pins per W/E face x 4 rows
    print('  N32 channel ratio (vk_chan method): ', {f'{e[1]:.0f}-{e[2]:.0f}': round((360 if 0<e[1] and e[2]<W else 180)/(e[0]*48.6*USE),2) for e in ext})
