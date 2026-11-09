import json,sys
IRG=float(sys.argv[1]) if len(sys.argv)>1 else 1.8e6   # irg mapped cells per svc_lo (ESTIMATE)
H=lambda s:(s+8.64)**2                                 # footprint with 4.32 halo
SML,SMD,H4=H(172.8),H(138.24),H(172.8)  # actual11268.96948/6834.84156um2 @0.40, snapped8.64um                 # Codex compact outlines 11-07
GC_CELLS=110e3; GC=H((GC_CELLS*0.118/0.40)**0.5)       # glue core ~110k cells, util 0.40
IRGC_CELLS=140e3; IRGC=H((IRGC_CELLS*0.118/0.40)**0.5)
W,ETA=1408.0,0.85
STRIP={'hi':178.0,'lo':24.6}
MARGIN=25900-25358.4
GLUE={'hi':0.73e6,'lo':0.89e6}; PARENT_MAX=150e3
T_AR=1.2e9/1258.9; TAU=4.159; T_MTP=1.2e9*TAU/3653.8
def tok(dc_ar,dc_mtp): return 1.2e9/(T_AR+dc_ar), 1.2e9*TAU/(T_MTP+dc_mtp)
import math
def need(row,sml,smd,h4,irg_frac=1.0):
    ng=math.ceil((GLUE[row]-PARENT_MAX)/GC_CELLS)
    a=sml*SML+smd*SMD+h4*H4+ng*GC
    nirg=0
    if row=='lo':
        nirg=math.ceil(IRG*irg_frac/IRGC_CELLS); a+=nirg*IRGC
    dy=max(0.0,a/(W*ETA)-STRIP[row]); dy=math.ceil(dy/8.64)*8.64
    return dict(cores=sml+smd+h4+ng+nirg,glue_cores=ng,irg_cores=nirg,area_mm2=round(a/1e6,3),dy=round(dy,2))
opts=[('R0 ruled split, full width (16 SML+8 SMD+16 H4)',16,8,16,1.0,(80,80)),
      ('R1 (B): SM 2:1 (8 SML+4 SMD) + half merges (8 H4)',8,4,8,1.0,None),
      ('R2 (B)+(C): SM of the 4 edge svc into band cells',8,4,8,1.0,None),
      ('R3 (B)+irg SRAM (already macros: no change)',8,4,8,1.0,None),
      ('R4 (B)+irg scorer 2:1 (16 of 32 hslices; NOT in ruling)',8,4,8,0.5,None),
      ('R5 (E) half attention width: 32 hcores + R1 (NOT in ruling)',8,4,8,1.0,None)]
SM_LO,SM_HI=4352,11080; MG_HI=25600; IDX_HI=29453
for name,sml,smd,h4,irgf,_ in opts:
    hi=need('hi',sml,smd,h4); lo=need('lo',sml,smd,h4,irgf)
    if name.startswith('R5'):
        free=32*157.68*259.2/1e6
        for r in (hi,lo):
            r['dy']=max(0.0,math.ceil(((r['area_mm2']-free)*1e6/(W*ETA)-STRIP['hi' if r is hi else 'lo'])/8.64)*8.64) if r['area_mm2']>free else 0.0
    tot=hi['dy']+lo['dy']
    print(name,'| hi',hi,'| lo',lo,'| die dy',round(tot,2),'margin',round(MARGIN,1),'FITS' if tot<=MARGIN else 'NO FIT (+%.0f over)'%(tot-MARGIN))
print('tok basis AR 1258.9 MTP 3653.8; T_AR',round(T_AR),'T_MTP step',round(T_MTP))
for lab,ar,mtp in [('SM 2:1 low',SM_LO,SM_LO),('SM 2:1 high',SM_HI,SM_HI),('half merge high',MG_HI,MG_HI),
                   ('B low',SM_LO,SM_LO),('B high',SM_HI+MG_HI,SM_HI+MG_HI),('H4 +2 pin full width',80,80),
                   ('idx 2:1 high',IDX_HI,29573),('E: attn 2:1 (+1280/layer) + B low',51200+SM_LO,51200+SM_LO)]:
    a,m=tok(ar,mtp); print(f'{lab:36s} AR {a:7.1f} ({(a/1258.9-1)*100:+.2f}%)  MTP {m:7.1f} ({(m/3653.8-1)*100:+.2f}%)')
print('footprints um2 SML',round(SML),'SMD',round(SMD),'H4',round(H4),'GC',round(GC),'IRGC',round(IRGC))
