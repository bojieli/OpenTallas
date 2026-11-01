from pathlib import Path
import ast,re,json,hashlib
HERE=Path(__file__).resolve().parent;k=Path(__import__('sys').argv[1])
src=(HERE/'parameter_helper_source.py').read_text();ns=dict(ast=ast,re=re,json=json,Path=Path)
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef) and n.name in {'_mask','_integer','_close','_defaults'}:exec(compile(ast.Module(body=[n],type_ignores=[]),'<fixedparam>','exec'),ns)
bound=(k/'rtl_fixed_parameters/s81p_col_h10_r0_p4__t1_bound.sv').read_text();mask=ns['_mask'](bound)
rom='ot_v41_rom_elem_q_qxpq_w10_gb';cf='dsfd_cfifo_crs4';bf='dsfd_bf_front_roots'
rk=Path('/srv/opentallas-scratch2/claude/s81ck5/kits/ot_v41_rom_q_cgr0k3_rti_ck12R')
rconfig=(rk/'config.mk').read_text();args=re.search(r'^export VERILOG_TOP_PARAMS = (.+)$',rconfig,re.M)[1].split()
romfixed={a:int(b) for a,b in zip(args[::2],args[1::2])};assert romfixed['CGR']==0 and romfixed['RSTP']==1
checks=[];headers=[]
for master in [rom,cf,bf]:
 native=(k/'rtl'/f'{master}.sv').read_text();expected=ns['_defaults'](ns['_mask'](native),master)
 if master==rom:expected.update(romfixed)
 if master==cf:
  assert chr(96)+'ifdef DSFD_CRS4_LGATE' in native
  assert '-DDSFD_CRS4_LGATE' not in (k/'config.mk').read_text()
  expected={'LFACE':0,'LGATE':0}
 for hit in re.finditer(r'\b'+re.escape(master)+r'\s*#\s*\(',mask):
  start=hit.end()-1;end=ns['_close'](mask,start);raw=bound[start+1:end-1];argmask=mask[start+1:end-1];actual=dict(expected);pos=0;identity=None
  while pos<len(argmask):
   pm=re.match(r'\s*,?\s*\.(\w+)\s*\(',argmask[pos:])
   if not pm:raise ValueError((master,'bad named arg',raw[pos:]))
   a=pos+pm.end()-1;b=ns['_close'](argmask,a);expr=raw[a+1:b-1].strip()
   if pm[1]=='INSTANCE':
    if master==rom:assert re.fullmatch(r'P_u_r0_u_e\d+_INSTANCE',expr),expr
    elif master==bf:assert expr=='""',expr
    else:raise ValueError('unexpected INSTANCE')
    identity=expr
   else:actual[pm[1]]=ns['_integer'](expr,{})
   pos=b
   if not argmask[pos:].strip():break
  if actual!=expected:raise ValueError((master,'physical specialization mismatch',actual,expected))
  checks.append(dict(master=master,params=actual,INSTANCE=identity))
 clean=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',native)
 h=re.search(r'(?<![\w$])module\s+'+re.escape(master)+r'\b',clean);depth=0;stop=None
 for i in range(h.end(),len(clean)):
  c=clean[i]
  if c=='(':depth+=1
  elif c==')':depth-=1
  elif c==';' and depth==0:stop=i+1;break
 assert stop is not None
 out=k/'rtl'/f'{master}_bb.v';out.write_text('// Exact specialization checked before header staging; content INSTANCE retained.\n(* blackbox *)\n'+clean[h.start():stop]+'\nendmodule\n');headers.append('/work/rtl/'+out.name)
cfg=(k/'config.mk').read_text();line=re.search(r'^export VERILOG_FILES = .+$',cfg,re.M)[0]
(k/'config.before_native_params.mk').write_text(cfg);(k/'config.mk').write_text(cfg.replace(line,line+' '+' '.join(headers)))
ledger=dict(scope='exact selected view specialization, not latest recipe; native content INSTANCE retained',ROM_selected_ODB='577ac0dc4585c0cd16134964b7ddc6d6d0c996e9259bac496b36d0b7ec0f8822',ROM_config_sha256=hashlib.sha256(rconfig.encode()).hexdigest(),CFIFO_selected_view='s81coll_cfifo_crs4 Oct18 spec params{} / source no DSFD_CRS4_LGATE, both defaults0',BF_selected_view='bf_roots_1016_fg content INSTANCE empty; provisional qualification unchanged',checks=checks,headers={p:hashlib.sha256((k/p.replace('/work/','')).read_bytes()).hexdigest()for p in headers})
(k/'native_parameter_binding.json').write_text(json.dumps(ledger,indent=2));print('PASS exact specialization bindings',len(checks))

