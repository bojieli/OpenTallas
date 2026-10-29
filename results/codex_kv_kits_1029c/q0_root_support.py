import importlib.util,sys,json
from pathlib import Path
kit,out=map(Path,sys.argv[1:]);s=importlib.util.spec_from_file_location('lec',kit/'lec.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);g=m.read_aig(kit/'lec/gold.aig');gp,gc,gx,_,_=m.key_points(g,m.read_map(kit/'lec/gold.map'));bylit={v//2:k for k,v in gp.items()};base=g['I']+g['L'];rec=[]
for k in sorted(gc):
 if not k.endswith('.u_tag.g_line.line[11]'):continue
 seen=set();todo=[gc[k]//2];support=[]
 while todo:
  v=todo.pop()
  if v in seen or not v:continue
  seen.add(v)
  if v<=base:support.append({'variable':v,'key':bylit.get(v,'X'+str(v))})
  else:
   j=2*(v-base-1);todo.extend([g['ands'][j]//2,g['ands'][j+1]//2])
 rec.append({'point':k,'raw_D':gc[k],'support':support,'ands':len(seen)-len(support)})
print(json.dumps(rec,indent=1),flush=True);out.write_text(json.dumps(rec,indent=1)+'\n')
