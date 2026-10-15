#!/usr/bin/env python3
"""Extract actual elaborated VM hard-boundary census and pure-wire pin producer joins.
Input is Verilator5.050 --json-only, explicit READ_PIPE4/CAP_PIPE2 native candidate source.
No behavioral logic is reclassified as wiring. Missing physical homes stay explicit.
"""
import argparse,collections,gzip,hashlib,json,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def walk(n):
 if isinstance(n,dict):
  yield n
  for v in n.values():yield from walk(v)
 elif isinstance(n,list):
  for x in n:yield from walk(x)
def local(n):
 if isinstance(n,dict):
  yield n
  if n.get('type')=='CELL':return
  for v in n.values():yield from local(v)
 elif isinstance(n,list):
  for x in n:yield from local(x)
def cells(n,path=''):
 if isinstance(n,dict):
  if n.get('type')=='CELL':yield path+n['name'],n;return
  if n.get('type') in ('BEGIN','GENBLOCK') and n.get('name'):path+=n['name']+'.'
  for v in n.values():yield from cells(v,path)
 elif isinstance(n,list):
  for x in n:yield from cells(x,path)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ast',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 tree=json.loads(a.ast.read_text());index={n['addr']:n for n in walk(tree) if 'addr'in n};mods={n['addr']:n for n in tree['modulesp']};specs={}
 for p in (ROOT/'physical/ref_tile').glob('*/spec.json'):
  s=json.loads(p.read_text());specs[p.parent.name]=(s,p)
 def const(n):
  s=n['name'];part=s.split("'")[1].lstrip('s');return int(part[1:].replace('_',''),{'h':16,'d':10,'b':2,'o':8}[part[0]])
 def width(n):
  d=index[n['dtypep']];r=d.get('range');return abs(int(r.split(':')[0])-int(r.split(':')[1]))+1 if r else 1
 def params(m):return {n['name']:const(n['valuep'][0]) for n in m['stmtsp'] if n['type']=='VAR' and n.get('isParam') and n.get('valuep') and n['valuep'][0]['type']=='CONST'}
 def kit(m,path):
  t=m['origName'];p=params(m)
  fixed={'dsfd_vm_static_bank128':'dsfd_vm_static_bank128_m4_v20','dsfd_vm_static_relay128_b4':'dsfd_vm_static_relay128_b4_native_cb','dsfd_vm_static_relay128_b8':'dsfd_vm_static_relay128_b8_native_cb','dsfd_vm_static_write_capture128':'dsfd_vm_direct_capture_'+('e' if p.get('SIDE',0)==0 else 'w')+'_native','dsfd_vm_static_cap_ctl':'dsfd_vm_static_cap_ctl_1015_r2','dsfd_vm_static_cap_leaf':'dsfd_vm_static_cap_leaf_1015_r7','dsfd_vm_static_rsched_p':'dsfd_vm_static_rsched_p_native_1015_l16','dsfd_vm_seq_tile':'dsfd_vm_seq_tile_native_1015_r1','dsfd_vm_static_landing':'dsfd_vm_static_landing_native_1015_r3'}
  if t in fixed:return fixed[t]
  if t=='dsfd_vm_static_scatter_b8_out':return 'dsfd_vm_direct_scatter_b%d_native_cb4'%p['BANK_BASE']
  if re.fullmatch('dsfd_vm_static_fsr_b[0-3]',t):return t+'_native_1015_r1'
  if re.fullmatch('dsfd_vm_static_return_bank8_l[0-3]_p',t):return t+'_native_1015_l16'
  if re.fullmatch('dsfd_vm_static_read_q[0-7]_p',t):return t+'_native_1015_'+('p2' if '_q0_'in t else 'p1')
  if re.fullmatch('dsfd_vm_static_read_v[0-7]_p',t):return t+'_native_1015_p2'
  if t in ('ot_s81_vm_x34_s','ot_s81_vm_x34_t','ot_s81_vm_x43_s','ot_s81_vm_x43_t'):
   w=p['W'];return t+'_w%d_1015_'%w+('r4' if t.endswith('_s') else 'r6') if w==542 else t+'_w%d_1015_f4'%w
  if t in ('dsfd_vm_static_w0_header','dsfd_vm_static_w0_payload','dsfd_vm_static_wdispatch128','dsfd_vm_static_wstage128','dsfd_vm_static_wcontrol'):return 'CANDIDATE:'+t
  return None
 uf={};ranks={}
 def root(x):
  while x in uf:
   if uf[x]in uf:uf[x]=uf[uf[x]]
   x=uf[x]
  return x
 def union(x,y):
  x=root(x);y=root(y)
  if x!=y:
   if ranks.get(x,0)<ranks.get(y,0):x,y=y,x
   uf[y]=x;ranks[x]=max(ranks.get(x,0),ranks.get(y,0)+1)
 unknown=collections.Counter();pending=[];leaves=[];sources={};parent_logic=[];qualification_cache={}
 def expr(n,path):
  t=n['type']
  if t=='VARREF':return [(path,n['varp'],i) for i in range(width(n))]
  if t=='CONST':return [('CONST',str((const(n)>>i)&1),0) for i in range(width(n))]
  if t=='SEL' and n['lsbp'][0]['type']=='CONST':
   start=const(n['lsbp'][0]);return expr(n['fromp'][0],path)[start:start+n['widthConst']]
  if t=='REPLICATE'and n['countp'][0]['type']=='CONST':return expr(n['srcp'][0],path)*const(n['countp'][0])
  if t=='CONCAT':return expr(n['rhsp'][0],path)+expr(n['lhsp'][0],path)
  if t in ('EXTEND','EXTENDS'):
   x=expr(n['lhsp'][0],path);return (x+([x[-1]] if t=='EXTENDS' else [('CONST','0',0)])*width(n))[:width(n)]
  unknown[t]+=1;return [(path,'EXPR'+n['addr'],i) for i in range(width(n))]
 def connect(x,y):
  if len(x)!=len(y):unknown['WIDTH_MISMATCH']+=1;return
  for xx,yy in zip(x,y):union(xx,yy)
 def recurse(m,path,connections=None):
  k=kit(m,path);vars=[n for n in local(m['stmtsp']) if n['type']=='VAR' and n.get('direction')in ('INPUT','OUTPUT','INOUT')]
  if connections:
   for v in vars:
    if v['name']in connections:connect([(path,v['addr'],i)for i in range(width(v))],connections[v['name']])
  if k:
   rec=dict(path=path,master=m['origName'],parameters=params(m),kit=k,ports={v['name']:dict(direction=v['direction'].lower(),bits=width(v))for v in vars},home=None)
   if k in specs:
    s,p=specs[k];rec.update(outline_um=[s['outline']['w'],s['outline']['h']],geometry_source=str(p.relative_to(ROOT)),geometry_sha256=sha(p.read_bytes()),native_view_present=bool(list((p.parent/'views').glob('*/*.lef'))))
   elif k.startswith('CANDIDATE:'):
    t=m['origName'];pn='dsfd_vm_static_wstage128_east' if t=='dsfd_vm_static_wstage128' else t;p=ROOT/'physical/s81_vm_write_edge_1015'/(pn+'.json')
    if p.exists():
     s=json.loads(p.read_text());rec.update(outline_um=s['outline_um'],geometry_source=str(p.relative_to(ROOT)),geometry_sha256=sha(p.read_bytes()),geometry_status='SOURCE_PIN_CANDIDATE_NO_CURRENT_NATIVE_KIT')
   if k in specs:
    spec,sp=specs[k]
    if k not in qualification_cache:
     gate=sp.parent/'gate_result.json';binding=json.loads(gate.read_text()).get('source_binding',{})if gate.exists()else{};snap={x['path']:x.get('sha256')for x in binding.get('files',[])};comparisons=[]
     for source in spec.get('sources',[]):
      pp=ROOT/source;actual=sha(pp.read_bytes())if pp.exists()else None;comparisons.append(dict(source=source,current_sha256=actual,gate_snapshot_sha256=snap.get(source),raw_bytes_equal=actual==snap.get(source)if actual and snap.get(source)else None))
     abstracts=sorted((sp.parent/'views').glob('*/abstract.json'));abstract=json.loads(abstracts[0].read_text())if abstracts else{};run=abstract.get('orfs_dir','');hit=re.search(r'-([a-f0-9]{9,40})/routes/',run)
     qualification_cache[k]=dict(kit_params=spec.get('params',{}),gate_start_commit=binding.get('start_commit'),view_route_source_commit=hit[1]if hit else None,source_comparisons=comparisons,qualification='GEOMETRY_ONLY_CURRENT_ROUTE_NETLIST_IDENTITY_UNVERIFIED')
    rec['route_source_binding']=qualification_cache[k];rec['explicit_kit_param_mismatches']={p:dict(elaborated=rec['parameters'].get(p),kit=v)for p,v in spec.get('params',{}).items()if rec['parameters'].get(p)!=v}
   if 'outline_um'not in rec:rec['geometry_status']='MISSING_ACTUAL_OUTLINE' 
   leaves.append(rec)
   for v in vars:
    for i in range(width(v)):pending.append(((path,v['addr'],i),(len(leaves)-1,v['name'],i,v['direction'])))
   return
  logic=collections.Counter(n['type']for n in local(m['stmtsp']) if n['type']in ('ALWAYS','ALWAYSFF','ALWAYSCOMB','ASSIGNW'))
  if logic:
   posedges=sorted(set(v['name']for n in local(m['stmtsp'])if n['type']=='SENITEM'and n.get('edgeType')=='POS'for v in n.get('sensp',[])if v['type']=='VARREF'))
   parent_logic.append(dict(path=path,master=m['origName'],statements=dict(logic),posedge_roots=posedges,physical_home=None))
  for n in local(m['stmtsp']):
   if n['type']=='ASSIGNW':connect(expr(n['lhsp'][0],path),expr(n['rhsp'][0],path))
  for name,c in cells(m['stmtsp']):
   recurse(mods[c['modp']],path+'.'+name,{pin['name']:expr(pin['exprp'][0],path)for pin in c['pinsp']if pin.get('exprp')})
 top=tree['modulesp'][0];recurse(top,'dut')
 for v in top['stmtsp']:
  if v['type']=='VAR'and v.get('direction')in ('INPUT','OUTPUT'):
   for i in range(width(v)):pending.append((('dut',v['addr'],i),(-1,v['name'],i,'OUTPUT'if v['direction']=='INPUT'else'INPUT')))
 groups=collections.defaultdict(list)
 for net,ep in pending:groups[root(net)].append(ep)
 counts=collections.Counter();edge_groups=[]
 with gzip.open(a.out/'pin_producer_join.jsonl.gz','wt') as f:
  for net,eps in groups.items():
   drivers=[e for e in eps if e[3]=='OUTPUT'];consumers=[e for e in eps if e[3]=='INPUT'];status='CONSTANT'if net in {root(('CONST','0',0)),root(('CONST','1',0))} else('ONE_DRIVER'if len(drivers)==1 else('MULTIPLE_DRIVERS'if len(drivers)>1 else'PARENT_LOGIC_OR_UNRESOLVED'))
   counts[status]+=len(consumers)
   f.write(json.dumps(dict(status=status,drivers=drivers,consumers=consumers),separators=(',',':'))+'\n')
 master_pins={}
 for leaf in leaves:
  k=leaf['kit']
  if k not in master_pins:
   pins={};src=None;status=None
   if k in specs:
    spec,sp=specs[k];lefs=sorted((sp.parent/'views').glob('*/*.lef'))
    if lefs:
     pp=lefs[0];txt=pp.read_text();src=str(pp.relative_to(ROOT));status='ROUTED_LEF'
     for nm,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n',txt,re.S):
      rect=re.search(r'RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',body)
      if rect:
       x,y,X,Y=map(float,rect.groups());pins[nm.replace('\\','')]=[(x+X)/2,(y+Y)/2]
    elif spec.get('io_tcl'):
     src=spec['io_tcl'];txt=subprocess.check_output(['git','show','HEAD:'+src],cwd=ROOT,text=True);status='ASSIGNED_PIN_CANDIDATE_NOT_ROUTED'
     for nm,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer \S+ -location \{([\d.eE+-]+) ([\d.eE+-]+)\}',txt):pins[nm]=[float(x),float(y)]
   elif 'geometry_source'in leaf:
    pp=ROOT/leaf['geometry_source'];d=json.loads(pp.read_text());src=leaf['geometry_source'];status='SOURCE_PIN_CANDIDATE_NOT_ROUTED';pins={p['name']:p['xy_um']for p in d['pins']}
   master_pins[k]=dict(source=src,status=status,pins=pins)
  expected=[p if info['bits']==1 else f'{p}[{i}]'for p,info in leaf['ports'].items()for i in range(info['bits'])]
  leaf['physical_pin_missing']=[p for p in expected if p not in master_pins[k]['pins']]
 with gzip.open(a.out/'master_pins.json.gz','wt')as f:json.dump(master_pins,f,separators=(',',':'))
 c=collections.Counter(x['master']for x in leaves)
 rec=dict(schema='opentallas.s81.vm-current-physical-inventory.v1',scope='NATIVE_CANDIDATE_READ_PIPE4_CAP_PIPE2_NOT_GENERATOR_ADOPTED',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),elaboration=dict(read_pipe=4,cap_pipe=2,ast_sha256=sha(a.ast.read_bytes()),verilator='5.050 --json-only'),hard_leaf_count=len(leaves),families=dict(c),leaves=leaves,parent_logic_regions=parent_logic,missing_outlines=[x['path']for x in leaves if'outline_um'not in x],pin_join=dict(consumers_by_status=dict(counts),expression_gaps=dict(unknown),method='Exact bitwise VARREF/SEL/CONCAT/CONST/EXTEND aliases and hierarchy ports only. Behavioral parent logic stays unresolved; no invented producer or straight-wire assumption.'),not_claimed=['No existing complete placement','No native packing adoption','No parent TT/FF/DRC/phi-R or full traffic cut proof'])
 (a.out/'inventory.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps({k:rec[k]for k in ['hard_leaf_count','families','missing_outlines','pin_join']},indent=1))
if __name__=='__main__':main()
