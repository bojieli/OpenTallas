import json
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work')
D=R/'results/s81_rck_11_reform_1108/tx_pilot';D.mkdir(parents=True,exist_ok=True)
S=R/'physical/die_plan/s81'; P=S/'inputs/core_pins';P.mkdir(parents=True,exist_ok=True)
M='ot_s81_rck_tx'; W,H=181.44,155.52
pins=[];dirs={}
for face,ports in [('E',[('rst_n',1,'INPUT'),('tx_v',1,'INPUT'),('tx_d',512,'INPUT')]),('W',[('p_v',1,'OUTPUT'),('p_d',544,'OUTPUT'),('fault',1,'OUTPUT')])]:
    ns=[(n if w==1 else f'{n}[{i}]',di) for n,w,di in ports for i in range(w)]
    for j,(n,di) in enumerate(ns):
        pins.append(dict(name=n,layer='M4',x=.042 if face=='W' else W-.042,y=round(24.060+j*.192,3)))
        dirs[n]=di
pins.append(dict(name='clk',layer='M5',x=90.732,y=H-.042));dirs['clk']='INPUT'
pp='inputs/core_pins/rck_tx_181x155_0222.json'; lp='results/s81_rck_11_reform_1108/tx_pilot/ot_s81_rck_tx.lef'
(P/'rck_tx_181x155_0222.json').write_text(json.dumps(dict(module=M,pins=pins),indent=1)+'\n')
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {M}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {H} ;',' SYMMETRY X Y ;']
for p in pins:
    x,y=p['x'],p['y'];n=p['name'];dx,dy=(.012,.042) if p['layer']=='M5' else (.042,.012);lef += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;',f'  USE {"CLOCK" if n=="clk" else "SIGNAL"} ;','  PORT',f'   LAYER {p["layer"]} ;',f'   RECT {x-dx:.3f} {y-dy:.3f} {x+dx:.3f} {y+dy:.3f} ;','  END',f' END {n}']
lef += [f'END {M}','END LIBRARY'];(R/lp).write_text('\n'.join(lef)+'\n')
base=json.loads((S/'die_plan.json').read_text())
core=dict(inst='u_core.u_tx_pin',module=M,origin_um=[2574.72,466.56],outline_um=[W,H],orient='R0',pins_file=pp,lef=lp)
plan={k:base[k] for k in ['die','clock']};plan['partition_types']={'serdes__t16':dict(outline_um=[2885.76,1226.88],hard_cores=[core])}
(D/'plan_draft.json').write_text(json.dumps(plan,indent=1)+'\n')
b='rtl/dsrom_sys/s81_link/'
spec=dict(name=M,top=M,sources=[b+'col/ot_s81_rck_reform.sv',b+'ot_s81_kp4_enc.sv',b+'ot_s81_kp4_common.sv',b+'ot_s81_gf1024.svh',b+'ot_s81_kp4_enc_mat.svh'],clock_port='clk',reset_ports=['rst_n'],macros=[],params={},route=dict(pd=.4,threads=8),defines=['OT_S81_RCK_REFORM','OT_S81_RCK_RELAY4','OT_S81_KP4_AM_FACE3','OT_S81_KP4_SYN_LOCAL'])
(D/'spec.json').write_text(json.dumps(spec,indent=1)+'\n')
recipes={M:dict(ref_tile=str(D.relative_to(R)),rtl_dirs=True,util=.4,suffix='vA',clock_pin_um=[W/2,H/2])}
(D/'recipes.json').write_text(json.dumps(recipes,indent=1)+'\n')
print(D)
