import pathlib,importlib.util,json
r=pathlib.Path('/subject');o=pathlib.Path('/out');sp=importlib.util.spec_from_file_location('F',r/'lec.py');F=importlib.util.module_from_spec(sp);sp.loader.exec_module(F)
g=F.read_aig(r/'lec/gold.aig');am=F.read_map(r/'lec/gold.map');gp,gc,*_=F.key_points(g,am);hyp=json.load(open(r/'lec/hyp.json'));rows=[]
for bit in range(8):
 key=f'ff:u_dut.u_fcore.u_x._190855_[{bit}]';lit=gc[key];seen=set();leaves=set();todo=[lit>>1]
 while todo:
  v=todo.pop()
  if not v or v in seen:continue
  seen.add(v)
  if v<=g['I']+g['L']:leaves.add(v);continue
  idx=v-g['I']-g['L']-1;todo.extend(x>>1 for x in g['ands'][2*idx:2*idx+2])
 support=[]
 for v in sorted(leaves):
  kind='input' if v<=g['I'] else 'latch';idx=v-1 if kind=='input' else v-g['I']-1
  support.append({'kind':kind,'index':idx,'names':am[kind].get(idx,[])})
 aliases=[k for k,d in gc.items() if d==lit and k!=key]
 rows.append({'key':key,'literal':lit,'same_next_D_keys':aliases,'support':support,'prior_hyp':[h for h in hyp if h[1]==key]})
(o/'SUPPORT.json').write_text(json.dumps({'scope':'READONLY_NATIVE_NEXT_D_NOT_EQ_OR_BASE_PROOF','rows':rows},indent=1)+'\n');print('rows',len(rows),'aliascounts',[len(x['same_next_D_keys'])for x in rows],'supportcounts',[len(x['support'])for x in rows],flush=True)
