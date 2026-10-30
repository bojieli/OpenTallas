import json,sys
from pathlib import Path
from layer_prog.emitted_control_routes import ControlView
from layer_prog.bound_control import BoundControl
v=ControlView(sys.argv[1],sys.argv[2]);rows=[]
for sl,row in v.die.rows.items():
 xf=v.atomic(row['part'],r'ot_s81dv_xfin');params={k:BoundControl._integer(n)for k,n in xf['params'].items()}
 assert params==dict(LA=6,LM=5,NS=16,NVL=5,SIW=7)
 v.units[sl+'.xf']=xf;fields={}
 for src,sport,dst,dport,n in [('xr','x_go','xf','go',1),('xr','x_eps','xf','eps',32),('xr','x_mode','xf','mode',1),('xr','x_sv','xf','s_v',1),('xr','x_si','xf','s_i',7),('xr','x_s','xf','s',32),('xf','rb_v','xr','x_rbv',1),('xf','rb_d','xr','x_rbd',32)]:
  age=v.local(sl+'.'+src,sport,sl+'.'+dst,dport,range(n),range(n));assert age==0;fields[sport+'->'+dport]=dict(bits=n,edges=age)
 rows.append(dict(slice=sl,sid=row['sid'],master=xf['master'],params=params,canonical=xf['canonical'],fields=fields))
Path(sys.argv[3]).write_text(json.dumps(dict(status='PASS_SELECTED_CURRENT_16_XF_ABI',source_top_sha256=v.die.die_sha,slices=rows,global_admission=False),indent=1)+'\n')
print('PASS16 currentXF NS16 NVL5 LM5 LA6 SIW7;exactlocalGO/partial/RSTDfields all0wireedges')
