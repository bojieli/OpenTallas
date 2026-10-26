import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/srv/opentallas-scratch/codex-mixq-shell-1015/src');sys.path.insert(0,str(root/'tools/s81_engram_mix'))
import gate
out=root.parent/'run';out.mkdir(exist_ok=True)
results=[]
for mut in range(4):
 d=out/f'L01_m{mut}'
 cmd=['python3',str(root/'tools/s81_engram_mix/gate.py'),'--out',str(d),'--snap',str(root.parent/'fx/engram_L01.pkl'),'--mix4','--fp','rtl','--mut',str(mut)]
 with (out/f'gate_m{mut}.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 text=(d/f'run_m{mut}.log').read_text() if (d/f'run_m{mut}.log').exists() else ''
 ok=r.returncode==0 and '772' in text if mut==0 else r.returncode!=0 and bool(text)
 results.append(dict(layer='L01',mutant=mut,rc=r.returncode,ok=ok,stdout=text))
 (out/'gate_results.json').write_text(json.dumps(results,indent=1));assert ok,results[-1]
 if mut in (0,1):
  ld=out/f'L14_m{mut}';ld.mkdir(exist_ok=True);gate.prep(ld,str(root.parent/'fx/engram_L14.pkl'))
  binary=d/f'obj_rtl_m{mut}_tb_s81_engram_mix4_c/Vtb_s81_engram_mix4_c'
  r=subprocess.run([str(binary),'+dir='+str(ld)],capture_output=True,text=True)
  (ld/f'run_m{mut}.log').write_text(r.stdout+r.stderr)
  ok=r.returncode==0 and '772' in r.stdout if mut==0 else r.returncode!=0
  results.append(dict(layer='L14',mutant=mut,rc=r.returncode,ok=ok,stdout=r.stdout+r.stderr))
  (out/'gate_results.json').write_text(json.dumps(results,indent=1));assert ok,results[-1]
with (out/'census_driver.log').open('w') as log:r=subprocess.run(['python3',str(root/'tools/s81_engram_mix/census.py'),str(out/'census'),'ot_s81_engram_mixq'],stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0
j=json.loads((out/'census/census.json').read_text());assert j['total_flop_bits']==259329,j
assert len(j['flop_bits_by_clock'])==33,j;assert j['flop_bits_by_clock']['ck[0]']==6553,j
mods=json.loads((out/'census/hierarchical.json').read_text())['modules'];top=mods['ot_s81_engram_mixq']
assert sorted(c['type'] for c in top['cells'].values())==['ot_s81_engram_mix','ot_s81_engram_mixq_shell']
shell=mods['ot_s81_engram_mixq_shell'];ports={p:dict(direction=v['direction'],width=len(v['bits'])) for p,v in shell['ports'].items()}
res=dict(source_commit='aa021c333',gate_results=results,census=j,shell_ports=ports,parent_cell_types=[c['type'] for c in top['cells'].values()],source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv',root/'rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv')})
(out/'report.json').write_text(json.dumps(res,indent=1));print(json.dumps(res,indent=1),flush=True)
