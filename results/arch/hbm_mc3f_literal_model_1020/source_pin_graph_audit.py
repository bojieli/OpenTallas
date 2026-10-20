"""Read immutable source-matched synthesis DB, no placement or PG qualification."""
import odb,json,hashlib,gzip,re
from pathlib import Path
from collections import defaultdict
SRC=Path('/frozen/src'); WORK=Path('/frozen/work'); OUT=Path('/work')
manifest=json.load(open(OUT/'source_manifest.json'));matches=[]
for n,h in manifest['files'].items():
 if n.startswith('rtl/') or n.endswith('_bb.v'):
  p=SRC/n;a=hashlib.sha256(p.read_bytes()).hexdigest();assert a==h,n;matches.append(dict(path=n,sha256=a))
cfg=(WORK/'config.mk').read_text();params=dict(re.findall(r'(OREG|KREG|KRREG|RREG|WPAY|RESET_LANDING|SRAM_P192|PURE_FACE|RST_FOREST|PCID_LOCAL|RST_LEAVES|WROK_COPIES|POST_REG)\s+(\d+)',cfg))
expected=dict(OREG='1',KREG='1',KRREG='1',RREG='1',WPAY='1',RESET_LANDING='2',SRAM_P192='1',PURE_FACE='1',RST_FOREST='1',PCID_LOCAL='1',RST_LEAVES='256',WROK_COPIES='1',POST_REG='1');assert params==expected,(params,expected)
def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=m.end();d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
roles={};libs=[]
root=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
for p in sorted(root.glob('*RVT_TT*.lib*')):
 if 'FAKE' in p.name:continue
 raw=p.read_bytes();s=gzip.decompress(raw).decode()if p.suffix=='.gz'else raw.decode();libs.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()))
 for n,b in blocks(s,'cell'):
  pins={}
  for pn,pb in blocks(b,'pin'):
   dr=re.search(r'\bdirection\s*:\s*(\w+)',pb);fn=re.search(r'\bfunction\s*:\s*"([^"]+)"',pb)
   pins[pn]=dict(direction=dr[1]if dr else None,function=fn[1]if fn else None,clock=bool(re.search(r'\bclock\s*:\s*true',pb)))
  ins=[n for n,p in pins.items()if p['direction']=='input'];outs=[n for n,p in pins.items()if p['direction']=='output']
  unary=False
  if len(ins)==len(outs)==1:
   fn=re.sub(r'[()\s]','',pins[outs[0]]['function']or'');unary=fn in[ins[0],'!'+ins[0],ins[0]+"'"]
  ns=re.search(r'\bnext_state\s*:\s*"([^"]+)"',b)
  roles[n]=dict(pins=pins,sequential=bool(re.search(r'\bff\s*\(',b)),next_state=ns[1]if ns else None,unary=unary)
odbpaths=list((WORK/'results/asap7').glob('*/base/1_synth.odb'));assert len(odbpaths)==1
p=odbpaths[0];db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock();dbu=block.getDbUnitsPerMicron()
instances={i.getName():i for i in block.getInsts()};unknown=sorted({i.getMaster().getName()for i in instances.values()if not i.getMaster().isBlock()}-set(roles));assert not unknown,unknown
loads=defaultdict(list);drivers=defaultdict(list)
for i in instances.values():
 for t in i.getITerms():
  if not t.getNet()or str(t.getMTerm().getSigType())in['POWER','GROUND']:continue
  (loads if str(t.getMTerm().getIoType())=='INPUT'else drivers)[t.getNet().getId()].append(t)
def walk(net,direction):
 todo=[net];seen=set();front=[];bufs=set()
 while todo:
  n=todo.pop()
  if n.getId()in seen:continue
  seen.add(n.getId())
  for t in(loads if direction=='input'else drivers)[n.getId()]:
   i=t.getInst();r=roles.get(i.getMaster().getName(),{})
   if r.get('unary'):
    bufs.add(i.getName())
    for q in i.getITerms():
     if str(q.getMTerm().getIoType())==('OUTPUT'if direction=='input'else'INPUT')and q.getNet():todo.append(q.getNet())
   else:
    pn=t.getMTerm().getName();pr=r.get('pins',{}).get(pn,{})
    ok=r.get('sequential',False)and not pr.get('clock',False)
    if direction=='input':ok=ok and pn in re.findall(r'[A-Za-z_][A-Za-z0-9_]*',r.get('next_state')or'')
    else:ok=ok and pr.get('direction')=='output'
    front.append(dict(inst=i.getName(),master=i.getMaster().getName(),pin=pn,sequential_data=bool(ok)))
 return front,sorted(bufs)
ports=[];errors=[];pinff=set()
for p in block.getBTerms():
 if str(p.getSigType())in['POWER','GROUND']:continue
 name=p.getName()
 if name=='clk':continue
 direction=str(p.getIoType()).lower();assert direction in['input','output']
 if not p.getNet():errors.append('unconnected '+name);continue
 f,b=walk(p.getNet(),direction)
 if not f or not all(t['sequential_data']for t in f):errors.append('nonregistered '+name)
 pinff.update(t['inst']for t in f if t['sequential_data']);ports.append(dict(port=name,direction=direction,frontier=f,transparent=b))
# Include the second explicitly declared reset-landing FF, not arbitrary reset leaves.
landing=[n for n in instances if 'g_reset_face.rst_l' in n];assert len(landing)==2,landing;pinff.update(landing)
macros=sorted(n for n,i in instances.items()if i.getMaster().isBlock());area=lambda i:i.getMaster().getWidth()*i.getMaster().getHeight()/dbu**2
std=sum(area(i)for i in instances.values()if not i.getMaster().isBlock());pinarea=sum(area(instances[n])for n in pinff)
r=dict(status='PASS_SOURCE_PIN_GRAPH'if not errors else'FAIL',errors=errors,params=params,
 source_files=matches,odb_sha256=hashlib.sha256(odbpaths[0].read_bytes()).hexdigest(),config_sha256=hashlib.sha256(cfg.encode()).hexdigest(),
 real_standard_libs=libs,unknown_masters=unknown,ports=ports,input_ports=sum(p['direction']=='input'for p in ports),output_ports=sum(p['direction']=='output'for p in ports),
 macros=macros,macro_count=len(macros),native_std_cells=len(instances)-len(macros),std_area_um2=std,
 source_pin_FF_inventory=sorted(pinff),source_pin_FF_count=len(pinff),source_pin_FF_area_um2=pinarea,
 remaining_source_ordinary_area_um2=std-pinarea,reset_landing=landing,
 placement_qualified=False,clock_qualified=False,PG_qualified=False,
 scope='Immutable source-matched1_synth native connectivity only; all nonclock port first/last frontiers must be actual real-Lib FF data D/Q. Does not approve placed pin exceptions/band/clock/PG/reach.')
(OUT/'source_pin_graph.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in['ports','source_pin_FF_inventory','real_standard_libs','source_files']}));assert not errors
