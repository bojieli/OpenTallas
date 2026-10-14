from pathlib import Path
import json,hashlib,subprocess,re,collections
base=Path(__file__).resolve().parent;out=base/'container_mapping';out.mkdir(exist_ok=True)
lib=base/'libs/merged.lib';source=base/'output/containers/partitioned.json'
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
manifest=json.loads((base/'source_manifest.json').read_text());assert all(hashlib.sha256((base/p).read_bytes()).hexdigest()==h for p,h in manifest['sha256'].items())
ys='read_json '+str(source)+'\nsynth -top ot_v41_rom_elem_q_qxpq_w10 -flatten -noabc\nstat\nwrite_json '+str(out/'generic.json')+'\ndffunmap\ndfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nstat -liberty '+str(lib)+'\nwrite_json '+str(out/'mapped.json')+'\n'
(out/'mapped.ys').write_text(ys)
cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/'mapped.ys')]
with (out/'mapped.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
print('MAPPED',r.returncode,flush=True)
receipt={'source_commit':'7602aac02','extractor_commit':'cd377489a','source_manifest':manifest,'container_graph_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'replay_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'command':cmd,'returncode':r.returncode,'physical_admission':False,'clock_delivery_admission':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
if r.returncode:raise SystemExit(r.returncode)
mods=json.loads((out/'mapped.json').read_text())['modules'];top='ot_v41_rom_elem_q_qxpq_w10';types=collections.Counter();clocks=collections.defaultdict(lambda:{'flops':0,'macros':[]});drivers={};groups={}
areas={}
text=lib.read_text()
for m in re.finditer(r'cell\s*\(\s*([^)]*?)\s*\)\s*\{',text):
 start=m.end();i=start;n=1
 while n:
  if text[i]=='{':n+=1
  if text[i]=='}':n-=1
  i+=1
 match=re.search(r'\barea\s*:\s*([0-9.eE+-]+)',text[start:i])
 if match:areas[m.group(1).strip().strip('"')]=float(match.group(1))
def walk(module,path,bindings,summary):
 def wire(bit):return bindings.get(bit,path+':'+str(bit)) if isinstance(bit,int) else 'const:'+str(bit)
 for name,c in mods[module].get('cells',{}).items():
  typ=c['type'];full=path+'.'+name
  if typ in mods and not mods[typ].get('attributes',{}).get('blackbox'):
   cb={}
   for port,descriptor in mods[typ].get('ports',{}).items():
    if port in c['connections']:
     for inner,outer in zip(descriptor['bits'],c['connections'][port]):cb[inner]=wire(outer)
   child=summary
   if module==top:
    child={'std_area_um2':0.0,'flops':0,'macros':collections.Counter()};groups[full]=child
   walk(typ,full,cb,child)
  else:
   types[typ]+=1
   ismacro=typ.startswith('ot_rom_')
   if ismacro:summary['macros'][typ]+=1
   else:summary['std_area_um2']+=areas.get(typ,0)
   if typ.startswith('DFF'):
    summary['flops']+=1
    clk=c['connections'].get('CLK');assert clk and len(clk)==1,(typ,c['connections'])
    clocks[wire(clk[0])]['flops']+=1
   if typ.startswith('ICG'):
    output=c['connections'].get('GCLK');assert output and len(output)==1
    drivers[wire(output[0])]={'actual_instance':full,'cell':typ,'output_pin':'GCLK','input_clock_wire':wire(c['connections']['CLK'][0]),'enable_wire':wire(c['connections']['ENA'][0])}
   if ismacro:
    cp=next((p for p in ('CLK','clk','ck') if p in c['connections']),None)
    if cp:clocks[wire(c['connections'][cp][0])]['macros'].append({'instance':full,'master':typ,'clock_pin':cp})
summary={'std_area_um2':0.,'flops':0,'macros':collections.Counter()}
for name,port in mods[top]['ports'].items():
 if name=='clk':
  for bit in port['bits']:drivers[top+':'+str(bit)]={'actual_top_port':'clk','source_driver':None,'physical_phase':None}
walk(top,top,{},summary)
receipt['groups']=groups;receipt['functional_clock_wire_consumption']={wire:{**row,'source':drivers.get(wire),'physical_root_qualification':False} for wire,row in clocks.items()};receipt['total_flops']=sum(v['flops'] for v in clocks.values());receipt['macro_counts']={k:v for k,v in types.items() if k.startswith('ot_rom_')};receipt['outputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='receipt.json'};receipt['qualification']='Mapped source area and direct clock-wire consumer census only; not a physical CTS root count, phase, pin or timing PASS.'
(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print('CONTAINER_MAPPED_COUNTS',receipt['total_flops'],{k:v['flops'] for k,v in clocks.items()},flush=True)
