from pathlib import Path
import hashlib,json,subprocess,sys
root=Path.cwd();tool=root/'tools/ref_tile/native_census.py';assert hashlib.sha256(tool.read_bytes()).hexdigest()=='4e7a7a425a8669a5f586ed3aa2873038e727293a9128aabae360fcbaa2cd61e0'
for view in ['gu','hu']:
 d=root/view;output=d/'corrected_native_census.json';assert not output.exists(),'No duplicate census'
 args=[sys.executable,str(tool),'--netlist',str(d/'1_2_yosys.v'),'--top','dsdv_sh_lk','--kit','dsdv_sh_lk_s10'+view,'--out',str(output)]
 for p in sorted((d/'libs').iterdir()):args+=['--liberty',str(p)]
 (d/'command.json').write_text(json.dumps(args,indent=2)+'\n')
 with(d/'corrected_native_census.log').open('w')as f:rc=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT).returncode
 if not output.exists():print(view,'TOOL_ERROR',rc);sys.exit(2)
 r=json.loads(output.read_text());print('CORRECTED_NATIVE453',view,'rc',rc,r['status'],'max',r['max_dynamic_loads'],'violations',len(r['violations']),'roles',len(r['role_errors']),flush=True)
