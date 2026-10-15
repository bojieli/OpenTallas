from pathlib import Path
import subprocess,json
root=Path('/srv/opentallas-scratch/codex/s81-hcp-partition-1015-v2')
base=Path('/srv/opentallas-scratch/codex/s81-hcx-native-1014')
exe=root/'pass/obj/Vtb_s81_hcx_projection_partition'
out=root/'boundary';out.mkdir(exist_ok=True)
rows=[]
for tag,layer in [('L00',0),('L24',24),('L25',25),('L39',39),('M0R0',40),('M1R0',41),('M2R4',42)]:
 cmd=[str(exe),'+DIR='+str(base/'resident_boundary_final'/tag),'+OT_ROM_DIR='+str(base/'resident_row0_full'),f'+LAYER={layer}']
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/(tag+'.log')).write_text(p.stdout)
 passed=p.returncode==0 and 'HCX_PROJECTION PASS' in p.stdout and p.stdout.count('native_cycles264')==2
 rows.append({'tag':tag,'layer':layer,'returncode':p.returncode,'exact_outputs':2 if passed else 0,'cycles':264 if passed else None,'pass':passed})
 print(tag,passed,flush=True)
p=subprocess.run([str(exe),'+DIR='+str(base/'resident_boundary_final/L25'),'+OT_ROM_DIR='+str(base/'resident_row0_full'),'+LAYER=25','+MUT_STAGE'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'stage_mutant.log').write_text(p.stdout)
mut=p.returncode!=0 and 'HCX_PROJECTION FAIL' in p.stdout
summary={'scope':'Actual clock-partition candidate arithmetic gate; equal-phase clock waveforms only, no CTS or physical qualification','rows':rows,'mutant_rejected':mut,'mutant_returncode':p.returncode,'all_pass':all(r['pass'] for r in rows) and mut}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2));raise SystemExit(0 if summary['all_pass'] else 1)
