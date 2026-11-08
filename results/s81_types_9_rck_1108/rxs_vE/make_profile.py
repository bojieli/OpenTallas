import json
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-rck-1113/work');S=R/'physical/die_plan/s81'
D=R/'results/s81_types_9_rck_1108/rxs_vE';D.mkdir(parents=True,exist_ok=True)
M='ot_s81_rck_rxs';W,H=259.2,216.;pins=[];dirs={}
ports=[('N',[('rst_n',1,'INPUT'),('i_v',1,'INPUT'),('i_d',544,'INPUT'),('i_am',9,'INPUT')]),('S',[('x_q',544,'OUTPUT'),('k_v',4,'OUTPUT'),('k_lo',310,'OUTPUT'),('k_L',5,'OUTPUT'),('k_any',1,'OUTPUT'),('lock',1,'OUTPUT'),('n_relock',32,'OUTPUT')])]
for face,pp in ports:
 ns=[(n if w==1 else f'{n}[{i}]',di) for n,w,di in pp for i in range(w)]
 for j,(n,di) in enumerate(ns):
  x=(54.060 if face=='N' else 20.028)+j*.192
  if face=='N' and x>127.6: x+=4.032
  pins.append(dict(name=n,layer='M5',x=round(x,3),y=.042 if face=='S' else H-.042));dirs[n]=di
pins.append(dict(name='ck',layer='M5',x=129.612,y=H-.042));dirs['ck']='INPUT'
pp='inputs/core_pins/rck_rxs_259x216_1113.json';lp='results/s81_types_9_rck_1108/rxs_vE/ot_s81_rck_rxs.lef'
(S/pp).write_text(json.dumps(dict(module=M,pins=pins),indent=1)+'\n')
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {M}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {H} ;',' SYMMETRY X Y ;']
for p in pins:
 x,y=p['x'],p['y'];n=p['name'];lef += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;',f'  USE {"CLOCK" if n=="ck" else "SIGNAL"} ;','  PORT','   LAYER M5 ;',f'   RECT {x-.012:.3f} {y-.042:.3f} {x+.012:.3f} {y+.042:.3f} ;','  END',f' END {n}']
lef += [f'END {M}','END LIBRARY'];(R/lp).write_text('\n'.join(lef)+'\n')
base=json.loads((S/'die_plan.json').read_text());plan={k:base[k] for k in ['die','clock']}
plan['partition_types']={'serdes__t16':dict(outline_um=[2885.76,1226.88],hard_cores=[dict(inst='u_core.u_dec.u_rxs',module=M,origin_um=[1296.,457.92],outline_um=[W,H],orient='R0',track_offset_um=[.012,.012],pins_file=pp,lef=lp)])}
(D/'plan_draft.json').write_text(json.dumps(plan,indent=1)+'\n')
b='rtl/dsrom_sys/s81_link/'
spec=dict(name=M,top=M,sources=[b+'col/ot_s81_rck_reform.sv',b+'ot_s81_kp4_dsyn.sv',b+'ot_s81_kp4_bm.sv',b+'ot_s81_kp4_common.sv',b+'ot_s81_gf1024.svh',b+'ot_s81_kp4_syn_mat.svh','rtl/common/landed_parent/ot_pl_land.sv'],clock_port='ck',reset_ports=['rst_n'],macros=[],params={},route=dict(pd=.4,threads=8),defines=['OT_S81_RCK_REFORM','OT_S81_RCK_RELAY4','OT_S81_KP4_AM_FACE3','OT_S81_KP4_SYN_LOCAL'])
(D/'spec.json').write_text(json.dumps(spec,indent=1)+'\n');(D/'recipes.json').write_text(json.dumps({M:dict(ref_tile=str(D.relative_to(R)),rtl_dirs=True,util=.4,suffix='vE_tail_sp',orfs_vars=dict(OT_SKIP_PRECTS_METRICS=1))},indent=1)+'\n')
print(D)
