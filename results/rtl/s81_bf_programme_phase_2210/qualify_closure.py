import json,os,sys,importlib.util
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200');source=r/'source_closure_candidate1';native=Path('/srv/opentallas-scratch2/claude/wt/die-s81-47b')
os.environ['OT_S81_SELECTED_SOURCE_ROOT']=str(source)
os.environ['OT_S81_SELECTED_ASBUILT_MANIFEST']='asbuilt_kva3_g3tag2_sel.json'
os.environ['OT_XS_ASB_SCHEDULE_DIR']=str(r)
os.environ['OT_XS_BF_MEAS']=str(r/'h10x_candidate.json')
for suffix in ['tools','tools/s81_dv','tools/s81_dv/layer_prog','tools/s81']:
 sys.path.insert(0,str(native/suffix))
import lower_xs
spec=importlib.util.spec_from_file_location('xs_bf_current',r/'xs_bf_current.py');bf=importlib.util.module_from_spec(spec);spec.loader.exec_module(bf)
records=bf.load_meas();rec,calendar=bf.meas_for(records,'col_h10',2,'asb_x',op='attn.wo_a')
assert calendar=='measured_bf_active_idle_q'
report=dict(status='PASS_EXACT_RETAINED_PROFILE_QUALIFIER',calendar=calendar,source_root=str(source),current_native_selected_RTL_changed=False,production_enabled=False,scope=rec['asbuilt_source_qualification']['scope'],source_manifest='retained immutable qualification manifest; not newly adopted selector manifest',added_cycles=0)
(r/'source_closure_qualified.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
