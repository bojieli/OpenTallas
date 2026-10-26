import re,json,collections,hashlib
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/codex-qc-a0-2157/parent_rawcut_mapped.v');s=p.read_text();mods={};clks=collections.Counter();types=collections.Counter();hard=[]
for m in re.finditer(r'^module\s+(\\?\S+?)\s*\((.*?)^endmodule',s,re.M|re.S):
 name=m[1].lstrip('\\');body=m[2];cells=[]
 for c in re.finditer(r'^  (\w+|\\\S+)\s+(\\?\S+)\s+\(\n(.*?)\n  \);',body,re.M|re.S):
  ports={a:b.strip()for a,b in re.findall(r'\.(\w+)\((.*?)\)',c[3],re.S)};cells.append((c[1].lstrip('\\'),c[2].lstrip('\\'),ports))
 mods[name]=cells

def visit(mod,portmap,path=''):
 for t,n,ps in mods[mod]:
  mapped={a:portmap.get(b,b)for a,b in ps.items()}
  if t in mods:visit(t,mapped,path+n+'/')
  elif t.startswith('DFF'):
   types[t]+=1;clks[mapped.get('CLK','MISSING')]+=1
  elif '_ASAP7_'in t:types[t]+=1
  else:hard.append({'type':t,'inst':path+n,'clock':{a:b for a,b in mapped.items()if a in('clk','ck')or a.startswith('ck_')}})
visit('qfd_tile_nk_a0c',{})
r={'mapped_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'standard_cells':sum(types.values()),'ff':sum(clks.values()),'ff_clock_nets':clks,'hard_instances':hard,'types':types,'status':'ACTUAL source synthesis census; no LEF/lib/CTS insertion credit'}
o=Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-2157/results/qc_a0_2157/rawfault_cut/parent_actual_synth.json');o.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in('types','hard_instances')},indent=2));print('hard',len(hard),collections.Counter(x['type']for x in hard));assert sum(x['type']=='ot_qwen_tile_lsl_rawfault_m3'for x in hard)==8
