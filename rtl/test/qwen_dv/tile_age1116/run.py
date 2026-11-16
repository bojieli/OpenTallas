import subprocess,json,re
from pathlib import Path
P=Path(__file__).parent;out={}
for op,name in enumerate(['qkv','o','gu','down']):
 r=subprocess.run([str(P/'obj/Vtb'),f'+cmds={P}/commands.hex',f'+op={op}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (P/(name+'.log')).write_text(r.stdout);lines=[s for s in r.stdout.splitlines() if s.startswith('TV ')];end=next((s for s in r.stdout.splitlines() if s.startswith('TILE_TIMING')),'');out[name]={'rc':r.returncode,'summary':end,'valid_edges':[int(re.search(r'edge(\d+)',s)[1]) for s in lines],'fault_observed':'FAULT ' in r.stdout}
(P/'mutant.hex').write_text(('0'*95+'\n')*4)
r=subprocess.run([str(P/'obj/Vtb'),f'+cmds={P}/mutant.hex','+op=0'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(P/'invalid_command_mutant.log').write_text(r.stdout);out['invalid_command_mutant']={'rc':r.returncode,'summary':next((s for s in r.stdout.splitlines() if s.startswith('TILE_TIMING')),''),'fault_observed':'FAULT ' in r.stdout}
(P/'results.json').write_text(json.dumps(out,indent=2)+'\n')
for k,v in out.items():print(k,v['summary'],flush=True)
