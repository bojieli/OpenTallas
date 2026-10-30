import sys,json,types,shutil
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-rtclock-1030')
S=O/'src';sys.path.insert(0,str(S/'tools/die_plan'))
import core_family_slice as C
kit=O/'kit'; core='ot_s81sl_cap_rt'
fams=json.loads((S/'physical/die_plan/s81/core_lat/families_r13.json').read_text())
fam=next(f for f in fams['families'] if f['name']=='s81sl_macro')
fam.update(name='s81sl_macro_rt_native_n',members=[core],macro_keepout={core:True},entry='centre')
fams={'families':[fam]};(O/'family_std.json').write_text(json.dumps(fams,indent=2)+'\n')
work=O/'std'/core;work.mkdir(parents=True,exist_ok=True)
base=next((kit/'run/results/asap7').glob('*/base'));rel=base.relative_to(kit)
C.docker_or(kit,'core_family_geo.tcl',dict(ODB='/work/'+str(rel)+'/3_place.odb',OUT='/work/r13_geo.txt',CLK='clk',ENTRY='129.612 129.36'),work/'geo.log')
(kit/'r13_geo.txt').replace(work/'geo.txt')
(work/'clkport.txt').write_text(C.clock_bterm_from_log((work/'geo.log').read_text(),'clk')+'\n')
C.render=lambda *args,**kwargs:None
args=types.SimpleNamespace(trunk_cal=None,replan_cal=None,fit=None,libdir=None,d1_steps=60,libtt=str(O/'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib'),libff=str(O/'asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib'))
result=C.run_core(fams,core,kit,O/'std',args)
(O/'std_result.json').write_text(json.dumps(result,indent=2)+'\n')
