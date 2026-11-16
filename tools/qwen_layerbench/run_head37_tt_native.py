#!/usr/bin/env python3
"""Run frozen HP13 frontend/native source construction off/on; no simulation or binding."""
from pathlib import Path
import json,hashlib,subprocess,shutil,sys
import argparse
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
root=args.root.resolve();source=root/'head37_tt_frontend1116';out=root/'head37_tt_native1116';out.mkdir(exist_ok=False)
expected='81f18c88024732039b2f11c36444cfabc5c6c355b19b92a4120938d3787bd544';results=[]
for flag in (0,1):
 p=out/f'head37_{flag}';shutil.copytree(source/'candidate',p);work=p/'work';(work/'generic').mkdir(parents=True);(work/'constructed2').mkdir()
 (p/'run_generic.ys').write_text((p/f'frontend_head37_{flag}.ys').read_text().replace('/work/',str(work)+'/'))
 (p/'run_construct.py').write_text((p/'construct_hp13_2.py').read_text().replace('/work/',str(work)+'/'))
 cmd=['/usr/bin/time','-v','-o',str(work/'frontend.time'),str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-l',str(work/'frontend.log'),'-s','run_generic.ys']
 with (work/'frontend.stdout.log').open('w')as f:subprocess.run(cmd,cwd=p,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (work/'construct.log').open('w')as f:subprocess.run(['/usr/bin/time','-v','-o',str(work/'construct.time'),'python3','run_construct.py'],cwd=p,stdout=f,stderr=subprocess.STDOUT,check=True)
 native=work/'constructed2/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv';sha=hashlib.sha256(native.read_bytes()).hexdigest();rec=json.loads((work/'constructed2/record.json').read_text())
 r={'HEAD_STAGE37':flag,'native_sha256':sha,'native_bytes':native.stat().st_size,'matches_selected_native':sha==expected,'original_cells':rec['original_cells'],'final_cells':rec['final_cells'],'source_constructor_calreg':1,'physical_qualified':False};results.append(r);(out/'progress.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(r),flush=True)
(out/'receipt.json').write_text(json.dumps({'status':'SOURCE_CONSTRUCTED_NOT_PHYSICAL','off_matches_selected':results[0]['matches_selected_native'],'variants':results,'source_frontend_receipt_sha256':hashlib.sha256((source/'receipt.json').read_bytes()).hexdigest(),'global_enable':False,'binding_changed':False,'simulation':'separate actual controller-only gate','corepub_successor':'requires actual source-node clock mapping; old SHA-guarded publisher generator not retagged'},indent=2)+'\n')
