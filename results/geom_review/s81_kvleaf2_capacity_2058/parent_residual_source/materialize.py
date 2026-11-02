from pathlib import Path
import re,json,hashlib,shutil
P=Path(__file__).parent;source=Path('/srv/opentallas-scratch/claude/codex-s81-kvbridge-size-2111');R=P/'rtl';R.mkdir(exist_ok=True)
for f in (source/'rtl').iterdir():
 if f.is_file():shutil.copy2(f,R/f.name)
census=json.load(open('/srv/opentallas-scratch/claude/wt/codex-s81-kvleaf2-census-2058/results/geom_review/s81_kvleaf2_capacity_2058/source_cut_census.json'))
cuts=[dict(z)for z in census['matching_common23']];cuts.append(dict(bound_inst='u_g_kv_u_kv',module='ot_s81sl_kv_leaf',actual_params='.CNIK(1), .CNIK_MUT(0), .CP(1), .CP_MUT(0), .HARD_RQ(0)'))
bound=R/'s81p_ot_s81sl_kv_leaf__t2_bound.sv';text=bound.read_text();before=hashlib.sha256(text.encode()).hexdigest();receipts=[]
def blankcomments(s):return re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:' '*len(m[0]),s,flags=re.S)
def header(module):
 found=[]
 for f in (source/'rtl').iterdir():
  if not f.is_file():continue
  s=f.read_text();clean=blankcomments(s);m=re.search(r'\bmodule\s+'+re.escape(module)+r'\b',clean)
  if not m:continue
  depth=0;end=None
  for k in range(m.end(),len(clean)):
   if clean[k]=='(':depth+=1
   elif clean[k]==')':depth-=1
   elif clean[k]==';'and depth==0:end=k+1;break
  assert end is not None;h=s[m.start():end];assert re.search(r'\b(input|output|inout)\b',blankcomments(h)),('nonANSI',module)
  found.append((f,h))
 assert len(found)==1,(module,len(found));return found[0]
for z in cuts:
 module,inst=z['module'],z['bound_inst'];alias='ot_s81_resid_cut_'+inst;f,h=header(module);h=blankcomments(h)
 decl=re.search(r'(?m)^\s*'+re.escape(module)+r'\s*(?:#\s*\((?P<params>[^;\n]*)\))?\s+'+re.escape(inst)+r'\s*\(',text);assert decl,(module,inst)
 actual_params=decl.group('params') or '';params=dict(re.findall(r'\.([A-Za-z_]\w*)\s*\(\s*([^()]*)\s*\)',actual_params))
 # Specialize only explicit declared integer parameter defaults to exact selected profile.
 for name,val in params.items():
  pat=r'(\b'+re.escape(name)+r'\s*=\s*)([^,\n)]+)';h,n=re.subn(pat,lambda m:m[1]+val.strip(),h);assert n==1,(module,name,n)
 h=re.sub(r'\bmodule\s+'+re.escape(module)+r'\b','module '+alias,h,count=1)
 bb='// SOURCE-ONLY sizing boundary, never a physical hard view. Exact native port header/profile.\n(* blackbox, keep_hierarchy *)\n'+h+'\nendmodule\n'
 out=R/(alias+'_bb.v');out.write_text(bb)
 pat=r'(?m)^(\s*)'+re.escape(module)+r'(\s*(?:#\s*\([^;\n]*\))?\s+)'+re.escape(inst)+r'\b'
 text,n=re.subn(pat,lambda m:m[1]+'(* keep = 1 *) '+alias+m[2]+inst,text);assert n==1,(inst,n)
 receipts.append(dict(bound_instance=inst,original_module=module,alias_module=alias,exact_selected_parameters=params,header_source=f.name,source_header_sha256=hashlib.sha256(header(module)[1].encode()).hexdigest(),new_header_sha256=hashlib.sha256(bb.encode()).hexdigest()))
bound.write_text(text);files=[v for v in json.load(open(source/'PREP.json'))['source_files']if not v.endswith('ot_s81sl_kv_bridge_size_top.sv')];files+=[f'/work/rtl/{n}'for n in ['s81p_ot_s81sl_kv_leaf__t2.sv','s81p_ot_s81sl_kv_leaf__t2_bound.sv']];files.extend('/work/rtl/'+z['alias_module']+'_bb.v'for z in receipts)
(P/'PREP.json').write_text(json.dumps(dict(status='SOURCE_ONLY_PREP_NOT_DISPATCHED',scope='Distinct normal parent-residual SYNTH sizing with24 exact direct source boundaries; no hard-view/source-plan adoption',root_authorization='Parent residual with23 matched hard source blackboxes if needed, distinct minimalvehicle',input_native_GEN_readset='intel1 kit-wave/s81/e8cbe5f6c70/items/ot_s81sl_kv_leaf__t2/gen/ot_s81sl_kv_leaf__t2/rtl',native_bound_before_sha256=before,native_bound_after_sha256=hashlib.sha256(text.encode()).hexdigest(),cuts=receipts,expected_cut_instances=24,source_files=files,top='s81p_ot_s81sl_kv_leaf__t2',added_ff=0,added_cycles=0,holds=['Normal RTL_LINT/current alias registry acceptance','Measured residual count excludes all24 abstract children; wholeKV mapped count remains separate','No physical blackbox/LEF/timing contract or canonical cut adoption','Native parent source epoch differs bind_ev2 census hash; exact direct24 parameter/instance mapping matched, source semantics currentcohort join still required'],proposed_memory_gb=16,proposed_threads=4,memory_basis='Conservative frontend sizing; no measured residual peak. Existing wholeKV32GB has17GB live,176SRAM hardlogic excluded here; report actual peak.'),indent=2)+'\n');print('Materialized',len(receipts),'exact source aliases;',len(files),'readset files; bound',before)
