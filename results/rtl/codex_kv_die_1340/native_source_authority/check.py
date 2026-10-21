from pathlib import Path
import ast,collections,hashlib,json,re,sys
B=Path.cwd();R=Path('/home/ubuntu/ot-scratch/claude/codex-kdie-captured5dd/source5dd');sys.path.insert(0,str(R/'tools'));import die_port_bind as PB
PB.ROOT=R
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=(B/'original.sv').read_text();new=(B/'candidate.sv').read_text();emit=(B/'kv_static_die.py').read_text();tree=ast.parse(emit);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rtl_text')
texts={m.group(1):m.group(0)for m in re.finditer(r'^// (qkd_kvs_\w+): GENERATED.*?^endmodule\n',old,re.M|re.S)};kinds=['ctl','attn','grp','pc','grp_h','pc_h','emb','hroot'];assert len(texts)==8
ns=dict(OrderedDict=collections.OrderedDict,GRP_S6C=False,GRP_S6C_RTL=dict(grp='',grp_h=''),KIND_MASTER=dict(zip(kinds,texts)),all_tiles=lambda:{k:dict(kind=k)for k in kinds},module_text=lambda t,n:texts[n]);exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual_emitter','exec'),ns);assert ns['rtl_text']()==old;ns['GRP_S6C']=True;assert ns['rtl_text']()==new
checks=['non_S6C_emission_byte_identity','S6C_exact_source_emission','six_other_bodies_byte_identity'];assert all(v in new for k,v in texts.items()if k not in ('qkd_kvs_grp_s6c','qkd_kvs_grp_h_s6c'));assert 'module qkd_kvs_grp_s6c 'not in new and 'module qkd_kvs_grp_h_s6c 'not in new
names=['qkd_kvs_grp_s6c','qkd_kvs_grp_h_s6c'];native=[R/'rtl/qwen_sys/static_kv_die_20261017'/f'{n}.sv'for n in names];files=[str(B/'candidate.sv'),*map(str,native)];bindings={n:dict(module=n,file=str(p),parameters={})for n,p in zip(names,native)}
s=(B/'kv_bound_netlist.py').read_text();start=s.index('    if any(b[\'module\']');end=s.index("    idx, _amb = PB.rtl_index",start);guard=__import__('textwrap').dedent(s[start:end]);start=s.index('    for _master in sorted(',end);end=s.index('\n    if _expanded is not None:',start);selected=__import__('textwrap').dedent(s[start:end]);base=dict(PB=PB,Path=Path,ROOT=R,defaultdict=collections.defaultdict,bindings=bindings,files=files,insts=[(n,'u_'+n,{}, {})for n in names],_expanded=None)
exec(guard,dict(base));checks.append('active_readset_unique_native_owners')
idx,amb=PB.rtl_index(['rtl'],files,{},files);base['idx']=idx;exec(selected,dict(base));checks.append('actual_strict_compiler_native_path_params_ports')
rows={}
for n,p in zip(names,native):
 m=idx[n];assert Path(m.path)==p and not m.params;assert len(m.body)>len(texts[n])  # real native structural body, not the wire-only shadow
 rows[n]=dict(source=str(p),sha256=sha(p),parameters=m.params,ports={k:list(v)for k,v in m.ports.items()},body_sha256=hashlib.sha256(m.body.encode()).hexdigest(),direct_children=sorted(PB.instantiated(m.body)))
# A stale wire-shadow body is refused even when the preferred native module is correct.
def refuses(code,ns,want):
 try:exec(code,ns)
 except SystemExit as e:
  assert want in str(e),(want,str(e));return str(e)
 raise AssertionError('mutant accepted: '+want)
mutants={}
bad=dict(base,files=[str(B/'original.sv'),*map(str,native)]);mutants['wire_shadow']=refuses(guard,bad,'active compilation redeclares')
b={k:dict(v)for k,v in bindings.items()};b[names[0]]['file']=str(B/'missing_native.sv');mutants['missing']=refuses(selected,dict(base,bindings=b),'selected binding source missing')
b={k:dict(v)for k,v in bindings.items()};b[names[0]]['file']=str(B/'original.sv');mutants['wrong_selected_source']=refuses(selected,dict(base,bindings=b),'does not come from selected source')
b={k:dict(v)for k,v in bindings.items()};b[names[0]]['file']=str(B/'candidate.sv');mutants['missing_module_in_present_source']=refuses(selected,dict(base,bindings=b),'declares 0 copies')
checks+=list(mutants)
# Check actual final checker argv construction, common to both strict passes.
sh=(B/'kv_port_bind_v2.sh').read_text();assert 'F+=(--rtl-file "$R/$NATIVE")'in sh;assert '${F[@]}'in sh and '${F2[@]}'in sh;assert "S.GRP_S6C_RTL.values()"in sh;checks.append('both_strict_passes_explicit_native_RTL')
seen=set();unres,models,seen_count=PB.child_closure(idx,names,[],seen_out=seen);closure={n:dict(path=idx[n].path,body_sha256=hashlib.sha256(idx[n].body.encode()).hexdigest())for n in sorted(seen)if n in idx};(B/'native_hierarchy.json').write_text(json.dumps(dict(modules=closure,unresolved={k:sorted(v)for k,v in unres.items()},models={k:sorted(v)for k,v in models.items()}),indent=2)+'\n')
r=dict(verdict='PASS',scope='source emission/native binding authority only; no whole-die bind/facts/physical',checks=checks,mutants=mutants,source_readset_sha256={str(p):sha(p)for p in [*native,B/'original.sv',B/'candidate.sv',B/'kv_static_die.py',B/'kv_bound_netlist.py',B/'kv_port_bind_v2.sh',R/'tools/die_port_bind.py']},native=rows,hierarchy=dict(modules=len(seen),unresolved={k:sorted(v)for k,v in unres.items()},models={k:sorted(v)for k,v in models.items()}));(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(verdict='PASS',checks=len(checks),hierarchy=r['hierarchy'])))
