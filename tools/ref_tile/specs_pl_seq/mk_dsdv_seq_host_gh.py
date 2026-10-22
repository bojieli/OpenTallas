# dsdv_seq_host_g (s10g lk 345.6x432) / _h (s10h lk 388.8x453.6) re-packs from _d43: same vertical stack, 43.2 channels
import json,copy,re,collections
WT='/home/ubuntu/wt/s81-seqhp-1021'
def pins(lef):
    txt=open(lef).read(); out=collections.defaultdict(list)
    for m in re.finditer(r'\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1',txt,re.S):
        r=re.search(r'RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)',m.group(2))
        if r:
            x0,y0,x1,y1=map(float,r.groups()); out[re.sub(r'\[.*','',m.group(1))].append(((x0+x1)/2,(y0+y1)/2))
    return out
VC=f'{WT}/physical/ref_tile/dsdv_sh_vc/views/dsdv_sh_vc/dsdv_sh_vc.lef'; vc=pins(VC)
c=json.load(open(f'{WT}/tools/ref_tile/specs_pl_seq/dsdv_seq_host_d43.json'))
S=['vi_s','vo_s','s_hw_e','s_hc_e','s_jd_e','st_rg_e']; Wf=['f_host','f_lf','t_host']
E_=['f_ks','s_hc_w','s_hw_w','s_j','s_jd_w','st_rg_w','t_kd']; N=['cw_v','cw_a','cw_d','vi_n','vo_n','tap_k','sink_k']
def rng(v,axis,off):
    a=[p[axis]+off for p in v]; return [round(min(a)-0.2,2),round(max(a)+0.2,2)]
LKAT=(43.2,43.2); ch=43.2; SQH=151.2; VCH=213.84
for tag,lw,lh in (('g',345.6,432.0),('h',388.8,453.6)):
    name='dsdv_seq_host_'+tag; lkv=f'physical/ref_tile/{name}/standin/dsdv_sh_lk'
    lk=pins(f'{WT}/{lkv}/dsdv_sh_lk.lef')
    Wo=round(LKAT[0]+lw+43.2,2)
    sqy=round(LKAT[1]+lh+ch,2); vcy=round(sqy+SQH+ch,2); vcx=86.4
    Ho=round(vcy+259.2,2)              # same N band as d43 (vc top + 45.36)
    d=copy.deepcopy(c); d['name']=name; d['outline']={'w':Wo,'h':Ho,'exact':True}
    d['children']=[
      {'view':lkv,'count':1,'inst':'*u_l0','at':list(LKAT),'orient':'R0'},
      {'view':'physical/ref_tile/dsdv_sh_sq/views/dsdv_sh_sq','count':1,'inst':'*u_l1','at':[86.4,sqy],'orient':'R0'},
      {'view':'physical/ref_tile/dsdv_sh_vc/views/dsdv_sh_vc','count':1,'inst':'*u_l2','at':[vcx,vcy],'orient':'R0'}]
    pr={}
    for p in S: pr[p]=rng(lk[p],0,LKAT[0])
    for p in Wf: pr[p]=rng(lk[p],1,LKAT[1])
    for p in E_: pr[p]=rng(lk[p],1,LKAT[1])
    for p in N: pr[p]=rng(vc[p],0,vcx)
    yc=round(LKAT[1]+lh+ch/2,2)
    pr['ck']=[round(yc-0.15,2),round(yc+0.15,2)]; pr['rst_n']=[round(yc+2.25,2),round(yc+2.55,2)]
    order=lambda ps:sorted(ps,key=lambda p:pr[p][0])
    d['pins']={'S':order(S),'N':order(N),'W':order(Wf),'E':order(E_+['ck','rst_n'])}
    d['pin_ranges']=pr
    d['structural_change']=(f"S81-SEQHP-1021 re-pack of dsdv_seq_host_c for the RL1 lk successor s10{tag} ({lw}x{lh}, p192 masters, "
      f"claude/s81-shlk-1021 @254543064): vertical stack on the 43.2 lattice, lk DECLARED PIN STAND-IN (43.2,43.2) / sq CLOSED (86.4,{sqy}) / "
      f"vc CLOSED ({vcx},{vcy}); 43.2 channels (lk N face -> sq S face ~1,000 nets; parent M6/M7 over the M5-capped children); "
      f"outline {Wo}x{Ho} = S81 die seqhost slot for s10{tag}. Parent S/W/E pins = lk faces, N pins = vc N face; ck/rst_n on E in the lk|sq channel.")
    d['job']=dict(c['job']); d['job'].update({'owner':'Claude:S81-SEQHP-1021','branch':'claude/s81-seqhp-1021','tag':'shp'+tag,
      'purpose':f'S81-DV {name}: DIAGNOSTIC --cts gate, CLOSED sq+vc views, s10{tag} lk DECLARED PIN STAND-IN (not a view); submit only after s10{tag} lk closes','submit':False,
      'hold_merge':f'diagnostic: lk = s10{tag} DECLARED PIN STAND-IN (s10f --cts timing models re-shaped to the s10{tag} outline / pin plan, not a view); swap in the s10{tag} closed view, regate, then submit_exact'})
    json.dump(d,open(f'{WT}/tools/ref_tile/specs_pl_seq/{name}.json','w'),indent=1)
    print(name,Wo,'x',Ho,'sq',sqy,'vc',vcy,'ck',pr['ck'])
