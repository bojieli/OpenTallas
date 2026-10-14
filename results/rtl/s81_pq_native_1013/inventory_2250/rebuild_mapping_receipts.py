from pathlib import Path
import json,re,hashlib,subprocess
out=Path('/var/tmp/s81rom2250/src/results/rtl/s81_pq_native_1013/inventory_2250');libs=Path('/var/tmp/s81rom2250/libs')
for p in out.glob('*_mapped.json'):
 top=p.stem.removesuffix('_mapped');mods=json.load(open(p))['modules'];types={};flops=0
 def walk(m):
  global flops
  for c in mods[m].get('cells',{}).values():
   t=c['type']
   if t in mods and not mods[t].get('attributes',{}).get('blackbox'):walk(t)
   else:
    types[t]=types.get(t,0)+1
    if t.startswith('DFF'):flops+=1
 walk(top)
 log=(out/f'{top}_mapped.log').read_text();areas=re.findall(r"Chip area for (?:top )?module '[^']*': ([\d.]+)",log)
 a={'top':top,'mapped_std_area_um2':float(areas[-1]),'clock_sink_flop_cells':flops,'cells_by_type_hierarchical':types,'macro_area_excluded':True,'qualification':'physical CTS, pin shape and routed throughput still owed','tool_image':subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','openroad/orfs:latest'],text=True).strip(),'mapping':'Yosys0.68 docker read_json native synth -> dffunmap+dfflibmap+ABC ASAP7TT real libraries; includes kept submodules','library_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in libs.glob('asap7*')},'mapped_log_sha256':hashlib.sha256(log.encode()).hexdigest()}
 (out/f'{top}_mapped_receipt.json').write_text(json.dumps(a,indent=2)+'\n');print(top,a['clock_sink_flop_cells'],a['mapped_std_area_um2'],{k:v for k,v in types.items() if k.startswith('ot_sram')})
