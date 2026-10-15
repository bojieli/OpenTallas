#!/usr/bin/env python3
"""Separate TT/FF/SS libraries on actual CTS ODB; placement RC diagnostic only."""
import argparse,sys,json,re,hashlib,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--orfs-dir',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--kit',required=True);p.add_argument('--corner-tool',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.corner_tool.parent));import corner_sta as C
base=next((a.orfs_dir/'results/asap7').glob('*/base'));rel='/work/'+str(base.relative_to(a.orfs_dir));a.out.mkdir(parents=True,exist_ok=True);vts=C.extra_vts(base/'4_cts.odb');results={}
for c in ('tt','ff','ss'):
 t=C.script(c,rel,[],post_sdc=[a.kit+'/signoff.sdc'],sdc_name='4_cts.sdc',vts=vts)
 t=t.replace('/6_final.odb','/4_cts.odb').replace('read_spef '+rel+'/6_final.spef','source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\nestimate_parasitics -placement')
 tp=a.out/f'{c}.tcl';tp.write_text(t)
 r=subprocess.run(['docker','run','--rm','-v',str(a.orfs_dir)+':/work:ro','-v',str(a.source_root)+':/src:ro','-v',str(a.out)+':/audit','openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/'+tp.name],capture_output=True,text=True)
 log=r.stdout+'\n'+r.stderr;(a.out/f'{c}.log').write_text(log);errors=re.findall(r'(?:\[ERROR[^\n]*|^Error:[^\n]*)',log,re.M)
 m=re.search(r'^OT_WS (\S+)',log,re.M);slack=float(m.group(1))*1e12 if m else None
 results[c]={'corner':c,'check':'hold' if c=='ff' else 'setup','tool_rc':r.returncode,'errors':errors,'worst_slack_ps':slack,'libs':C.corner_libs(c,vts),'tcl_sha256':hashlib.sha256(t.encode()).hexdigest()}
result={'scope':'Independent actual TT/FF/SS library loads on frozenCTS ODB; placementRC, exact post-propagated native signoffSDC. Pre-route diagnostic, notrouted/signoff/DRC0.','results':results,'source_sha256':{'odb':C.sha(base/'4_cts.odb'),'cts_sdc':C.sha(base/'4_cts.sdc'),'native_signoff_sdc':C.sha(a.source_root/a.kit/'signoff.sdc'),'corner_tool':C.sha(a.corner_tool)},'TT_setup_FF_hold_pass':all(results[c]['tool_rc']==0 and not results[c]['errors'] and results[c]['worst_slack_ps'] is not None and results[c]['worst_slack_ps']>=0 for c in ('tt','ff'))};(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['TT_setup_FF_hold_pass'] else 1)
