#!/usr/bin/env python3
"""Exact n691 pin-model packing; no RTL/stage/cycle change. Source census on w9 is independent of these coordinates."""
import json
from pathlib import Path
import slice9_kit as g
R=Path(__file__).resolve().parents[2]
g.NAME={'a':'qfd_dv_slice2_w10','b':'qfd_dv_slice2_w10b','e':'qfd_dv_slice2_e10','f':'qfd_dv_slice2_e10b'}[g.V]
g.CELL_Y=[v-129.6 for v in g.CELL_Y]
g.LRLY_Y-=129.6
BASE=3585.6
PACK=json.loads((R/'results/arch/codex_slice2_native_1021/head_pack/n691.json').read_text())
assert PACK['status']=='OPTIMAL' and PACK['independent_matching_bit_max_um']<=405 and PACK['independent_N_boundary_max_um']<=405
ORIENT={0:'R0',1:'MY',2:'MX',3:'R180'}
children_old=g.children

def children():
 kids=children_old()
 for k in kids:
  n=k['inst']
  if n.startswith('u_xh'):
   c=int(n[4:]);q=PACK['placements']['u_xh0']
  elif n.startswith('u_xl'):
   c,lf=map(int,n[4:].split('_'));q=PACK['placements'][f'u_xl0_{lf}']
  else:continue
  k['at']=[round(g.HC_X[c]+q['x'],3),round(BASE+q['y'],3)];k['orient']=ORIENT[q['orientation']]
 return kids

g.children=children
fences_old=g.fences

def fences():
 f=fences_old();f['r_su'][1]=(g.CEN_X0,g.BAND_Y1,g.CEN_X0+g.CEN_W,3542.4)
 f['r_tap']=(864.0,3542.4,1598.4,3585.6)
 for c in range(4):f[f'r_hc{c}']=(g.HC_X[c],BASE,g.HC_X[c]+561.6,g.H-2.16)
 return f

g.fences=fences
for c in range(4):g.CK[f'ck_r_hc{c}']=('N',g.HC_X[c]+278.784)
if __name__=='__main__':g.main()
