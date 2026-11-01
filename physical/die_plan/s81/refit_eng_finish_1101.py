#!/usr/bin/env python3
"""Re-site the four unsigned ENG finish children inside unchanged xfin boundaries."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--width',type=float,default=151.2);p.add_argument('--height',type=float,default=164.16);a=p.parse_args()
W,H=a.width,a.height
vd='physical/ref_tile/s81dv_eng_finish/views/ot_s81dv_eng_finish';lf=ROOT/vd/'ot_s81dv_eng_finish.lef'
txt=lf.read_text();pins=[]
for m in re.finditer(r'  PIN (.*?)\n    DIRECTION (INPUT|OUTPUT)',txt):pins.append(m.groups())
assert len(pins)==614
L=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','UNITS','    DATABASE MICRONS 1000 ;','END UNITS','','MACRO ot_s81dv_eng_finish','  FOREIGN ot_s81dv_eng_finish 0 0 ;','  CLASS BLOCK ;',f'  SIZE {W} BY {H} ;']
k0=90;k1=int((W-4.32-.012)/.048);prev=None
for i,(n,d) in enumerate(pins):
 c=round(.012+(k0+round(i*(k1-k0)/613))*.048,4)
 if prev is not None:assert c-prev>=.192-1e-6
 prev=c
 L += [f'  PIN {n}',f'    DIRECTION {d} ;','    USE SIGNAL ;','    PORT','      LAYER M5 ;',f'        RECT {c-.012:.4f} {H-.084:.4f} {c+.012:.4f} {H:.4f} ;','    END',f'  END {n}']
L+=['END ot_s81dv_eng_finish','END LIBRARY',''];lf.write_text('\n'.join(L))
sp=ROOT/'physical/ref_tile/s81dv_eng_finish/spec.json';s=json.loads(sp.read_text());s['structural_change']=f'CODEX 11-01 SLOT-OVERFULL repair: same master/RTL/params and four instances; child {W}x{H}, two-by-two placement inside unchanged 362.88-square ot_s81dv_xfin. Measured std 13700 um2 gives core fill {13700/((W-8.64)*(H-8.64)):.4f}; old 83.16x220.32 was 87%. All 614 N-face M5 pins re-spread, >=0.192 um pitch. No added cycles and no partition/die boundary change.';sp.write_text(json.dumps(s,indent=1)+'\n')
pp=ROOT/'physical/ref_tile/s81dv_xfin/spec.json';parent=json.loads(pp.read_text());xs=[8.64,round(362.88-W-8.64,3)];ys=[8.64,round(H+25.92,3)]
assert ys[1]+H<=358.56
parent['children']=[dict(view=vd,count=1,inst=f'g_cp[{i}].u_e',at=[xs[i%2],ys[i//2]]) for i in range(4)]
parent['outline_note']=s['structural_change'];pp.write_text(json.dumps(parent,indent=1)+'\n')
rp=ROOT/'physical/die_plan/s81/cores/legacy/recipes.json';r=json.loads(rp.read_text());r['ot_s81dv_eng_finish']=dict(child_of='ot_s81dv_xfin',ref_tile='physical/ref_tile/s81dv_eng_finish',lef_contract=vd+'/ot_s81dv_eng_finish.lef',rtl_dirs=True,two_mode=True,suffix='cxfin151',why='Unsigned child slot refit inside unchanged parent; parent remains held until child SIGNED.');rp.write_text(json.dumps(r,indent=1)+'\n')
print(json.dumps(dict(child=[W,H],core_fill=13700/((W-8.64)*(H-8.64)),parent_residual_fill=16094/((362.88-8.64)**2-4*W*H),positions=parent['children']),indent=1))
