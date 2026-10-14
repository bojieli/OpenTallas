from pathlib import Path
import subprocess,json,hashlib,re
base=Path('/srv/opentallas-scratch/codex/q-full-map-6ed42');out=base/'native_graph';image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';top='ot_v41_rom_elem_q_qxpq_w10';lib=base/'libs/merged.lib'
receipt={'source_commit':'6ed42d12c','source_graph_partition_sha256':hashlib.sha256((out/'input.json').read_bytes()).hexdigest(),'partition_script_sha256':hashlib.sha256((base/'partition_source.py').read_bytes()).hexdigest(),'image':image,'physical_admission':False,'commands':[]}
for phase,ys in [('generic',f'read_json {out}/input.json\nhierarchy -top {top}\ncheck\nsynth -top {top} -flatten -noabc\nstat\nwrite_json {out}/generic.json\n'),('mapped',f'read_json {out}/generic.json\ndffunmap\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nstat -liberty {lib}\nwrite_json {out}/mapped.json\n')]:
 (out/(phase+'.ys')).write_text(ys);cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/(phase+'.ys'))]
 with (out/(phase+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 receipt['commands'].append({'phase':phase,'command':cmd,'returncode':r.returncode});(out/'mapped_receipt.json').write_text(json.dumps(receipt,indent=2));print(phase,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
mods=json.loads((out/'mapped.json').read_text())['modules']
def census(t):
 area=0.;sinks=0;macro={}
 for c in mods[t].get('cells',{}).values():
  k=c['type'];m=mods.get(k,{})
  if m and not m.get('attributes',{}).get('blackbox'):
   a,s,mm=census(k);area+=a;sinks+=s
   for n,v in mm.items():macro[n]=macro.get(n,0)+v
  elif k.startswith('ot_rom_'):macro[k]=macro.get(k,0)+1
  else:area+=float(m.get('attributes',{}).get('area',0));sinks+=int(k.startswith('DFF'))
 return area,sinks,macro
rows=[]
for name,c in mods[top]['cells'].items():
 t=c['type']
 if t in mods and not mods[t].get('attributes',{}).get('blackbox'):
  a,s,mac=census(t);rows.append({'instance':name,'module':t,'mapped_std_area_um2':a,'sinks':s,'macros':mac,'ports':{n:{'direction':v['direction'],'width':len(v['bits'])} for n,v in mods[t]['ports'].items()}})
receipt.update({'groups':rows,'total':census(top),'library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'outputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.json','.log','.ys') and p.name!='mapped_receipt.json'},'qualification':'Actual source partition inventory only; original cell/memory connectivity reconstructed exactly, functional full PQ1 proof, independent five clocks, assigned physical interfaces and route remain OPEN.'})
(out/'mapped_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PARTITION_MAPPED',[(r['instance'],r['sinks'],r['mapped_std_area_um2']) for r in rows],flush=True)
