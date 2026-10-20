import pathlib,json,hashlib,re,ast
P=pathlib.Path
D=P('/srv/opentallas-scratch/claude/kv-tok/veh'); K=P('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub'); R=K.parent/'kvs14r-4db097403-codexmub'
files={}; missing=[]
def add(p,role):
 p=P(p)
 if not p.is_file(): missing.append(str(p));return
 key=str(p)
 if key not in files: files[key]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'roles':[]}
 if role not in files[key]['roles']:files[key]['roles'].append(role)
 return p.read_text(errors='replace')
for n in ['cases.txt','cases_stk.txt']:add(D/n,'frozen cases')
for n in ['port_bind_v2/die_bound.v','port_bind_v2/port_bind_v2.json','case_kv/relay_stages.json','case_kv/boot_ages.json','relay_check.json']:add(R/n,'frozen generated die input')
for n in ['kva_vehicle.sh','run_kv_attn_mu.sh','kv_attn_grp_map.py','slice_cut.py','slice_smoke.py','kva_mu_ports.py','drive_qwk_slice_attn_mu.svh','kv_attn_vectors.py']:add(D/'tools/qwen_layerbench'/n,'frozen tool')
add(D/'tools/die_port_bind.py','frozen parser')
vehicles={}; pending=[]; incdirs=[]
for v in ['WSQK','P0','P1']:
 sl=D/'g7'/v/'cut';sj=sl/'slice.json'; t=add(sj,'generated slice facts'); j=json.loads(t);top=j['top'];ff=sl/(top+'.f');ft=add(ff,'generated file list'); add(sl/(top+'.sv'),'generated slice RTL');
 vehicles[v]={'top':top,'masters':j['masters'],'instances':j['instances'] if isinstance(j['instances'],int) else len(j['instances']),'ports':len(j['ports']),'die_sha256':j['die_sha256']}
 for n in ['kva_grp_map.svh','kva_grp_facts.json','kva_ports.svh','kva_hier_refs.svh']:add(sl/n,'generated bench include or facts')
 for line in ft.splitlines():
  if line.startswith('+incdir+'):incdirs.append(P(line[8:]))
  elif line and not line.startswith(('+','-')):pending.append(P(line))
 for n in ['ot_sram_1r1w_256x128_m1_r2c2','ot_sram_1r1w_64x128_m1_r2c2']:pending.append(K/'physical/qkd_astk_strip/macros'/n/(n+'.v'))
 pending.append(K/'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v')
seen=set()
while pending:
 p=pending.pop()
 if str(p) in seen:continue
 seen.add(str(p));t=add(p,'compiled RTL/model closure')
 if not t:continue
 for inc in re.findall(r'`include\s+"([^"\n]+)"',t):
  opts=[p.parent/inc]+[d/inc for d in incdirs];q=next((x for x in opts if x.is_file()),None)
  if q:pending.append(q)
  else:missing.append('include:'+inc+' from '+str(p))
cases=(D/'cases_stk.txt').read_text()
for d in sorted(set(re.findall(r'\+VEC\d+=([^\s]+)',cases))):
 for n in ['q.hex','gold.hex','kv.hex','isa.hex','ctx']:add(P(d)/n,'frozen vector; only q/kv/gold consumed at runtime')
# Explicit source for optional vector regeneration; recursively discover local Python imports.
pending=[K/'tools/qwen_hbmacc_position_oracle_gpu.py',D/'tools/qwen_layerbench/kv_attn_gold.py',D/'tools/qwen_layerbench/kv_attn_vectors.py',K/'tools/qwen_nearhbm_attn_ref.py',K/'tools/hdc_golden.py'];seen=set();imports=[]
while pending:
 p=pending.pop()
 if str(p) in seen:continue
 seen.add(str(p));t=add(p,'vector-generator provenance (not simulation runtime)')
 if not t:continue
 try:tree=ast.parse(t)
 except SyntaxError:continue
 for node in ast.walk(tree):
  names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
  for name in names:
   q=next((x for x in [p.parent/(name.replace('.','/')+'.py'),D/'tools'/(name.replace('.','/')+'.py'),K/'tools'/(name.replace('.','/')+'.py')] if x.is_file()),None)
   if q:pending.append(q)
   else:imports.append(name)
print(json.dumps({'schema':'opentallas.kv_token_vehicle_frozen_files.v1','host':'ot-epyc5','die_run':str(R),'source_tree':str(K),'vehicles':vehicles,'files':files,'missing':sorted(set(missing)),'external_python_imports':sorted(set(imports))},indent=2))
