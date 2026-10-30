import sys,json,types,shutil
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-rtclock-1030');S=O/'src';sys.path.insert(0,str(S/'tools/die_plan'))
import core_family_slice as C
core='ot_s81sl_cap_rt';fams=json.loads((O/'family_std.json').read_text());fams['families'][0].update(wire='ndr2w',name='s81sl_macro_rt_native_n_ndr')
(O/'family_ndr.json').write_text(json.dumps(fams,indent=2)+'\n');d=O/'ndr'/core;d.mkdir(parents=True,exist_ok=True)
for f in ('geo.txt','sites.txt','clkport.txt','geo.log','sites.log'):shutil.copy2(O/'std'/core/f,d/f)
C.render=lambda *args,**kwargs:None
a=types.SimpleNamespace(trunk_cal=None,replan_cal=None,fit=None,libdir=None,d1_steps=60,libtt=str(O/'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib'),libff=str(O/'asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib'))
r=C.run_core(fams,core,O/'kit',O/'ndr',a);(O/'ndr_result.json').write_text(json.dumps(r,indent=2)+'\n')
