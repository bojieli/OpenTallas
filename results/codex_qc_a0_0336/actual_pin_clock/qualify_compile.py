"""Model-only complete compiler check; no install, kit mutation, or SDC write."""
from pathlib import Path
import json,sys
p=Path.cwd();sys.path.insert(0,str(p/'natural_model/tools'));import core_infra as C
source,model,report,kit,out=sys.argv[1:];sl=json.load(open(source));m=json.load(open(model));r=json.load(open(report));t=sl['core_tree'];t['install_stage']='pre_cts';t['model_qualification']={'measured_timing_used':False,'electrical_latency_qualified':True,'source':str(Path(model).resolve()),'model':m['basis'],'band_policy':'info','window_policy':'info','corners':r['corners']}
try:
 text=C.emit_tcl(sl,Path(kit));Path(out+'_compiler.tcl').write_text(text);Path(out+'_qualified.json').write_text(json.dumps(sl,indent=1)+'\n');result={'status':'PASS','scope':'model-only compiler emit; not installed or adopted','clock_nodes':len(t['nodes']),'source':source,'corners':r['corners']}
except Exception as e:result={'status':'FAIL','scope':'model-only compiler emit; not installed or adopted','exception':type(e).__name__,'reason':str(e),'source':source}
Path(out+'_compile.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
