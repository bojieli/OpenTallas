import json,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work');S=R/'physical/die_plan/s81'
D=R/'results/s81_rck_11_reform_1108/rxb_pilot';D.mkdir(parents=True,exist_ok=True)
M='ot_s81_rck_rxb';W,H=725.76,280.8;pins=[];dirs={}
# Source-facing input groups over their receiving hard blocks; consumer-facing outputs under the output/SRAM bank.
groups=[('N',244.668,[('x_q',544,'INPUT')]),('N',349.116,[('k_v',4,'INPUT'),('k_lo',310,'INPUT'),('k_L',5,'INPUT'),('k_any',1,'INPUT')]),('N',430.044,[(n,1,'INPUT') for n in ['lpr_syn','lpr_dly','lpr_chn','lpr_out']]),('S',520.044,[('q_d',512,'OUTPUT'),('q_v',1,'OUTPUT'),('q_first',1,'OUTPUT'),('q_unc',1,'OUTPUT'),('q_nerr',5,'OUTPUT'),('q_seq',8,'OUTPUT')]),('S',420.012,[('n_corr',32,'OUTPUT'),('n_unc',32,'OUTPUT')])]
for face,start,pp in groups:
 ns=[(n if w==1 else f'{n}[{i}]',di) for n,w,di in pp for i in range(w)]
 for j,(n,di) in enumerate(ns):
  x=start+j*.192
  if face=='N' and start==349.116 and x>360.8: x+=4.032
  pins.append(dict(name=n,layer='M5',x=round(x,3),y=.042 if face=='S' else H-.042));dirs[n]=di
pins.append(dict(name='ck',layer='M5',x=362.892,y=H-.042));dirs['ck']='INPUT'
pp='inputs/core_pins/rck_rxb_725x280_0222.json';lp='results/s81_rck_11_reform_1108/rxb_pilot/ot_s81_rck_rxb.lef'
(S/pp).write_text(json.dumps(dict(module=M,pins=pins),indent=1)+'\n')
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {M}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {H} ;',' SYMMETRY X Y ;']
for p in pins:
 x,y=p['x'],p['y'];n=p['name'];lef += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;',f'  USE {"CLOCK" if n=="ck" else "SIGNAL"} ;','  PORT','   LAYER M5 ;',f'   RECT {x-.012:.3f} {y-.042:.3f} {x+.012:.3f} {y+.042:.3f} ;','  END',f' END {n}']
lef += [f'END {M}','END LIBRARY'];(R/lp).write_text('\n'.join(lef)+'\n')
base=json.loads((S/'die_plan.json').read_text());plan={k:base[k] for k in ['die','clock']};plan['partition_types']={'serdes__t16':dict(outline_um=[2885.76,1226.88],hard_cores=[dict(inst='u_core.u_dec.u_rxb',module=M,origin_um=[1071.36,155.52],outline_um=[W,H],orient='R0',track_offset_um=[.012,.012],pins_file=pp,lef=lp,obs_max='M6')])};(D/'plan_draft.json').write_text(json.dumps(plan,indent=1)+'\n')
old=Path('/srv/opentallas-scratch2/claude/s81-rck-10/vJ/serdes__t16')
macro_def=[('ot_sram_1r1w2c_64x546_m1',[21.6,43.2]),('ot_s81_kp4_dchn',[220.32,43.2]),('ot_sram_1r1w_32x546_m1',[518.4,43.2])]
mac=[];bbs=[];receipt=[]
for name,at in macro_def:
 md=D/'macros'/name;md.mkdir(parents=True,exist_ok=True)
 for ext in ['.lef','_tt.lib','_ff.lib']:
  src=old/'macros'/(name+ext);shutil.copyfile(src,md/(name+ext));receipt.append(str(src))
 bb=name+'_bb.v'; dest=D/'rtl'/bb;dest.parent.mkdir(exist_ok=True);shutil.copyfile(old/'rtl'/bb,dest);bbs.append(str(dest.relative_to(R)))
 mac.append(dict(inst={'ot_sram_1r1w2c_64x546_m1':'u_dly.u_dmem','ot_s81_kp4_dchn':'u_chn','ot_sram_1r1w_32x546_m1':'u_out.u_cmem'}[name],view=str(md.relative_to(R)),at=at))
b='rtl/dsrom_sys/s81_link/';src=[b+'col/ot_s81_rck_reform.sv',b+'ot_s81_kp4_ddly.sv',b+'ot_s81_kp4_dout.sv',b+'ot_s81_kp4_common.sv',b+'ot_s81_gf1024.svh','rtl/common/landed_parent/ot_pl_land.sv']+bbs
spec=dict(name=M,top=M,sources=src,clock_port='ck',reset_ports=['lpr_syn','lpr_dly','lpr_chn','lpr_out'],macros=mac,params={},route=dict(pd=.4,threads=8,macro_halo_um=5.4),defines=['OT_S81_RCK_REFORM','OT_S81_RCK_RELAY4','OT_S81_KP4_AM_FACE3','OT_S81_KP4_SYN_LOCAL','OT_S81_LPL_CHUNK'])
(D/'spec.json').write_text(json.dumps(spec,indent=1)+'\n');(D/'recipes.json').write_text(json.dumps({M:dict(ref_tile=str(D.relative_to(R)),rtl_dirs=True,util=.4,suffix='vA',route_m6=True)},indent=1)+'\n');(D/'inherited_macro_sources.json').write_text(json.dumps(receipt,indent=1)+'\n');print(D)
