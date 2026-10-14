from pathlib import Path
import json,hashlib,re,collections
base=Path(__file__).resolve().parent
out=base/'clock_per_container_census';out.mkdir(exist_ok=True)
lib=base/'libs/merged.lib'
previous=base/'container_mapping/receipt.json'
receipt={'source_commit':'7602aac02','extractor_commit':'cd377489a','input_mapping_receipt_sha256':hashlib.sha256(previous.read_bytes()).hexdigest(),'input_mapped_json_sha256':hashlib.sha256((base/'container_mapping/mapped.json').read_bytes()).hexdigest(),'physical_admission':False,'clock_delivery_admission':False}
assert receipt['input_mapped_json_sha256']==json.loads(previous.read_text())['outputs_sha256']['mapped.json']
mods=json.loads((base/'container_mapping/mapped.json').read_text())['modules'];top='ot_v41_rom_elem_q_qxpq_w10';types=collections.Counter();clocks=collections.defaultdict(lambda:{'flops':0,'macros':[]});drivers={};groups={}
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
    summary.setdefault('functional_clock_wires',collections.Counter())[wire(c['connections']['CLK'][0])]+=1
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
receipt['groups']=groups;receipt['functional_clock_wire_consumption']={wire:{**row,'source':drivers.get(wire),'physical_root_qualification':False} for wire,row in clocks.items()};receipt['total_flops']=sum(v['flops'] for v in clocks.values());receipt['macro_counts']={k:v for k,v in types.items() if k.startswith('ot_rom_')};receipt['replay_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();receipt['qualification']='Mapped source area and direct clock-wire consumer census only; not a physical CTS root count, phase, pin or timing PASS.'
(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print('CONTAINER_MAPPED_COUNTS',receipt['total_flops'],{k:v['flops'] for k,v in clocks.items()},flush=True)
