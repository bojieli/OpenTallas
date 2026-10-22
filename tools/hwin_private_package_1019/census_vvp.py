import pathlib,re,json,sys,collections,hashlib
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);text=p.read_text(); chunks=re.split(r'(?m)(?=^S_\w+ \.scope )',text);scopes={};current=None
for c in chunks:
 m=re.match(r'(S_\w+) \.scope (\w+), "([^"]+)"(?: "([^"]+)")?[^\n]*;',c)
 if not m:continue
 parent=re.search(r', (S_\w+);',m[0]);scopes[m[1]]={'id':m[1],'kind':m[2],'name':m[3],'module':m[4],'parent':parent[1] if parent else None,'chunk':c}
def path(s):
 if 'path' not in s:s['path']=(path(scopes[s['parent']])+'.' if s['parent'] in scopes else '')+s['name']
 return s['path']
selected_name=sys.argv[3] if len(sys.argv)>3 else 'dut'
selected=[s for s in scopes.values() if path(s).endswith('.'+selected_name) or '.'+selected_name+'.' in path(s)];counts=collections.Counter(s['module'] for s in selected if s['kind']=='module');decls=[]
for s in selected:
 for m in re.finditer(r'(?m)^(\w+) \.var(?:/(\w+))? "([^"]+)", (-?\d+) (-?\d+);',s['chunk']):
  ancestor=s
  while ancestor['kind']!='module' and ancestor['parent'] in scopes:ancestor=scopes[ancestor['parent']]
  macro=ancestor['module']=='ot_sram_1r1w_64x16_m1'
  decls.append({'owning_module':ancestor['module'],'scope':path(s),'module':s['module'],'id':m[1],'kind':m[2] or '4state','name':m[3],'declared_bits':abs(int(m[4])-int(m[5]))+1,'classification':'macro_behavior' if macro else 'source_declaration_not_native_FF'})
assert counts['ot_sram_1r1w_64x16_m1']==84,counts
assert counts['dsdv_mu_hwin_capture_1019_early_current_hit']==(0 if selected_name=='dut_default' else 148),counts
json.dump({'scope':'Actual private candidate Icarus elaboration, no mapped retention claim','vvp_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'module_instance_counts':dict(sorted(counts.items())),'source_var_declarations':decls,'source_var_declarations_note':'All var declarations including procedural temporaries; NOT a synthesized FF/area census. Macro behavioral state not charged as std cells.','native_cost_total_um2':None},out.open('w'),indent=2);print(dict(counts));print('var_declarations',len(decls))
